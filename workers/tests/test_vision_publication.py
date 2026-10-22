import copy
import importlib
import importlib.util

import httpx
import pytest

from test_direct_vision import Repository, Store, reading, run


def module():
    name = "classic_hubble_pipeline.vision_publication"
    assert importlib.util.find_spec(name), "Atomic direct-vision publication is missing"
    return importlib.import_module(name)


def setup():
    store = Store()
    repo = Repository(store)
    data = reading(store)
    data["lines"].append({"text": "2026. 10. 22.(목) 19:30", "page_index": 0})
    run(repo, store, data, apply=True)
    target = {
        "id": "p1", "title": "Test concert", "starts_on": "2026-10-22",
        "ends_on": "2026-10-22", "intro_image_urls": [repo.sources[0]["source_url"]],
    }
    repo.load_vision_target = lambda _: copy.deepcopy(target)
    repo.load_vision_source = lambda _: copy.deepcopy(repo.sources[0])
    writes = []
    repo.publish_direct_vision = lambda payload: writes.append(payload) or {"status": "published", "items": 1}
    return repo, store, target, writes


def test_dry_run_revalidates_saved_pixels_and_catalogue_without_public_write():
    repo, store, _, writes = setup()
    with httpx.Client() as client:
        result = module().publish(repo, store, client, "p1")
    assert result["status"] == "ready"
    assert result["items"] == 1
    assert not writes


def test_apply_rechecks_live_source_and_sends_one_atomic_request(monkeypatch):
    repo, store, target, writes = setup()
    monkeypatch.setattr(module(), "download_source", lambda client, url: (store.source, "image/png"))
    with httpx.Client() as client:
        result = module().publish(repo, store, client, "p1", apply=True)
    assert result["status"] == "published"
    assert len(writes) == 1
    payload = writes[0]
    assert payload["p_expected_performance"] == target
    assert payload["p_source"] == repo.sources[0]
    assert payload["p_reading"] == next(iter(repo.cached.values()))
    assert payload["p_evaluation"]["matching"]["items"][0]["scope"] == "full_work"
    assert payload["p_evaluation"]["performance_date"] == "2026-10-22"
    assert payload["p_items"][0]["work_id"] == "rach-2"
    assert "confidence" not in payload["p_items"][0]


@pytest.mark.parametrize("problem", ["multiple_images", "range", "partial", "unmatched", "unread", "association"])
def test_incomplete_or_ambiguous_program_is_not_published(problem, monkeypatch):
    repo, store, target, writes = setup()
    if problem == "multiple_images":
        target["intro_image_urls"].append("https://kopis.or.kr/upload/other.jpg")
    elif problem == "range":
        target["ends_on"] = "2026-10-23"
    elif problem == "partial":
        repo.cached.clear()
        data = reading(store)
        data["coverage"] = "partial"
        run(repo, store, data, apply=True)
    elif problem == "unmatched":
        repo.works = []
    elif problem == "unread":
        repo.cached.clear()
    else:
        repo.sources[0]["performance_ids"] = ["other"]
    monkeypatch.setattr(module(), "download_source", lambda *args: pytest.fail("No download for ineligible program"))
    with httpx.Client() as client:
        result = module().publish(repo, store, client, "p1", apply=True)
    assert result["status"] != "published"
    assert not writes


def test_replaced_live_bytes_stop_publication(monkeypatch):
    repo, store, _, writes = setup()
    monkeypatch.setattr(module(), "download_source", lambda *args: (b"replaced image", "image/png"))
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1", apply=True)["status"] == "source_changed"
    assert not writes


def test_rpc_stale_result_is_returned_not_counted_as_published(monkeypatch):
    repo, store, _, _ = setup()
    monkeypatch.setattr(module(), "download_source", lambda *args: (store.source, "image/png"))
    repo.publish_direct_vision = lambda _: {"status": "stale", "items": 0}
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1", apply=True) == {"status": "stale", "items": 0}


@pytest.mark.parametrize("date_text", [None, "10월23일(금)", "2025.10.22.(수)"])
def test_poster_date_must_support_target_performance(date_text):
    repo, store, _, writes = setup()
    repo.cached.clear()
    data = reading(store)
    if date_text:
        data["lines"].append({"text": date_text, "page_index": 0})
    run(repo, store, data, apply=True)
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1")["status"] == "date_binding_required"
    assert not writes


def test_korean_month_day_uses_the_target_year():
    repo, store, _, _ = setup()
    repo.cached.clear()
    data = reading(store)
    data["lines"].append({"text": "10월22일(목) 오후7시30분", "page_index": 0})
    run(repo, store, data, apply=True)
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1")["status"] == "ready"


@pytest.mark.parametrize("date_text", [
    "2026. 10. 22 TUR 7:30 PM",  # The original PF299019 really prints TUR.
    "2026.10.22 THU 19:30",
    "2026. 10. 22 [목] 오후 7시 30분",
    "2026/10/22 Thursday 19:30",
    "10.22 (THUR) 19:30 | 부산콘서트홀",
])
def test_observed_date_headings_bind_without_rewriting_the_reading(date_text):
    repo, store, _, writes = setup()
    repo.cached.clear()
    data = reading(store)
    data["lines"].append({"text": date_text, "page_index": 0})
    run(repo, store, data, apply=True)
    before = copy.deepcopy(repo.cached)
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1")["status"] == "ready"
    assert repo.cached == before
    assert not writes


@pytest.mark.parametrize("headers", [
    ["2025.10.22 THU 19:30"],
    ["2026.10.23 [금] 19:30"],
    ["Biography: debuted 2026.10.22 THU in Seoul"],
    ["2026.10.22 THURSDAYISH"],
    ["2026.10.22 THU", "2026.10.23 [금]"],
    ["2026.10.22 THU & 10.23 FRI"],
    ["2026.10.22 THU ~ 23 FRI"],
    ["2026.10.22 THU 2026.10.23 FRI"],
    ["2026.10.22 THU", "2026.02.30 [월]"],
])
def test_new_heading_forms_cannot_bypass_single_valid_date_binding(headers, monkeypatch):
    repo, store, _, writes = setup()
    repo.cached.clear()
    data = reading(store)
    data["lines"].extend({"text": text, "page_index": 0} for text in headers)
    run(repo, store, data, apply=True)
    monkeypatch.setattr(module(), "download_source", lambda *args: pytest.fail("No source download"))
    with httpx.Client() as client:
        assert module().publish(repo, store, client, "p1", apply=True)["status"] == "date_binding_required"
    assert not writes
