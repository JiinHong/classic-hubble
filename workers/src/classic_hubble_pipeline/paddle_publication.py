"""Publish independently verified full works from immutable PaddleOCR evidence.

Text selections are a separate observation, never a renamed direct image reading.
This path never claims that the entire programme has been recovered.
"""

import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime

from .music_extraction import digest, validate_response
from .music_review import _current_ocr
from .performance_dates import DATE_BINDING_VERSION
from .source_archive import download_source
from .vision_publication import _date_matches

VERSION = "paddle-partial-program-v1"
METHOD = "reviewed_paddle_text"
MIN_LINE_SCORE = 0.9
MATCH_REASONS = {"composer_and_catalogue", "composer_and_alias"}


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
