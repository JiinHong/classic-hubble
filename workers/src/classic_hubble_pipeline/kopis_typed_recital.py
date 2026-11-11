"""Link official, typed KOPIS recital items. The poster corroborates the event, not the songs."""
import hashlib
import json
import re
from datetime import UTC, datetime

from .direct_vision import _cached, _identity, _original
from .music_extraction import digest, json_bytes
from .source_archive import download_source


_HEADER = re.compile(r"(?:M\.Sop|Sop|Ten)\. [가-힣]{2,6} · Kl\. [가-힣]{2,6}")
_SONG = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ '!?,.()-]{0,150}), D ([1-9][0-9]{0,3})(?: No\. ([1-9][0-9]?))?")
_DETAIL = ("mt20id", "prfnm", "prfpdfrom", "prfpdto", "dtguidance", "fcltynm", "styurls")


def parse_program(sty):
    if not isinstance(sty, str) or len(sty.encode()) > 32000:
        return []
    lines = sty.replace("\r\n", "\n").split("\n")
    if len(lines) > 200 or lines[0].strip(" ") != "[PROGRAM]":
        return []
    rows, group, in_group = [], False, 0
    for i, raw in enumerate(lines[1:], 1):
        s = raw.strip(" ")
        if not s:
            continue
        if _HEADER.fullmatch(s):
            if group and not in_group:
                return []
            group, in_group = True, 0
        elif s == "— Pause —":
            if not group or not in_group:
                return []
            group, in_group = False, 0
        else:
            m = _SONG.fullmatch(s)
            if not group or not m or len(rows) >= 60:
                return []
            rows.append(dict(position=len(rows), line=i, title=m[1], number=m[2], member=m[3], literal=s))
            in_group += 1
    return rows if group and in_group else []


def select_songs(rows, references):
    choices, held = [], {}
    for row in rows:
        index = row["position"]
        if row["member"] is not None:
            held[index] = "member_identity_not_verified"
            continue
        matches = [ref for ref in references if ref.get("member") is None and ref["number"] == row["number"]
                   and row["title"] in ref["title_forms"]]
        if len(matches) != 1:
            held[index] = "ambiguous_authority" if matches else "no_verified_title_and_number"
            continue
        choices.append(dict(position=index, line=row["line"], work_id=matches[0]["work_id"]))
    return choices, held


def publish(repository, store, client, kopis, performance_id, detail, authority_sha, *, apply=False):
    target = repository.load_vision_target(performance_id)
    if (not target or not target.get("starts_on") or target["starts_on"] != target.get("ends_on")
            or len(target.get("intro_image_urls") or []) != 1 or target.get("title") != detail.get("prfnm")):
        return {"status": "date_or_source_binding_required", "items": 0}
    url, = target["intro_image_urls"]
    src = repository.load_vision_source(url)
    if not src or src.get("source_url") != url or performance_id not in (src.get("performance_ids") or []):
        return {"status": "source_not_archived", "items": 0}
    identity = _identity(store, src["sha256"])
    if store.bucket != "classic-hubble-sources" or src.get("bucket") != store.bucket or src.get("object_key") != identity["source_object_key"]:
        raise ValueError("Cover archive identity mismatch")
    cached = _cached(repository, store, identity)
    if not cached or cached["reading"].get("extraction_status") != "no_program_identified":
        return {"status": "not_cover_only", "items": 0}
    _original(store, identity)
    if not re.fullmatch(r"[a-f0-9]{64}", authority_sha):
        raise ValueError("Invalid catalogue key")
    raw = store.read(f"extractions/sha256/{authority_sha[:2]}/{authority_sha}")
    if hashlib.sha256(raw).hexdigest() != authority_sha:
        raise ValueError("Catalogue authority archive mismatch")
    proof = json.loads(raw)
    if proof.get("purpose") != "schubert_lied_identities_v1":
        raise ValueError("Wrong catalogue authority")
    songs = parse_program(detail.get("sty"))
    candidates, held = select_songs(songs, proof["works"])
    if not candidates:
        return {"status": "no_verified_typed_songs", "items": 0, "held": held}
    doc = dict(url=url, sha=src["sha256"], reading_key=digest(identity), envelope_utf8=json_bytes(cached).decode(),
               authority_key=authority_sha, sty_sha=hashlib.sha256(detail["sty"].encode()).hexdigest())
    preview = repository.publish_kopis_typed_recital(performance_id, doc, candidates, None)
    if not apply or preview["status"] != "ready":
        return {**preview, "held": held}
    expected = preview["program"]
    if [(r["position"], r["work_id"], r["display_title"]) for r in expected] != [
        (c["position"], c["work_id"], songs[c["position"]]["literal"]) for c in candidates
    ] or any(r["performed_scope"] != "unknown" or r["scope_details"] != [] for r in expected):
        raise ValueError("Official programme preview changed")
    detail_now = kopis.get_performance_detail(detail["mt20id"]).raw_payload
    if any(detail_now.get(k) != detail.get(k) for k in (*_DETAIL, "sty")):
        return {"status": "official_detail_changed", "items": 0, "held": held}
    data, mime = download_source(client, url)
    live = hashlib.sha256(data).hexdigest()
    if live != src["sha256"] or mime != src["content_type"]:
        return {"status": "cover_changed", "items": 0, "held": held}
    doc.update(live_sha=live, content_type=mime, live_detail={k:detail_now[k] for k in _DETAIL},
               live_sty_sha=hashlib.sha256(detail_now["sty"].encode()).hexdigest(), checked_at=datetime.now(UTC).isoformat())
    return {**repository.publish_kopis_typed_recital(performance_id, doc, candidates, expected), "held": held}
