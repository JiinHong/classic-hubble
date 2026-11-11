import copy

import pytest

from classic_hubble_pipeline import paddle_publication as pub
from classic_hubble_pipeline.work_matching import CanonicalWork
from test_music_extraction import WORK, quote
from test_paddle_publication import save, setup


PARENT = CanonicalWork("group-id", "poulenc-quinze-improvisations",
                       ("Les Quinze Improvisations",), ("Francis Poulenc", "프랑시스 풀랑크"), None)
RANGES = ["제7번~제12번", "제1번~제6번,제13번~제15번"]


def run(monkeypatch, *, change=None, skip_parent=False):
    def prepare(d):
        lines = ["2026. 10. 21 [수]", "Program", "10월 21일(수)", "Other",
                 "Other work", "10월 22일(목)", "프랑시스 풀랑크", "즉흥곡 " + RANGES[0],
                 "Sergei Rachmaninoff", "Piano Concerto No. 2 in C minor, Op. 18",
                 "프랑시스 풀랑크", "즉흥곡 " + RANGES[1], "Artist"]
        d["lines"] = [{"text": t, "score": .99} for t in lines]
        if change == "additional_text":
            d["lines"][7]["text"] += " 연주하지 않음"
        if change == "low_score":
            d["lines"][7]["score"] = .8

    repo, store, data = setup(prepare)
    repo.load_work_catalog = lambda: [WORK] if skip_parent else [WORK, PARENT]
    repo.load_ocr_results_for_sources = lambda *_: repo.load_ocr_results()
    repo.publish_paddle_program_bundle = repo.publish_paddle_program
    repo.load_paddle_program_section = lambda *_: dict(version="dated-program-section-v1",
        performance_date="2026-10-22", heading_line=5, end_line=12)
    calls = []

    def resolve(ref, composer_line, title_line):
        calls.append(ref)
        assert ref["scope"] == "excerpt"
        if composer_line != ref["composer"][0]["quote"] or title_line != ref["title"][0]["quote"]:
            return None
        return PARENT.id

    repo.load_paddle_numbered_excerpt = resolve
    middle = data["items"][0]
    middle.update(composer=quote(8, "Sergei Rachmaninoff"),
                  title=quote(9, "Piano Concerto No. 2 in C minor, Op. 18"), key=None,
                  catalogue=quote(9, "Op. 18"), movements=[])
    outer = [dict(context="program", scope="excerpt", key=None, catalogue=None,
                  composer=quote(i-1, "프랑시스 풀랑크"), title=quote(i, "즉흥곡 "+r),
                  movements=[quote(i, part) for part in r.split(",")])
             for i, r in zip((7, 11), RANGES)]
    if change == "no_ranges":
        outer[0]["movements"] = []
    if change == "wrong_scope":
        outer[0]["scope"] = "full_work"
    if change == "outside":
        outer[0]["composer"] = quote(3, "Other")
    data["items"] = [outer[0], middle, outer[1]]
    rid = save(repo, store, data)
    monkeypatch.setattr(pub, "download_source", lambda *_: (store.original, "image/png"))
    assert pub.publish_bundle(repo, store, None, "p1", [rid])["items"] == 0
    assert calls == []
    result = pub.publish_bundle(repo, store, None, "p1", [rid], apply=True, dated_program=True)
    return result, repo.writes[0], calls, copy.deepcopy(outer)


def test_keeps_separate_numbered_excerpt_slots_in_original_order(monkeypatch):
    result, payload, calls, outer = run(monkeypatch)
    assert result == {"status": "published", "items": 3}
    assert calls == outer
    items = payload["p_items"]
    assert [(r["work_id"], r["performed_scope"], r["scope_details"]) for r in items] == [
        (PARENT.id, "excerpt", [RANGES[0]]), (WORK.id, "full_work", []),
        (PARENT.id, "excerpt", RANGES[1].split(","))]
    rows = payload["p_documents"][0]["matching"]["items"]
    assert all(rows[i]["identity_reason"] == "composer_and_numbered_excerpt"
               and rows[i]["suggested_work_id"] is None for i in (0, 2))


@pytest.mark.parametrize("change", ["additional_text", "low_score", "no_ranges", "wrong_scope", "outside"])
def test_rejects_weak_or_unbound_excerpt_without_hiding_other_items(monkeypatch, change):
    result, payload, _, _ = run(monkeypatch, change=change)
    assert result["items"] == 2
    assert [r["position"] for r in payload["p_items"]] == [0, 1]
    assert payload["p_items"][1]["scope_details"] == RANGES[1].split(",")


def test_stale_or_missing_canonical_parent_stays_private(monkeypatch):
    result, payload, _, _ = run(monkeypatch, skip_parent=True)
    assert result["items"] == 1 and payload["p_items"][0]["work_id"] == WORK.id
