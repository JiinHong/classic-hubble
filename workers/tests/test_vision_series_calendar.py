import copy
import hashlib
import json

import pytest

from classic_hubble_pipeline import vision_publication
from test_direct_vision import reading, run
from test_vision_publication import setup


@pytest.mark.parametrize("proof_ok,other_date,expected", [
    (True, False, "published"), (False, False, "date_binding_required"),
    (True, True, "date_binding_required"),
])
def test_only_proved_calendar_can_be_separated_from_a_complete_single_program(
    proof_ok, other_date, expected, monkeypatch,
):
    repo, store, target, writes = setup()
    repo.cached.clear()
    data = reading(store)
    original = data["lines"][:3]
    lines = (["2026. 10. 22 (목) 19:30"] + [v["text"] for v in original] + ["Artist"]
             + (["2026. 10. 23 (금) 19:30"] if other_date else [])
             + ["<위대한 작곡가> 시리즈 연간 공연 일정", "3 / 12", "10 / 22"])
    for key in ("composer", "title", "key", "catalogue"):
        ref = data["items"][0][key][0]
        ref["line_id"] = f"L{int(ref['line_id'][1:]) + 1:06}"
    data["lines"] = [{"text": value, "page_index": 0} for value in lines]
    run(repo, store, data, apply=True)
    stored = copy.deepcopy(repo.cached)
    proof = {"version": "direct-series-calendar-v1", "performance_date": target["starts_on"],
             "calendar_line": lines.index("<위대한 작곡가> 시리즈 연간 공연 일정"), "end_line": 4}

    def prove(raw, sha, day):
        assert json.loads(raw) == data and hashlib.sha256(raw.encode()).hexdigest() == sha
        assert day == target["starts_on"]
        return proof if proof_ok else None

    repo.load_direct_series_program = prove
    monkeypatch.setattr(vision_publication, "download_source", lambda *args: (store.source, "image/png"))
    assert vision_publication.publish(repo, store, None, "p1")["status"] == "date_binding_required"
    result = vision_publication.publish(repo, store, None, "p1", apply=True, series_calendar=True)
    assert result["status"] == expected and repo.cached == stored
    if expected == "published":
        assert len(writes) == 1
        ev = writes[0]["p_evaluation"]
        assert ev["series_program"] == proof and json.loads(ev["series_reading_utf8"]) == data
        assert ev["publication_version"] == "direct-vision-series-calendar-v1"
        assert writes[0]["p_items"][0]["work_id"] == "rach-2"
    else:
        assert not writes
