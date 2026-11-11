import hashlib
from types import SimpleNamespace

import pytest

from classic_hubble_pipeline.kopis_typed_recital import parse_program, select_songs


PROGRAM = "[PROGRAM]\nSop. 주수연 · Kl. 이고은\nDas Mädchen, D 652\n\n— Pause —\nTen. 조창후 · Kl. 이고은\nDie Nebensonnen, D 911 No. 23\nDas Mädchen, D 7"


def test_separates_people_dates_and_member_from_work_identity():
    songs = parse_program(PROGRAM)
    assert [(i["position"], i["line"], i["title"], i["number"], i["member"]) for i in songs] == [
        (0, 2, "Das Mädchen", "652", None), (1, 6, "Die Nebensonnen", "911", "23"),
        (2, 7, "Das Mädchen", "7", None),
    ]
    valid = {"work_id": "unique-652", "number": "652", "title_forms": ["Das Mädchen"], "member": None}
    refs = [valid, {**valid, "number": "911", "work_id": "cycle", "title_forms": ["Die Nebensonnen"]}]
    yes, held = select_songs(songs, refs)
    assert yes == [{"position": 0, "line": 2, "work_id": "unique-652"}]
    assert held == {1: "member_identity_not_verified", 2: "no_verified_title_and_number"}
    assert select_songs(songs, [valid, {**valid, "work_id": "other"}])[1][0] == "ambiguous_authority"


@pytest.mark.parametrize("change", [
    lambda s:s.replace("[PROGRAM]", "[PROFILE]"), lambda s:s.replace("Sop. 주수연 · Kl. 이고은\n",""),
    lambda s:s+"\n2026.10.21", lambda s:s+"\nSop. 주수연 · Kl. 이고은",
    lambda s:s.replace("D 652","D 652b"), lambda s:s.replace("No. 23","No. 23-24"),
    lambda s:s.replace("D 652","D 652 (arr.)"), lambda s:s.replace("D 652","D 0"),
    lambda s:s.replace("Das Mädchen, D 652","[다른 날짜]\nDas Mädchen, D 652"),
    lambda s:s.replace("— Pause —","이력"), lambda s:s.replace("Ten. 조창후 · Kl. 이고은","다른 작곡가"),
    lambda s:s.replace("Das Mädchen, D 652","2026-10-22, D 652"),
    lambda s:s.replace("— Pause —","— Pause —\n— Pause —"),
])
def test_unknown_sections_fail_closed(change):
    assert parse_program(change(PROGRAM)) == []


@pytest.mark.parametrize("change,status", [
    ("none", "published"), ("no_apply", "ready"), ("existing", "unchanged"),
    ("changed_title", "official_detail_changed"), ("changed_songs", "official_detail_changed"),
    ("changed_cover", "cover_changed"), ("poster_has_songs", "not_cover_only"),
    ("changed_authority", "error"), ("changed_preview", "error"),
])
def test_archive_fresh_official_detail_and_image_bytes_before_writing(monkeypatch, change, status):
    from classic_hubble_pipeline import kopis_typed_recital as pub
    from classic_hubble_pipeline.music_extraction import json_bytes

    h = lambda b: hashlib.sha256(b).hexdigest()
    cover = b"dated cover"
    sha = h(cover)
    packet = json_bytes({"purpose": "schubert_lied_identities_v1", "works": [
        {"work_id": "song", "number": "652", "title_forms": ["Das Mädchen"], "member": None}]})
    key = h(packet)
    store = SimpleNamespace(bucket="classic-hubble-sources", read=lambda k: packet + (b"!" if change == "changed_authority" else b""))
    detail = dict(mt20id="PF000001", prfnm="recital", prfpdfrom="2026.10.22", prfpdto="2026.10.22",
                  dtguidance="목요일(19:30)", fcltynm="예술의전당 (리사이틀홀)", styurls={"styurl": "cover"}, sty=PROGRAM)
    rpc, fresh, original = [], [], []
    def call(pid, doc, selected, expected):
        rpc.append(expected)
        assert pid == "concert" and doc["sty_sha"] == h(PROGRAM.encode()) and selected == [{"position": 0, "line": 2, "work_id": "song"}]
        if change == "existing":
            return {"status": "unchanged", "items": 1}
        if expected is None:
            return {"status": "ready", "items": 1, "program": [dict(position=0, work_id="song", display_title="Das Mädchen, D 652",
                performed_scope="full_work" if change == "changed_preview" else "unknown", scope_details=[])]}
        assert doc["live_sha"] == sha and doc["live_sty_sha"] == doc["sty_sha"] and doc["live_detail"]["mt20id"] == detail["mt20id"]
        return {"status": "published", "items": 1}
    def current(kid):
        fresh.append(kid)
        return SimpleNamespace(raw_payload={**detail, **({"prfnm": "replaced"} if change == "changed_title"
            else {"sty": PROGRAM+" changed"} if change == "changed_songs" else {})})
    repo = SimpleNamespace(load_vision_target=lambda p: dict(title="recital", starts_on="2026-10-22", ends_on="2026-10-22", intro_image_urls=["cover"]),
        load_vision_source=lambda u: dict(source_url=u, bucket=store.bucket, sha256=sha, content_type="image/jpeg", performance_ids=["concert"],
            object_key="originals/sha256/"+sha[:2]+"/"+sha), publish_kopis_typed_recital=call)
    monkeypatch.setattr(pub, "_original", lambda s,i:original.append(i["source_sha256"]))
    monkeypatch.setattr(pub, "_cached", lambda *_:{"reading": {"extraction_status":"items_extracted" if change=="poster_has_songs" else "no_program_identified"}})
    monkeypatch.setattr(pub, "download_source", lambda c,u:(b"replacement" if change=="changed_cover" else cover, "image/jpeg"))
    run = lambda:pub.publish(repo,store,None,SimpleNamespace(get_performance_detail=current),"concert",detail,key,apply=change!="no_apply")
    if status=="error":
        with pytest.raises(ValueError):
            run()
    else:
        assert run()["status"]==status
    assert len([v for v in rpc if v is not None])==int(status=="published")
    assert len(original)==int(change!="poster_has_songs")
    assert len(fresh)==int(change in {"none","changed_title","changed_songs","changed_cover"})
