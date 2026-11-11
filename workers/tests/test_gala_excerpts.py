from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest

from classic_hubble_pipeline import direct_movement_publication as mp
from classic_hubble_pipeline.music_extraction import json_bytes


def test_gala_suggests_only_literal_parent_and_distinct_excerpt_on_the_same_programme_line():
    credit = {"line_id": "L000003", "quote": "베르디"}
    title = {"line_id": "L000006", "quote": "Rigoletto"}
    part = {"line_id": "L000006", "quote": "Caro nome"}
    ref = dict(context="program", scope="excerpt", composer=[credit], title=[title], movements=[[part]], key=None, catalogue=None)
    row = dict(source_index=0, context="program", scope="excerpt", reason="scope_requires_review",
               identity_reason="no_candidate", candidate_ids=[], evidence=ref,
               fields=dict(composer="베르디", title="Rigoletto", movements=["Caro nome"], catalogue=None, key=None))
    proof = dict(printed_composer="베르디", works=[dict(printed_title="Rigoletto", work_id="w")])
    frozen = dict(validation_status="complete", warnings=[], source_warnings=[], rejected_items=[], items=[row])
    assert mp.gala_candidates(frozen, proof) == [{"index": 0, "work_id": "w", "scope": "excerpt"}]
    for field, value in (("scope","full_work"), ("context","biography"), ("scoped_work_id","different"),
                         ("candidate_ids",["other"]), ("reason","work_details_conflict"), ("derived_from",0)):
        assert mp.gala_candidates({**frozen, "items":[{**row,field:value}]},proof)==[]
    for field, value in (("movements",[[{**part,"line_id":"L000007"}]]), ("scope","full_work"),
                         ("title",[{**title,"quote":"Rigolet"}]), ("composer",[{**credit,"quote":"다른 작곡가"}])):
        bad=deepcopy(row);bad["evidence"][field]=value
        assert mp.gala_candidates({**frozen,"items":[bad]},proof)==[]
    for bad in ({**proof,"works":proof["works"]*2}, {**proof,"printed_composer":"동명이인"}):
        assert mp.gala_candidates(frozen,bad)==[]
    assert mp.gala_candidates({**frozen,"items":[row,row]},proof)==[]


def test_private_gala_proof_must_bind_event_and_verify_both_archived_source_bytes():
    server = {}
    def put(prefix, data):
        key = sha256(data).hexdigest()
        server[f"{prefix}/sha256/{key[:2]}/{key}"] = data
        return key
    calendar, catalogue = put("originals", b"calendar"), put("originals", b"catalogue")
    proof = dict(purpose="named_gala_excerpts_v1", edition_identified=False, performance_id="p",
                 date="2026-10-22", event_title="Gala", source_sha="s", works=[{"work_id":"w"}],
                 calendar={"sha256":calendar}, catalogue_source={"sha256":catalogue})
    key = put("extractions", json_bytes(proof))
    store = SimpleNamespace(read=server.__getitem__)
    target = dict(title="Gala", starts_on="2026-10-22")
    assert mp._gala_proof(store, key, target, "p", "s") == proof
    assert mp._gala_proof(store, key, {**target,"starts_on":"2026-10-23"}, "p", "s") is None
    assert mp._gala_proof(store, key, target, "other", "s") is None
    assert mp._gala_proof(store, key, target, "p", "changed") is None
    server[f"originals/sha256/{catalogue[:2]}/{catalogue}"] = b"wrong"
    with pytest.raises(ValueError, match="source identity mismatch"):
        mp._gala_proof(store, key, target, "p", "s")
