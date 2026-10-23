"""Promote verified corrections of unpublished readings without erasing evidence."""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from uuid import UUID

from .direct_vision import _cached, _identity, _match_reading, _original, _sources, _validate
from .music_extraction import MAX_RESPONSE_BYTES, digest, json_bytes, parse_response


def promote_correction(repository, store, proposal_id: str, *, apply=False) -> dict:
    """A stored proposal is evidence, not approval to bypass publication guards."""
    proposal_id = str(UUID(proposal_id))
    pointer = repository.load_vision_correction(proposal_id)
    if not pointer or pointer.get("bucket") != store.bucket:
        raise ValueError("Missing correction evidence in this bucket")
    sha = pointer.get("result_sha256", "")
    key = f"extractions/sha256/{sha[:2]}/{sha}"
    if not re.fullmatch(r"[a-f0-9]{64}", sha) or pointer.get("result_object_key") != key:
        raise ValueError("Invalid correction evidence key")
    raw = store.read(key)
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("Correction evidence integrity mismatch")
    proposal = parse_response(raw)
    identity = _identity(store, pointer.get("source_sha256", ""))
    if (
        proposal.get("identity") != identity
        or proposal.get("kind") != "direct_reading_correction_proposal"
        or proposal.get("correction_contract_version") != "private-correction-proposal-v1"
        or proposal.get("status") != "pending_revision_workflow"
        or pointer.get("status") != proposal["status"]
    ):
        raise ValueError("Correction identity or contract mismatch")
    reading = _validate(json_bytes(proposal.get("corrected_reading")), identity["source_sha256"])
    reading_sha = digest(reading)
    expected = proposal.get("active_reading_pointer_at_discovery", {})
    previous_sha = expected.get("reading_sha256")
    if (
        any(expected.get(k) != v for k, v in identity.items())
        or not isinstance(previous_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", previous_sha)
        or previous_sha != pointer.get("supersedes_reading_sha256")
        or previous_sha != proposal.get("supersedes_reading_sha256")
        or reading_sha != pointer.get("corrected_reading_sha256")
        or reading_sha != proposal.get("corrected_reading_sha256")
        or reading_sha == previous_sha
    ):
        raise ValueError("Correction reading hashes mismatch")
    current = repository.load_direct_vision_result(digest(identity))
    revision = {"proposal_id": proposal_id, "previous_reading_sha256": previous_sha}
    if current and current.get("reading_sha256") == reading_sha and current.get("revision") == revision:
        cached = _cached(repository, store, identity)
        if cached["reading"] != reading or cached.get("revision") != revision:
            raise ValueError("Applied correction evidence mismatch")
        return {"status": "unchanged", "published_items": 0}
    if current != expected:
        return {"status": "stale", "published_items": 0}
    _cached(repository, store, identity)
    _original(store, identity)
    sources = _sources(repository, identity)
    matching = _match_reading(repository, identity, reading)
    envelope = {
        **identity, "sources": sources, "reading": reading, "reading_sha256": reading_sha,
        "matching": matching, "revision": revision, "publication_status": "not_published",
    }
    if len(json_bytes(envelope)) > MAX_RESPONSE_BYTES:
        raise ValueError("Saved reading size limit exceeded")
    if not apply:
        return {"status": "ready", "published_items": 0}
    if sources != _sources(repository, identity):
        return {"status": "stale", "published_items": 0}
    stored = store.archive_extraction_result(envelope)
    new_pointer = {
        **identity, "reading_sha256": reading_sha, "status": reading["status"],
        "coverage": reading["coverage"], "result_sha256": stored.sha256,
        "result_object_key": stored.key, "observed_at": reading["observed_at"],
        "stored_at": datetime.now(UTC).isoformat(), "revision": revision,
    }
    return repository.revise_direct_vision({
        "p_key": digest(identity), "p_expected_reading": expected, "p_new_reading": new_pointer,
        "p_proposal_id": proposal_id, "p_expected_proposal": pointer, "p_expected_sources": sources,
    })
