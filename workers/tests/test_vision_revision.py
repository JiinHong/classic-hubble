"""Synthetic correction evidence exercises private revisions, not OCR accuracy."""
import copy
import importlib
import importlib.util

import pytest

from classic_hubble_pipeline import direct_vision
from classic_hubble_pipeline.music_extraction import digest, json_bytes
from test_direct_vision import Repository, Store, reading, run


def module():
    name = "classic_hubble_pipeline.vision_revision"
    assert importlib.util.find_spec(name), "Atomic private reading revision is missing"
    return importlib.import_module(name)


class RevisionRepository(Repository):
    def __init__(self, store):
        super().__init__(store)
        self.proposal = None
        self.promotions = []
        self.history = []
        self.rpc_status = "revised"

    def load_vision_correction(self, proposal_id):
        return copy.deepcopy(self.proposal)

    def revise_direct_vision(self, payload):
        self.promotions.append(copy.deepcopy(payload))
        if self.rpc_status == "revised":
            assert self.cached[payload["p_key"]] == payload["p_expected_reading"]
            self.history.append(copy.deepcopy(self.cached[payload["p_key"]]))
            self.cached[payload["p_key"]] = copy.deepcopy(payload["p_new_reading"])
        return {"status": self.rpc_status, "published_items": 0}


PROPOSAL_ID = "00000000-0000-0000-0000-000000000001"


def fixture():
    store = Store()
    repo = RevisionRepository(store)
    original = reading(store)
    original.update(items=[], extraction_status="no_program_identified", lines=[{"page_index": 0, "text": "Typo"}])
    run(repo, store, original, apply=True)
    identity = direct_vision._identity(store, store.sha)
    old = repo.load_direct_vision_result(digest(identity))
    corrected = copy.deepcopy(original)
    corrected["lines"][0]["text"] = "Correct"
    proposal = {
        "kind": "direct_reading_correction_proposal", "correction_contract_version": "private-correction-proposal-v1",
        "status": "pending_revision_workflow", "identity": identity,
        "active_reading_pointer_at_discovery": old, "supersedes_reading_sha256": digest(original),
        "corrected_reading": corrected, "corrected_reading_sha256": digest(corrected),
    }
    def persist():
        evidence = store.archive_extraction_result(proposal)
        repo.proposal = {"source_sha256": store.sha, "bucket": store.bucket, "status": "pending_revision_workflow",
            "result_sha256": evidence.sha256, "result_object_key": evidence.key,
            "supersedes_reading_sha256": digest(original), "corrected_reading_sha256": digest(corrected), "active_cache_replaced": False}
    persist()
    return repo, store, original, corrected, proposal, persist


def test_revision_dry_run_does_not_replace_observation_or_write_evidence():
    repo, store, original, corrected, _, _ = fixture()
    before = copy.deepcopy(repo.cached), copy.deepcopy(store.saved)
    result = module().promote_correction(repo, store, PROPOSAL_ID)
    assert result == {"status": "ready", "published_items": 0}
    assert (repo.cached, store.saved) == before and not repo.promotions


def test_revision_keeps_original_bytes_history_and_active_cache_and_is_idempotent():
    repo, store, original, corrected, proposal, _ = fixture()
    objects_before = copy.deepcopy(store.objects)
    result = module().promote_correction(repo, store, PROPOSAL_ID, apply=True)
    assert result == {"status": "revised", "published_items": 0}
    cached = direct_vision._cached(repo, store, proposal["identity"])
    assert cached["reading"] == corrected
    assert repo.history == [proposal["active_reading_pointer_at_discovery"]]
    assert all(store.objects[k] == v for k, v in objects_before.items())
    saved_count = len(store.saved)
    assert module().promote_correction(repo, store, PROPOSAL_ID, apply=True)["status"] == "unchanged"
    assert len(store.saved) == saved_count and len(repo.promotions) == 1
    with pytest.raises(ValueError, match="different reading"):
        run(repo, store, original, apply=True)


@pytest.mark.parametrize("problem", ["proposal_hash", "source_bytes", "corrected_hash", "other_source", "ungrounded", "missing"])
def test_invalid_revision_never_reaches_atomic_promotion(problem):
    repo, store, _, corrected, proposal, persist = fixture()
    if problem == "proposal_hash":
        store.objects[repo.proposal["result_object_key"]] += b"x"
    elif problem == "source_bytes":
        store.objects[store.key] += b"x"
    elif problem == "corrected_hash":
        proposal["corrected_reading_sha256"] = "a" * 64
        persist()
    elif problem == "other_source":
        proposal["identity"]["source_sha256"] = "b" * 64
        persist()
    elif problem == "ungrounded":
        corrected["items"] = reading(store)["items"]
        corrected["extraction_status"] = "items_extracted"
        proposal["corrected_reading_sha256"] = digest(corrected)
        persist()
    else:
        repo.proposal = None
    before = copy.deepcopy(repo.cached)
    with pytest.raises(ValueError):
        module().promote_correction(repo, store, PROPOSAL_ID, apply=True)
    assert repo.cached == before and not repo.promotions


def test_stale_expected_reading_is_not_replaced():
    repo, store, _, _, proposal, _ = fixture()
    repo.cached[digest(proposal["identity"])]["stored_at"] = "changed"
    assert module().promote_correction(repo, store, PROPOSAL_ID, apply=True)["status"] == "stale"
    assert not repo.promotions


@pytest.mark.parametrize("status", ["stale", "published_source_requires_reconciliation"])
def test_atomic_rpc_refusal_is_not_reported_as_a_success(status):
    repo, store, _, _, _, _ = fixture()
    repo.rpc_status = status
    before = copy.deepcopy(repo.cached)
    assert module().promote_correction(repo, store, PROPOSAL_ID, apply=True) == {"status": status, "published_items": 0}
    assert repo.cached == before and not repo.history


def test_source_refresh_during_validation_stops_before_upload(monkeypatch):
    repo, store, _, _, _, _ = fixture()
    original_sources = module()._sources
    calls = 0
    def sources(repository, identity):
        nonlocal calls
        calls += 1
        rows = original_sources(repository, identity)
        if calls == 2:
            rows[0]["checked_at"] = "changed"
        return rows
    monkeypatch.setattr(module(), "_sources", sources)
    saved_count = len(store.saved)
    assert module().promote_correction(repo, store, PROPOSAL_ID, apply=True)["status"] == "stale"
    assert not repo.promotions and len(store.saved) == saved_count
