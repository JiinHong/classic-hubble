"""Publish verified direct readings without changing the original observation."""

import hashlib
import re
from datetime import UTC, date, datetime

from .direct_vision import _cached, _identity, _match_reading, _original
from .music_extraction import digest, json_bytes
from .performance_dates import DATE_BINDING_VERSION, date_headings
from .source_archive import download_source

PUBLICATION_VERSION = "direct-vision-single-source-v1"


def publish_kopis_sheets(repository, store, client, performance_id, sty_sha, *, apply=False):
    """Bind complete original sheets to the same ordered programme in KOPIS."""
    if not re.fullmatch(r"[0-9a-f]{64}", sty_sha) or store.bucket != "classic-hubble-sources":
        raise ValueError("Invalid detail digest or source bucket")
    target = repository.load_vision_target(performance_id)
    urls = (target or {}).get("intro_image_urls") or []
    if not (2 <= len(urls) <= 6 and len(set(urls)) == len(urls)
            and target.get("starts_on") and target["starts_on"] == target.get("ends_on")):
        return {"status": "date_or_source_binding_required", "items": 0}
    documents, content_types = [], []
    for url in urls:
        source = repository.load_vision_source(url)
        if (not source or source.get("source_url") != url
                or performance_id not in (source.get("performance_ids") or [])):
            return {"status": "source_not_archived", "items": 0}
        identity = _identity(store, source["sha256"])
        if source.get("bucket") != store.bucket or source.get("object_key") != identity["source_object_key"]:
            raise ValueError("Source identity mismatch")
        cached = _cached(repository, store, identity)
        if not cached:
            return {"status": "not_read", "items": 0}
        reading = cached["reading"]
        if reading.get("status") != "text_extracted" or reading.get("coverage") != "complete":
            return {"status": "partial_reading", "items": 0}
        _original(store, identity)
        documents.append({"url": url, "sha": source["sha256"], "reading_key": digest(identity),
                          "reading_utf8": json_bytes(reading).decode("utf-8")})
        content_types.append(source["content_type"])

    preview = repository.publish_direct_kopis_sheets(performance_id, sty_sha, documents, None)
    if preview["status"] != "ready" or not apply:
        return preview
    expected = preview.get("program")
    if not isinstance(expected, list) or not expected or len(expected) != preview.get("items"):
        raise ValueError("Invalid sheet publication preview")
    for doc, original_type in zip(documents, content_types, strict=True):
        data, content_type = download_source(client, doc["url"])
        live_sha = hashlib.sha256(data).hexdigest()
        if live_sha != doc["sha"] or content_type != original_type:
            return {"status": "source_changed", "items": 0}
        doc.update(live_sha=live_sha, content_type=content_type, checked_at=datetime.now(UTC).isoformat())
    return repository.publish_direct_kopis_sheets(performance_id, sty_sha, documents, expected)


def _date_matches(reading, target_date):
    target = date.fromisoformat(target_date)
    dates, invalid = date_headings(
        (line["text"] for line in reading["lines"]), fallback_year=target.year
    )
    return not invalid and dates == {(target.year, target.month, target.day)}


def publish(repository, store, client, performance_id, *, apply=False, series_calendar=False):
    target = repository.load_vision_target(performance_id)
    if not target:
        return {"status": "missing_performance", "items": 0}
    urls = target["intro_image_urls"]
    if len(urls) != 1 or not target["starts_on"] or target["starts_on"] != target["ends_on"]:
        return {"status": "date_or_source_binding_required", "items": 0}
    source = repository.load_vision_source(urls[0])
    if not source or source["source_url"] != urls[0] or performance_id not in source["performance_ids"]:
        return {"status": "source_not_archived", "items": 0}
    identity = _identity(store, source["sha256"])
    if source["object_key"] != identity["source_object_key"] or source["bucket"] != store.bucket:
        raise ValueError("Source identity mismatch")
    cached = _cached(repository, store, identity)
    if cached is None:
        return {"status": "not_read", "items": 0}
    if cached["reading"]["coverage"] != "complete":
        return {"status": "partial_reading", "items": 0}
    reading = cached["reading"]
    proof = None
    if series_calendar:
        raw = json_bytes(reading).decode("utf-8")
        proof = repository.load_direct_series_program(raw, cached["reading_sha256"], target["starts_on"])
        if (not proof or proof.get("version") != "direct-series-calendar-v1"
                or proof.get("performance_date") != target["starts_on"]
                or not 0 < proof["end_line"] < proof["calendar_line"] < len(reading["lines"])):
            return {"status": "date_binding_required", "items": 0}
        # Keep every non-calendar date visible, including dates in the artist section.
        if not _date_matches({**reading, "lines": reading["lines"][:proof["calendar_line"]]}, target["starts_on"]):
            return {"status": "date_binding_required", "items": 0}
        # The proof checks all work citations against their original (unshifted) lines.
        reading = {**reading, "lines": reading["lines"][:proof["end_line"]]}
    if not _date_matches(reading, target["starts_on"]):
        return {"status": "date_binding_required", "items": 0}
    _original(store, identity)
    matching = _match_reading(repository, identity, reading)
    if not matching or not matching["complete"] or matching["source_warnings"]:
        return {"status": "unresolved_program", "items": 0}
    items = []
    for row in matching["items"]:
        if row["context"] != "program":
            continue
        if not row["suggested_work_id"] or row["scope"] != "full_work":
            return {"status": "unresolved_program", "items": 0}
        fields = row["fields"]
        items.append({
            "work_id": row["suggested_work_id"], "position": len(items),
            "display_title": " ".join(filter(None, [fields["title"], fields["catalogue"]])),
            "composer_name": fields["composer"],
        })
    if not items:
        return {"status": "no_program", "items": 0}
    if not apply:
        return {"status": "ready", "items": len(items)}
    data, content_type = download_source(client, urls[0])
    if hashlib.sha256(data).hexdigest() != source["sha256"] or content_type != source["content_type"]:
        return {"status": "source_changed", "items": 0}
    evaluation = {
        "publication_version": PUBLICATION_VERSION,
        "reading_sha256": cached["reading_sha256"], "matching": matching,
        "source_checked_at": datetime.now(UTC).isoformat(),
        "live_sha256": source["sha256"],
        "performance_date": target["starts_on"],
        "date_binding_version": DATE_BINDING_VERSION,
    }
    if proof is not None:
        evaluation.update(publication_version="direct-vision-series-calendar-v1",
                          series_program=proof, series_reading_utf8=raw)
    return repository.publish_direct_vision({
        "p_performance_id": performance_id, "p_expected_performance": target,
        "p_source": source,
        "p_reading": repository.load_direct_vision_result(digest(identity)),
        "p_evaluation": evaluation, "p_items": items,
    })
