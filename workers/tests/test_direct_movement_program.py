from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from classic_hubble_pipeline import direct_movement_publication as mp


def verified():
    return dict(source_index=1, context="program", identity_reason="composer_and_catalogue",
                reason="scope_requires_review", scope="unknown", scoped_work_id="w", candidate_ids=["w"],
                fields={"composer":"P. I. Tchaikovsky","title":"Symphony No.4","catalogue":"Op.36",
                        "key":"f minor","movements":["I. Andante","II. Andantino"]},
                evidence={"scope":"full_work"})


def result(row):
    return dict(validation_status="complete", source_warnings=[], rejected_items=[], warnings=[], items=[row])


def test_only_shared_stable_catalogue_identity_and_printed_scope_are_submitted():
    old=verified()
    assert mp.aligned_movement_matches(result(old),result(deepcopy(old)))==[{"index":1,"work_id":"w","scope":"unknown"}]
    for scope in ("excerpt","movement"):
        old["scope"]=scope
        assert mp.aligned_movement_matches(result(old),result(deepcopy(old)))[0]["scope"]==scope


@pytest.mark.parametrize("overrides",[
    {"candidate_ids":["w","other"]},{"identity_reason":"no_candidate"},{"reason":"explicit_key_conflict"},
    {"scoped_work_id":"other","candidate_ids":["other"]},{"scope":"full_work"},{"context":"biography"},
    {"source_index":3},{"fields":{**verified()["fields"],"movements":[]}},{"evidence":{"scope":"arrangement"}},
    {"derived_from":"previous"},{"identity_reason":"composer_and_alias"}
])
def test_stale_or_uncertain_either_side_stays_private(overrides):
    old=verified()
    assert mp.aligned_movement_matches(result(old),result({**deepcopy(old),**overrides}))==[]
    assert mp.aligned_movement_matches(result({**deepcopy(old),**overrides}),result(old))==[]


def test_source_with_another_date_or_invalid_reading_stays_private():
    row=verified()
    for override in ({"source_warnings":["multiple_performance_dates"]},{"validation_status":"rejected"},{"rejected_items":[1]},{"warnings":["duplicate_reference"]}):
        assert mp.aligned_movement_matches(result(row),{**result(row),**override})==[]


@pytest.mark.parametrize("mode",["preview","apply","stale_bytes","partial","stale_catalogue","protected"])
def test_direct_publication_verifies_archive_and_only_writes_an_unchanged_ready_packet(monkeypatch, mode):
    body=b"original";sha=hashlib.sha256(body).hexdigest();url="https://kopis.or.kr/upload/test.jpg"
    store=SimpleNamespace(bucket="classic-hubble-sources")
    target=dict(starts_on="2026-10-22",ends_on="2026-10-22",intro_image_urls=[url])
    source=dict(source_url=url,sha256=sha,performance_ids=["pid"],bucket=store.bucket,
                object_key=f"originals/sha256/{sha[:2]}/{sha}",content_type="image/jpeg")
    events=[]
    def resolve(pid, packet, candidates, expected):
        events.append("review" if expected is None else "write")
        assert pid=="pid" and packet["sha"]==sha and packet["url"]==url
        if mode=="protected":return {"status":"existing_program_preserved","items":0}
        public=[dict(position=1,work_id="w",performed_scope="unknown")]
        if expected is None:return {"status":"ready","items":1,"program":public}
        assert expected==public and packet["live_sha"]==sha and packet["checked_at"]
        return {"status":"published","items":1}
    repo=SimpleNamespace(load_vision_target=lambda _:target,load_vision_source=lambda _:source,publish_direct_movement_program=resolve)
    rd=dict(coverage="partial" if mode=="partial" else "complete",extraction_status="items_extracted",lines=[dict(text="2026.10.22(목) 19:30")])
    monkeypatch.setattr(mp,"_cached",lambda *_:dict(reading=rd,matching=result(verified())))
    monkeypatch.setattr(mp,"_original",lambda *_:events.append("archive"))
    monkeypatch.setattr(mp,"_match_reading",lambda *_:result({**verified(),"candidate_ids":[]} if mode=="stale_catalogue" else verified()))
    def live(_,u):
        events.append("live");assert u==url
        return (b"changed" if mode=="stale_bytes" else body),"image/jpeg"
    monkeypatch.setattr(mp,"download_source",live)
    final=mp.publish(repo,store,None,"pid",apply=mode!="preview")
    assert (final["status"],events)=={
        "partial":("incomplete_or_undated_reading",[]),
        "preview":("ready",["archive","review"]),"apply":("published",["archive","review","live","write"]),
        "stale_bytes":("source_changed",["archive","review","live"]),
        "stale_catalogue":("no_verified_catalogue_movements",["archive"]),
        "protected":("existing_program_preserved",["archive","review"])
    }[mode]
