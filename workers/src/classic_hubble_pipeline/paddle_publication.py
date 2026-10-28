"""Publish verified work identities and extent from immutable PaddleOCR evidence.

Text selections are a separate observation, never a renamed direct image reading.
This path never claims that the entire programme has been recovered.
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from contextlib import ExitStack
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
from dotenv import load_dotenv

from .music_extraction import digest, validate_response
from .music_review import _current_ocr
from .performance_dates import DATE_BINDING_VERSION, date_headings
from .r2 import R2Settings, R2Store
from .source_archive import download_source
from .supabase import SupabaseRepository, SupabaseSettings
from .vision_publication import _date_matches

VERSION = "paddle-partial-program-v1"
METHOD = "reviewed_paddle_text"
MIN_LINE_SCORE = 0.9
MATCH_REASONS = {"composer_and_catalogue", "composer_and_alias"}
BUNDLE_VERSION = "paddle-performance-bundle-v2"
PERFORMED_SCOPES = {"full_work", "movement", "excerpt", "arrangement", "unknown"}


def _score_ok(line):
    score = line.get("score")
    return type(score) in (int, float) and math.isfinite(score) and MIN_LINE_SCORE <= score <= 1


def _eligible(item, document):
    if item["context"] != "program":
        return "not_confirmed_program"
    if item["scope"] != "full_work":
        return "scope_requires_review"
    if not item["suggested_work_id"]:
        return item["reason"]
    if not item["fields"]["composer"] or item["reason"] not in MATCH_REASONS:
        return "explicit_composer_match_required"
    for field in ("composer", "title", "catalogue", "key"):
        for quote in item["evidence"][field] or []:
            if not _score_ok(document["lines"][int(quote["line_id"][1:])]):
                return "low_ocr_evidence_score"
    return None


def _verified_review(store, pointer):
    raw = store.read(pointer["result_object_key"])
    if hashlib.sha256(raw).hexdigest() != pointer["result_sha256"]:
        raise ValueError("Review integrity verification failed")
    saved = json.loads(raw)
    if any(saved.get(k) != v for k, v in pointer.items() if k not in {"result_object_key", "result_sha256"}):
        raise ValueError("Review metadata differs from immutable evidence")
    if pointer["version"] != VERSION or pointer["method"] != METHOD or pointer["bucket"] != store.bucket:
        raise ValueError("Unsupported review provenance")
    return saved


def save_review(repository, store, ocr_sha, response, *, notes):
    """Save an operator-reviewed text selection; performs no OCR or public write."""
    if not isinstance(notes, str) or not notes.strip():
        raise ValueError("Programme context and scope review notes are required")
    document = _current_ocr(repository, store, ocr_sha)
    if not document["pipeline_version"].startswith("paddle-"):
        raise ValueError("Expected PaddleOCR evidence")
    matching = validate_response(response, document, ocr_sha, repository.load_work_catalog(), automatic=True)
    if matching["validation_status"] != "complete" or matching["warnings"]:
        raise ValueError("Invalid or duplicate source selection")
    identity = {"version": VERSION, "method": METHOD, "source_sha256": document["source_sha256"],
                "document_sha256": ocr_sha, "response": response, "notes": notes, "bucket": store.bucket}
    key = digest(identity)
    existing = repository.load_paddle_review(key)
    if existing:
        saved = _verified_review(store, existing)
        if any(saved.get(k) != v for k, v in identity.items()):
            raise ValueError("Existing review identity mismatch")
        return key
    envelope = {**identity, "review_id": key, "reviewed_at": datetime.now(UTC).isoformat()}
    stored = store.archive_extraction_result(envelope)
    pointer = {**envelope, "result_sha256": stored.sha256, "result_object_key": stored.key}
    _verified_review(store, pointer)
    repository.upsert_provider_record(provider="paddle_review", entity_type="program_selection",
                                      provider_id=key, ingestion_run_id=None, payload=pointer)
    if repository.load_paddle_review(key) != pointer:
        raise ValueError("Review readback mismatch")
    return key


def publish(repository, store, client, performance_id, review_id, *, apply=False):
    target = repository.load_vision_target(performance_id)
    if not target:
        return {"status": "missing_performance", "items": 0}
    urls = target["intro_image_urls"]
    if len(urls) != 1 or not target["starts_on"] or target["starts_on"] != target["ends_on"]:
        return {"status": "date_or_source_binding_required", "items": 0}
    source = repository.load_vision_source(urls[0])
    pointer = repository.load_paddle_review(review_id)
    if not pointer:
        return {"status": "not_reviewed", "items": 0}
    review = _verified_review(store, pointer)
    if not source or source["source_url"] != urls[0] or performance_id not in source["performance_ids"]:
        return {"status": "source_not_archived", "items": 0}
    if source["sha256"] != review["source_sha256"] or source["bucket"] != store.bucket:
        return {"status": "source_changed", "items": 0}
    document = _current_ocr(repository, store, review["document_sha256"])
    if document["source_object_key"] != source["object_key"]:
        raise ValueError("Source key mismatch")
    if hashlib.sha256(store.read(source["object_key"])).hexdigest() != source["sha256"]:
        raise ValueError("Original integrity verification failed")
    quality_lines = {"lines": [line for line in document["lines"] if _score_ok(line)]}
    if not _date_matches(document, target["starts_on"]) or not _date_matches(quality_lines, target["starts_on"]):
        return {"status": "date_binding_required", "items": 0}
    matching = validate_response(review["response"], document, review["document_sha256"],
                                 repository.load_work_catalog(), automatic=True)
    if matching["validation_status"] != "complete" or matching["warnings"] or matching["source_warnings"]:
        return {"status": "invalid_selection", "items": 0}
    items, reasons = [], Counter()
    for row in matching["items"]:
        reason = _eligible(row, document)
        row["publication_eligible"] = reason is None
        if reason:
            reasons[reason] += 1
            continue
        fields = row["fields"]
        items.append({"work_id": row["suggested_work_id"], "position": row["source_index"],
                      "display_title": " ".join(filter(None, [fields["title"], fields["catalogue"]])),
                      "composer_name": fields["composer"]})
    result = {"status": "ready" if items else "no_eligible_items", "items": len(items),
              "program_status": "partially_confirmed", "withheld_reasons": dict(reasons)}
    if not items or not apply:
        return result
    live, content_type = download_source(client, urls[0])
    if hashlib.sha256(live).hexdigest() != source["sha256"] or content_type != source["content_type"]:
        return {"status": "source_changed", "items": 0}
    # Re-read metadata immediately before the atomic transaction, never cached IDs.
    ocr = next(r for r in repository.load_ocr_results() if r["result_sha256"] == review["document_sha256"])
    return repository.publish_paddle_program({
        "p_performance_id": performance_id, "p_expected_performance": target,
        "p_source": source, "p_ocr": ocr, "p_review": pointer,
        "p_evaluation": {"publication_version": VERSION, "performance_date": target["starts_on"],
                         "date_binding_version": DATE_BINDING_VERSION, "matching": matching,
                         "live_sha256": source["sha256"], "source_checked_at": datetime.now(UTC).isoformat()},
        "p_items": items,
    })


def _bundle_eligible(row, document):
    if row.get("derived_from"):
        return "derived_selection_requires_review"
    if row["scope"] not in PERFORMED_SCOPES:
        return "unsupported_scope"
    identity = row["suggested_work_id"] or row["scoped_work_id"]
    reason = _eligible({**row, "scope": "full_work", "suggested_work_id": identity,
                        "reason": row["identity_reason"]}, document)
    if reason:
        return reason
    for movement in row["evidence"]["movements"]:
        if any(not _score_ok(document["lines"][int(q["line_id"][1:])]) for q in movement):
            return "low_ocr_evidence_score"
    return None


def publish_bundle(repository, store, client, performance_id, review_ids, *, apply=False):
    """Validate the current performance's complete image set, then publish a subset.

    Review identities remain v1. This distinct publication contract carries the
    performed scope and retains the source of every item and supporting date.
    """
    target = repository.load_vision_target(performance_id)
    if not target:
        return {"status": "missing_performance", "items": 0}
    urls = target["intro_image_urls"]
    if (not urls or len(urls) > 50 or len(set(urls)) != len(urls)
            or not target["starts_on"] or target["starts_on"] != target["ends_on"]):
        return {"status": "date_or_source_binding_required", "items": 0}
    sources = [repository.load_vision_source(url) for url in urls]
    if any(not s or s["source_url"] != url or s["bucket"] != store.bucket
           or performance_id not in s["performance_ids"] for url, s in zip(urls, sources)):
        return {"status": "source_not_archived", "items": 0}
    reviews = {}
    for key in dict.fromkeys(review_ids):
        pointer = repository.load_paddle_review(key)
        if not pointer:
            return {"status": "not_reviewed", "items": 0}
        review = _verified_review(store, pointer)
        if review["response"]["status"] == "uncertain":
            return {"status": "incomplete_source_bundle", "items": 0}
        if review["source_sha256"] in reviews:
            return {"status": "ambiguous_source_review", "items": 0}
        reviews[review["source_sha256"]] = pointer
    hashes = {s["sha256"] for s in sources}
    if hashes != reviews.keys():
        return {"status": "incomplete_source_bundle", "items": 0}
    ocr_rows = repository.load_ocr_results_for_sources(hashes, store.bucket)
    # Reuse one bounded snapshot during validation. The RPC rechecks every
    # pointer while holding the performance lock; cached metadata cannot publish.
    snapshot = SimpleNamespace(load_ocr_results=lambda: ocr_rows, load_source_archives=lambda: sources)
    works = repository.load_work_catalog()
    documents, items, reasons, seen = [], [], Counter(), set()
    expected_date = tuple(map(int, target["starts_on"].split("-")))
    for source in sources:
        pointer = reviews[source["sha256"]]
        doc = _current_ocr(snapshot, store, pointer["document_sha256"])
        if hashlib.sha256(store.read(source["object_key"])).hexdigest() != source["sha256"]:
            raise ValueError("Original integrity verification failed")
        dates, invalid = date_headings([line["text"] for line in doc["lines"]], fallback_year=expected_date[0])
        if invalid or dates - {expected_date}:
            return {"status": "date_binding_required", "items": 0}
        if dates and not _date_matches({"lines": [line for line in doc["lines"] if _score_ok(line)]}, target["starts_on"]):
            return {"status": "date_binding_required", "items": 0}
        matching = validate_response(pointer["response"], doc, pointer["document_sha256"], works, automatic=True)
        if matching["validation_status"] != "complete" or matching["warnings"] or matching["source_warnings"]:
            return {"status": "invalid_selection", "items": 0}
        for row in matching["items"]:
            reason = _bundle_eligible(row, doc)
            row["publication_eligible"] = reason is None
            if reason:
                reasons[reason] += 1
                continue
            fields = row["fields"]
            work_id = row["suggested_work_id"] or row["scoped_work_id"]
            signature = (work_id, row["scope"], tuple(fields["movements"]))
            if signature in seen:
                row["publication_eligible"] = False
                reasons["duplicate_evidence"] += 1
                continue
            seen.add(signature)
            items.append({"work_id": work_id, "position": len(items),
                          "display_title": " ".join(filter(None, [fields["title"], fields["catalogue"]])),
                          "composer_name": fields["composer"], "performed_scope": row["scope"],
                          "scope_details": fields["movements"], "source_url": source["source_url"]})
        documents.append({"source": source,
                          "ocr": next(r for r in ocr_rows if r["result_sha256"] == pointer["document_sha256"]),
                          "review": pointer, "matching": matching,
                          "date_binding": "target" if dates else "absent"})
    if not any(d["date_binding"] == "target" for d in documents):
        return {"status": "date_binding_required", "items": 0}
    result = {"status": "ready" if items else "no_eligible_items", "items": len(items),
              "program_status": "partially_confirmed", "withheld_reasons": dict(reasons)}
    if not items or not apply:
        return result
    for doc in documents:
        source = doc["source"]
        raw, content_type = download_source(client, source["source_url"])
        if hashlib.sha256(raw).hexdigest() != source["sha256"] or content_type != source["content_type"]:
            return {"status": "source_changed", "items": 0}
        doc.update(live_sha256=source["sha256"], source_checked_at=datetime.now(UTC).isoformat())
    return repository.publish_paddle_program_bundle({
        "p_performance_id": performance_id, "p_expected_performance": target,
        "p_documents": documents, "p_items": items,
        "p_evaluation": {"publication_version": BUNDLE_VERSION, "date_binding_version": DATE_BINDING_VERSION,
                         "performance_date": target["starts_on"]},
    })


def main(argv=None, *, repository=None, store=None, stdout=None, stderr=None):
    """Revalidate one saved performance bundle; no OCR or model calls."""
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--performance-id", required=True)
    parser.add_argument("--review-id", action="append", required=True)
    parser.add_argument("--apply", action="store_true", help="Publish after live-source and atomic DB checks.")
    args = parser.parse_args(argv)
    if len(args.review_id) > 50:
        parser.error("At most 50 saved reviews per performance")
    try:
        with ExitStack() as stack:
            if repository is None or store is None:
                load_dotenv()
            if repository is None:
                settings = SupabaseSettings.from_env()
                if settings.url != "https://klnfamtwxwrelrjeguqb.supabase.co":
                    raise ValueError("This publication command targets Classic Hubble only")
                repository = stack.enter_context(SupabaseRepository(settings))
            if store is None:
                settings = R2Settings.from_env()
                if settings.bucket != "classic-hubble-sources":
                    raise ValueError("Expected the private Classic Hubble source bucket")
                store = stack.enter_context(R2Store(settings))
            client = stack.enter_context(httpx.Client(
                timeout=30, follow_redirects=False,
                headers={"User-Agent": "classic-hubble-pipeline/0.1"},
            )) if args.apply else None
            result = publish_bundle(repository, store, client, args.performance_id, args.review_id, apply=args.apply)
        output.write(json.dumps({"mode": "apply" if args.apply else "dry_run", **result}) + "\n")
        return 0
    except Exception as error:  # No source text or credentials in operational logs.
        errors.write(f"Paddle publication failed: {type(error).__name__}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
