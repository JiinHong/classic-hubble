from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.program_repair import plan_program_repairs
from classic_hubble_pipeline.work_matching import CanonicalWork


def test_repair_keeps_existing_links_and_resequences_only_target_performance():
    m = MusicMatcher(
        [
            CanonicalWork("a", "a", ("Work A",), ("Composer",), "Op.1"),
            CanonicalWork("b", "b", ("Work B",), ("Composer",), "Op.2"),
        ]
    )
    source = {
        "id": "x",
        "performance_id": "p",
        "source_provider": "nol",
        "display_title": "Composer / Work A Op.1\nComposer / Work B Op.2",
        "composer_name": None,
        "work_id": None,
        "position": 1,
        "source_url": "https://source.test/1",
        "source_type": "official",
        "confidence": 0.98,
    }
    linked = {
        **source,
        "id": "linked",
        "work_id": "existing",
        "display_title": "Untouched",
        "position": 0,
    }
    plans = plan_program_repairs([linked, source], m, {"x"})
    assert len(plans) == 1
    plan = plans[0]
    assert [r["work_id"] for r in plan["items"]] == ["existing", "a", "b"]
    assert [r["position"] for r in plan["items"]] == [0, 1, 2]
    assert plan["expected"][1]["display_title"] == source["display_title"]
    assert plan["items"][0]["display_title"] == "Untouched"
    assert all(r["source_url"] == source["source_url"] for r in plan["items"])


def test_second_pass_does_not_produce_the_same_repair():
    m = MusicMatcher([CanonicalWork("a", "a", ("Work A",), ("Composer",), "Op.1")])
    row = {
        "id": "x",
        "performance_id": "p",
        "source_provider": "nol",
        "display_title": "Work A Op.1",
        "composer_name": "Composer",
        "work_id": "a",
        "position": 0,
    }
    assert plan_program_repairs([row], m, {"x"}) == []


def test_non_nol_rows_are_never_replaced():
    m = MusicMatcher([])
    row = {
        "id": "x",
        "performance_id": "p",
        "source_provider": "manual",
        "display_title": "Unknown",
        "composer_name": None,
        "work_id": None,
        "position": 0,
    }
    assert plan_program_repairs([row], m, {"x"}) == []
