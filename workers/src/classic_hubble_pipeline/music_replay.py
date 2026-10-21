"""Re-evaluate saved OCR/model results offline; never call a model or publish."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .music_extraction import json_bytes, parse_response, validate_response
from .music_matching import MusicMatcher
from .work_matching import CanonicalWork


def _save(path: Path, value: object):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(json_bytes(value))


def replay(root: Path, output: Path) -> dict:
    works = [
        CanonicalWork(
            **{
                **row,
                "titles": tuple(row["titles"]),
                "composers": tuple(row["composers"]),
                "aliases": tuple(row.get("aliases", [])),
            }
        )
        for row in json.loads((root / "catalogue.json").read_text())
    ]
    matcher = MusicMatcher([replace(work, requires_review=False) for work in works])
    output.mkdir(mode=0o700)
    reports, rows, failures = [], [], []
    reasons, identity_reasons, rejection_reasons = Counter(), Counter(), Counter()
    raw_items = 0
    for path in sorted(root.glob("*/extraction.json")):
        sha = path.parent.name
        if not re.fullmatch(r"[a-f0-9]{64}", sha):
            continue
        try:
            payload = parse_response(path.read_bytes())
            if isinstance(payload.get("items"), list):
                raw_items += len(payload["items"])
            report = validate_response(
                payload,
                json.loads((path.parent / "ocr.json").read_text()),
                sha,
                works,
                automatic=True,
                matcher=matcher,
            )
        except ValueError as error:
            failures.append({"document_sha256": sha, "error": str(error)})
            continue
        reports.append(report)
        _save(output / f"{sha}.json", report)
        for rejected in report["rejected_items"]:
            rejection_reasons[rejected["reason"]] += 1
        for item in report["items"]:
            reasons[item["reason"]] += 1
            identity_reasons[item["identity_reason"]] += 1
            rows.append(
                {
                    "document_sha256": sha,
                    "index": item["source_index"],
                    "context": item["context"],
                    "scope": item["scope"],
                    "composer": item["fields"]["composer"],
                    "title": item["fields"]["title"],
                    "catalogue": item["fields"]["catalogue"],
                    "full_work_id": item["suggested_work_id"],
                    "scoped_work_id": item["scoped_work_id"],
                    "candidate_ids": ";".join(item["candidate_ids"]),
                    "reason": item["reason"],
                    "identity_reason": item["identity_reason"],
                }
            )
    summary = {
        "documents": len(reports) + len(failures),
        "raw_items": raw_items,
        "validation_statuses": dict(Counter(r["validation_status"] for r in reports)),
        "document_failures": failures,
        "validated_items": len(rows),
        "rejected_items": sum(rejection_reasons.values()),
        "rejection_reasons": dict(rejection_reasons),
        "matching_reasons": dict(reasons),
        "identity_reasons": dict(identity_reasons),
        "full_work_references": sum(bool(r["full_work_id"]) for r in rows),
        "scoped_work_references": sum(bool(r["scoped_work_id"]) for r in rows),
        "unique_full_works": len(
            {r["full_work_id"] for r in rows if r["full_work_id"]}
        ),
        "unique_scoped_works": len(
            {r["scoped_work_id"] for r in rows if r["scoped_work_id"]}
        ),
        "matched_documents": len(
            {
                r["document_sha256"]
                for r in rows
                if r["full_work_id"] or r["scoped_work_id"]
            }
        ),
        "additional_api_calls": 0,
        "additional_cost_usd": 0,
        "public_database_updates": False,
        "accuracy_measured": False,
    }
    _save(output / "summary.json", summary)
    if rows:
        fd = os.open(output / "items.csv", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
