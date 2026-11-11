"""Publish a work association with its printed movements, without inferring a full work."""
import hashlib
import json
import re
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


def registry_candidates(stored, current, authorities):
    """A later parent identity may fill an empty match, never replace a different one."""
    def indexed(result):
        if (not result or result.get("validation_status") != "complete" or result.get("warnings")
                or result.get("source_warnings") or result.get("rejected_items")):
            return {}
        rows = {}
        for row in result["items"]:
            if row.get("derived_from") or row["context"] != "program":
                continue
            i = row["source_index"]
            if i in rows:
                return {}
            rows[i] = row
        return rows

    old, new = indexed(stored), indexed(current)
    candidates = []
    for i in sorted(old.keys() & new.keys()):
        a, b = old[i], new[i]
        if any(a[k] != b[k] for k in ("evidence", "fields", "scope")):
            continue
        f = b["fields"]
        if not f.get("title") or not f.get("composer"):
            continue
        if b["scope"] == "full_work" and not any(f.get(k) for k in ("movements", "catalogue", "key")):
            wid = b.get("suggested_work_id")
            if not wid or any(x.get("reason") != "composer_and_alias" or x.get("identity_reason") != "composer_and_alias"
                              or x.get("candidate_ids") != [wid] or x.get("suggested_work_id") != wid
                              or x.get("scoped_work_id") for x in (a, b)):
                continue
        elif b["scope"] == "unknown" and all(f.get(k) for k in ("movements", "catalogue", "key")):
            wid = b.get("scoped_work_id")
            if (not wid or a.get("reason") != "scope_requires_review" or b.get("reason") != "scope_requires_review"
                    or b.get("candidate_ids") != [wid] or b.get("identity_reason") != "composer_and_catalogue"
                    or b.get("suggested_work_id") or a.get("suggested_work_id") or a.get("scoped_work_id")
                    or a.get("candidate_ids") != [] or a.get("identity_reason") != "no_candidate"):
                continue
        else:
            continue
        key = authorities.get(wid)
        if isinstance(key, str) and re.fullmatch("[0-9a-f]{64}", key):
            candidates.append({"index": i, "work_id": wid, "scope": "unknown", "authority_key": key})
    return candidates


def gala_candidates(frozen, proof):
    """A reviewed parent can fill an empty identity, not reinterpret a numbered excerpt."""
    if (not frozen or frozen.get("validation_status") != "complete"
            or any(frozen.get(k) != [] for k in ("warnings", "source_warnings", "rejected_items"))):
        return []
    parents = {}
    for w in proof["works"]:
        name = w["printed_title"]
        if not name or name in parents or not w["work_id"]:
            return []
        parents[name] = w["work_id"]
    matches, seen = [], set()
    for r in frozen["items"]:
        i, ref, f = r["source_index"], r["evidence"], r["fields"]
        if (i in seen or "derived_from" in r or
                any(x.get("context") != "program" or x.get("scope") != "excerpt" for x in (r, ref))
                or r.get("reason") != "scope_requires_review" or r.get("identity_reason") != "no_candidate"
                or r.get("candidate_ids") != [] or r.get("suggested_work_id") or r.get("scoped_work_id")
                or any(x.get(k) is not None for x in (f, ref) for k in ("catalogue", "key"))
                or f.get("composer") != proof["printed_composer"] or not f.get("title") or f["title"] not in parents
                or len(ref.get("composer") or []) != 1 or ref["composer"][0].get("quote") != f["composer"]
                or len(ref.get("title") or []) != 1 or ref["title"][0].get("quote") != f["title"]
                or len(ref.get("movements") or []) != 1 or len(ref["movements"][0]) != 1):
            return []
        part = ref["movements"][0][0]
        if (not part.get("quote") or part.get("line_id") != ref["title"][0].get("line_id")
                or f.get("movements") != [part["quote"]] or part["quote"] == f["title"]):
            return []
        seen.add(i)
        matches.append(dict(index=i, work_id=parents[f["title"]], scope="excerpt"))
    return sorted(matches, key=lambda x: x["index"])


def _gala_proof(store, key, target, performance_id, source_sha):
    if not isinstance(key, str) or not re.fullmatch("[0-9a-f]{64}", key):
        raise ValueError("Invalid gala programme authority")
    raw = store.read(f"extractions/sha256/{key[:2]}/{key}")
    if hashlib.sha256(raw).hexdigest() != key:
        raise ValueError("Changed gala programme authority")
    proof = json.loads(raw)
    if (proof.get("purpose") != "named_gala_excerpts_v1" or proof.get("edition_identified") is not False
            or proof.get("performance_id") != performance_id or proof.get("source_sha") != source_sha
            or proof.get("date") != target["starts_on"] or proof.get("event_title") != target["title"]
            or not proof.get("works")):
        return None
    for k in ("calendar", "catalogue_source"):
        sha = proof[k]["sha256"]
        if not re.fullmatch("[0-9a-f]{64}", sha) or hashlib.sha256(store.read(f"originals/sha256/{sha[:2]}/{sha}")).hexdigest() != sha:
            raise ValueError("Gala authority source identity mismatch")
    return proof


def publish(repository, store, client, performance_id, *, apply=False, authorities=None, gala_key=None):
    if authorities is not None and gala_key is not None:
        raise ValueError("Select one programme authority")
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
            or (gala_key is None and not _date_matches(reading, target["starts_on"]))):
        return {"status": "incomplete_or_undated_reading", "items": 0}
    _original(store, identity)
    if gala_key is not None:
        proof = _gala_proof(store, gala_key, target, performance_id, source["sha256"])
        candidates = gala_candidates(cached["matching"], proof) if proof else []
    else:
        current = _match_reading(repository, identity, reading)
        candidates = (aligned_movement_matches(cached["matching"], current) if authorities is None
                      else registry_candidates(cached["matching"], current, authorities))
    if not candidates:
        return {"status": "no_verified_catalogue_movements", "items": 0}
    packet = dict(url=url, sha=source["sha256"], reading_key=digest(identity),
                  envelope_utf8=json_bytes(cached).decode("utf-8"))
    if gala_key is not None:
        packet.update(identity_mode="named_gala_excerpts_v1", gala_key=gala_key)
    elif authorities is not None:
        packet["identity_mode"] = "independent_parent_registry_v1"
        for key in {c["authority_key"] for c in candidates}:
            data = store.read(f"extractions/sha256/{key[:2]}/{key}")
            if hashlib.sha256(data).hexdigest() != key:
                raise ValueError("Parent authority archive mismatch")
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
