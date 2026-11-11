"""Publish a work association with its printed movements, without inferring a full work."""
import hashlib
from datetime import UTC, datetime

from .direct_vision import _cached, _identity, _match_reading, _original
from .music_extraction import digest, json_bytes
from .source_archive import download_source
from .vision_publication import _date_matches


def aligned_movement_matches(stored, current):
    def eligible(result):
        if (not result or result.get("validation_status") != "complete" or result.get("warnings")
                or result.get("source_warnings") or result.get("rejected_items")):
            return {}
        rows = {}
        for row in result["items"]:
            wid, fields = row.get("scoped_work_id"), row["fields"]
            if (row.get("derived_from") or row["context"] != "program" or row["scope"] not in {"unknown", "excerpt", "movement"}
                    or row.get("reason") != "scope_requires_review" or row.get("identity_reason") != "composer_and_catalogue"
                    or not wid or row.get("suggested_work_id") or row.get("candidate_ids") != [wid]
                    or not all(fields.get(k) for k in ("composer", "title", "catalogue", "movements"))):
                continue
            index = row["source_index"]
            if index in rows:
                return {}
            rows[index] = (wid, row["scope"], fields, row["evidence"])
        return rows

    old, new = eligible(stored), eligible(current)
    return [{"index": i, "work_id": old[i][0], "scope": old[i][1]}
            for i in sorted(old) if i in new and new[i] == old[i]]


def publish(repository, store, client, performance_id, *, apply=False):
    target = repository.load_vision_target(performance_id)
    if (not target or not target.get("starts_on") or target["starts_on"] != target.get("ends_on")
            or len(target.get("intro_image_urls") or []) != 1):
        return {"status": "date_or_source_binding_required", "items": 0}
    url, = target["intro_image_urls"]
    source = repository.load_vision_source(url)
    if (not source or store.bucket != "classic-hubble-sources" or source.get("source_url") != url
            or performance_id not in (source.get("performance_ids") or [])):
        return {"status": "source_not_archived", "items": 0}
    identity = _identity(store, source["sha256"])
    if source.get("bucket") != store.bucket or source.get("object_key") != identity["source_object_key"]:
        raise ValueError("Source identity mismatch")
    cached = _cached(repository, store, identity)
    if not cached:
        return {"status": "not_read", "items": 0}
    reading = cached["reading"]
    if (reading["coverage"] != "complete" or reading["extraction_status"] != "items_extracted"
            or not _date_matches(reading, target["starts_on"])):
        return {"status": "incomplete_or_undated_reading", "items": 0}
    _original(store, identity)
    candidates = aligned_movement_matches(cached["matching"], _match_reading(repository, identity, reading))
    if not candidates:
        return {"status": "no_verified_catalogue_movements", "items": 0}
    packet = dict(url=url, sha=source["sha256"], reading_key=digest(identity),
                  envelope_utf8=json_bytes(cached).decode("utf-8"))
    preview = repository.publish_direct_movement_program(performance_id, packet, candidates, None)
    if not apply or preview["status"] != "ready":
        return preview
    expected = preview.get("program") or []
    if len(expected) != len(candidates) or [(r["position"], r["work_id"], r["performed_scope"]) for r in expected] != [
        (r["index"], r["work_id"], r["scope"]) for r in candidates
    ]:
        raise ValueError("Movement publication preview changed")
    data, content_type = download_source(client, url)
    live_sha = hashlib.sha256(data).hexdigest()
    if live_sha != source["sha256"] or content_type != source["content_type"]:
        return {"status": "source_changed", "items": 0}
    packet.update(live_sha=live_sha, content_type=content_type, checked_at=datetime.now(UTC).isoformat())
    return repository.publish_direct_movement_program(performance_id, packet, candidates, expected)
