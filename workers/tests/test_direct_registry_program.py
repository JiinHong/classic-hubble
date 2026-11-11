from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from classic_hubble_pipeline import direct_movement_publication as mp


def rows():
    pair = []
    for index, (title, author, key, opus, moves) in enumerate([
        ("Salve Regina", "Arvo Pärt", None, None, []),
        ("Requiem", "W. A. Mozart", "D minor", "K. 626", ["1. Requiem", "2. Kyrie"]),
    ]):
        fields = dict(title=title, composer=author, key=key, catalogue=opus, movements=moves)
        pair.append(dict(source_index=index, fields=fields, evidence={"scope":"full_work","context":"program"},
            context="program", scope="unknown" if moves else "full_work",
            suggested_work_id=None if moves else "part", scoped_work_id="mozart" if moves else None,
            candidate_ids=["mozart" if moves else "part"], reason="scope_requires_review" if moves else "composer_and_alias",
            identity_reason="composer_and_catalogue" if moves else "composer_and_alias"))
    current=dict(validation_status="complete", warnings=[], source_warnings=[], rejected_items=[], items=pair)
    old=deepcopy(current)
    old["items"][1].update(identity_reason="no_candidate",scoped_work_id=None,candidate_ids=[])
    return old,current,{"mozart":"b"*64,"part":"a"*64}


def test_independent_parent_proof_links_newly_catalogued_work_without_claiming_edition_or_extent():
    old,new,proofs=rows()
    assert mp.registry_candidates(old,new,proofs)==[
        {"index":0,"work_id":"part","scope":"unknown","authority_key":"a"*64},
        {"index":1,"work_id":"mozart","scope":"unknown","authority_key":"b"*64}]
    assert old["items"][1]["scoped_work_id"] is None


@pytest.mark.parametrize("change",["new_warnings","old_ambiguous","old_conflict","stale_literals","stale_reference",
                                   "new_ambiguous","new_conflict","missing_key","no_current_proof","invalid_proof",
                                   "nonprogram","no_number","no_movements","duplicate_old_index","derived","arrangement"])
def test_a_new_catalogue_snapshot_cannot_override_ambiguity_or_supply_unprinted_details(change):
    old,new,proofs=rows();o,n=old["items"][1],new["items"][1]
    if change=="new_warnings":new["source_warnings"]=["multiple_performance_dates"]
    if change=="old_ambiguous":o["candidate_ids"]=["one","two"]
    if change=="old_conflict":o["identity_reason"]="explicit_key_conflict"
    if change=="stale_literals":o["fields"]["key"]="D Major"
    if change=="stale_reference":o["evidence"]["scope"]="excerpt"
    if change=="new_ambiguous":n["candidate_ids"].append("another")
    if change=="new_conflict":n["identity_reason"]="composer_and_alias"
    if change=="missing_key":o["fields"]["key"]=n["fields"]["key"]=None
    if change=="no_current_proof":del proofs["mozart"]
    if change=="invalid_proof":proofs["mozart"]="some-key"
    if change=="nonprogram":o["context"]="biography"
    if change=="no_number":o["fields"]["catalogue"]=n["fields"]["catalogue"]=None
    if change=="no_movements":o["fields"]["movements"]=n["fields"]["movements"]=[]
    if change=="duplicate_old_index":old["items"].append(deepcopy(o))
    if change=="derived":n["derived_from"]="previous"
    if change=="arrangement":o["scope"]=n["scope"]="arrangement"
    assert all(r["work_id"]!="mozart" for r in mp.registry_candidates(old,new,proofs))


def test_title_only_still_requires_the_same_positive_canonical_id_and_no_inferred_scope():
    old,new,proofs=rows();old["items"][0].update(suggested_work_id=None,candidate_ids=[],identity_reason="no_candidate")
    assert [r["work_id"] for r in mp.registry_candidates(old,new,proofs)]==["mozart"]
    old,new,proofs=rows();new["items"][0]["scope"]="excerpt"
    assert [r["work_id"] for r in mp.registry_candidates(old,new,proofs)]==["mozart"]


@pytest.mark.parametrize("tampered",[True,False])
def test_worker_verifies_authority_archive_before_contacting_publication(monkeypatch,tampered):
    old,new,_=rows();url="https://kopis.or.kr/upload/example.jpg";orig="1"*64
    proof=b"saved independent attribution";key=hashlib.sha256(proof).hexdigest();seen=[]
    def read(k):
        seen.append(k)
        return b"changed" if tampered else proof
    store=SimpleNamespace(bucket="classic-hubble-sources",read=read)
    target=dict(starts_on="2026-10-22",ends_on="2026-10-22",intro_image_urls=[url])
    src=dict(source_url=url,sha256=orig,bucket=store.bucket,performance_ids=["pid"],object_key=f"originals/sha256/11/{orig}")
    def submit(pid,packet,candidates,expected):
        seen.append("preview");assert expected is None and packet["identity_mode"]=="independent_parent_registry_v1"
        assert [c["authority_key"] for c in candidates]==[key]
        return {"status":"parent_authority_unverified","items":0}
    repo=SimpleNamespace(load_vision_target=lambda _:target,load_vision_source=lambda _:src,publish_direct_movement_program=submit)
    monkeypatch.setattr(mp,"_original",lambda *_:None)
    rd=dict(coverage="complete",extraction_status="items_extracted",lines=[dict(text="2026.10.22(목) 19:30")])
    monkeypatch.setattr(mp,"_cached",lambda *_:dict(reading=rd,matching=old))
    monkeypatch.setattr(mp,"_match_reading",lambda *_:new)
    if tampered:
        with pytest.raises(ValueError,match="authority archive mismatch"):
            mp.publish(repo,store,None,"pid",authorities={"part":key})
    else:
        assert mp.publish(repo,store,None,"pid",apply=True,authorities={"part":key})["status"]=="parent_authority_unverified"
    assert seen==[f"extractions/sha256/{key[:2]}/{key}"]+([] if tampered else ["preview"])
