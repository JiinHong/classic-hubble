"""Prepare text-only requests and import private candidates; no model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from .music_extraction import (
    MAX_RESPONSE_BYTES,
    digest,
    json_bytes,
    parse_response,
    prepare_request,
    validate_response,
)
from .r2 import R2Settings, R2Store
from .supabase import SupabaseRepository, SupabaseSettings


def _timestamp(row):
    value = datetime.fromisoformat(row["processed_at"])
    if value.tzinfo is None:
        raise ValueError("OCR processing timestamp must include a timezone")
    return value


def _current_ocr(repository, store, ocr_sha: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{64}", ocr_sha):
        raise ValueError("Invalid OCR hash")
    rows = [r for r in repository.load_ocr_results() if r.get("bucket") == store.bucket]
    matches = [r for r in rows if r.get("result_sha256") == ocr_sha]
    if len(matches) != 1 or matches[0].get("status") != "text_extracted":
        raise ValueError("Expected one stored OCR text result")
    row = matches[0]
    processed_at = _timestamp(row)
    source_sha = row["source_sha256"]
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha):
        raise ValueError("Invalid source identity")
    if (
        row["result_object_key"] != f"ocr/sha256/{ocr_sha[:2]}/{ocr_sha}"
        or row["source_object_key"] != f"originals/sha256/{source_sha[:2]}/{source_sha}"
    ):
        raise ValueError("Invalid evidence key")
    if any(
        other.get("source_sha256") == source_sha
        and other.get("result_sha256") != ocr_sha
        and _timestamp(other) >= processed_at
        for other in rows
    ):
        raise ValueError("OCR result has been superseded")
    if not any(
        source.get("sha256") == source_sha
        and source.get("bucket") == store.bucket
        and source.get("object_key") == row["source_object_key"]
        for source in repository.load_source_archives()
    ):
        raise ValueError("OCR source is no longer current")
    raw = store.read(row["result_object_key"])
    if hashlib.sha256(raw).hexdigest() != ocr_sha:
        raise ValueError("OCR integrity verification failed")
    document = json.loads(raw)
    for field in (
        "source_sha256",
        "source_object_key",
        "pipeline_version",
        "bucket",
        "status",
    ):
        if document.get(field) != row.get(field):
            raise ValueError("OCR metadata does not match its evidence")
    return document


def prepare(repository, store, ocr_sha: str) -> dict:
    return prepare_request(_current_ocr(repository, store, ocr_sha), ocr_sha)


def import_response(
    repository, store, ocr_sha: str, raw: bytes, *, producer: str, apply=False
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,120}", producer):
        raise ValueError("Invalid producer label")
    document = _current_ocr(repository, store, ocr_sha)
    response = parse_response(raw)
    report = validate_response(
        response, document, ocr_sha, repository.load_work_catalog()
    )
    report.update(
        producer=producer,
        response_sha256=digest(response),
        source_sha256=document["source_sha256"],
        source_object_key=document["source_object_key"],
        ocr_pipeline_version=document["pipeline_version"],
        bucket=store.bucket,
    )
    candidate_id = digest(report)
    counters = {
        "item_count": len(report["items"]),
        "suggestions": sum(
            item["suggested_work_id"] is not None for item in report["items"]
        ),
    }
    if apply:
        run_id = repository.start_ingestion_run("music_extraction")
        try:
            # Recheck after validation; final approval must also recheck freshness.
            _current_ocr(repository, store, ocr_sha)
            saved = store.archive_extraction_result(report)
            repository.upsert_provider_record(
                provider="music_extraction",
                entity_type="extraction_candidate",
                provider_id=candidate_id,
                ingestion_run_id=run_id,
                payload={
                    **{key: value for key, value in report.items() if key != "items"},
                    **counters,
                    "result_object_key": saved.key,
                    "result_sha256": saved.sha256,
                    "processed_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as error:
            repository.finish_ingestion_run(
                run_id, status="failed", counters=counters, error=type(error).__name__
            )
            raise
        repository.finish_ingestion_run(run_id, status="completed", counters=counters)
    return {
        "mode": "applied" if apply else "dry_run",
        "candidate_id": candidate_id,
        "review_status": "unverified",
        "publishable": False,
        **counters,
    }


def main(argv=None, *, repository=None, store=None, stdout=None, stderr=None) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser(
        "prepare", help="Export a private text-only request; no model call."
    )
    export.add_argument("--ocr-sha", required=True)
    export.add_argument("--output", type=Path, required=True)
    ingest = commands.add_parser(
        "import", help="Validate a response; dry-run unless --apply."
    )
    ingest.add_argument("--ocr-sha", required=True)
    ingest.add_argument("--response", type=Path, required=True)
    ingest.add_argument(
        "--producer",
        required=True,
        help="Operator-supplied provenance, e.g. manual-test.",
    )
    ingest.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        with ExitStack() as stack:
            if repository is None or store is None:
                load_dotenv()
            if repository is None:
                repository = stack.enter_context(
                    SupabaseRepository(SupabaseSettings.from_env())
                )
            if store is None:
                store = stack.enter_context(R2Store(R2Settings.from_env()))
            if args.command == "prepare":
                bundle = prepare(repository, store, args.ocr_sha)
                fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(json_bytes(bundle))
                result = {
                    "mode": "prepared",
                    "lines": len(bundle["input"]["lines"]),
                    "model_called": False,
                }
            else:
                with args.response.open("rb") as handle:
                    raw = handle.read(MAX_RESPONSE_BYTES + 1)
                result = import_response(
                    repository,
                    store,
                    args.ocr_sha,
                    raw,
                    producer=args.producer,
                    apply=args.apply,
                )
        output.write(json.dumps(result) + "\n")
        return 0
    except Exception as error:  # noqa: BLE001 - no source text or credentials in logs.
        errors.write(f"Music extraction failed: {type(error).__name__}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
