import json
from pathlib import Path

import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.program_catalog_repairs import build_repair_plan
from classic_hubble_pipeline.program_split import split_program_block
from classic_hubble_pipeline.work_matching import CanonicalWork
from classic_hubble_pipeline.work_catalog import source_id

MANIFEST = json.loads(
    (Path(__file__).parents[1] / "data/program-catalog-repairs.json").read_text()
)
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/program-repair-nine.json").read_text()
)


def test_verified_repertoire_repairs_reuse_import_identity():
    manifest = json.loads((Path(__file__).parents[1] / "data/composer-repertoire-repairs.json").read_text())
    composers = [{"id": name, "name": name} for name in {r["composer"] for r in manifest["repairs"]}]
    plan = build_repair_plan(manifest, [], composers)
    assert len(plan["new_works"]) == 4
    for work, repair in zip(plan["new_works"], manifest["repairs"], strict=True):
        assert work["id"] == source_id(repair["identity_url"].split("/")[-1])
    assert not build_repair_plan(manifest, plan["new_works"], composers)["new_works"]
    bad = dict(manifest["repairs"][0], identity_url="https://www.wikidata.org/wiki/Q1")
    with pytest.raises(ValueError, match="identity"):
        build_repair_plan({"repairs": [bad]}, [], composers)


@pytest.mark.parametrize(
    "case", FIXTURE["cases"], ids=lambda case: case["expected_slug"]
)
def test_nine_real_failures_resolve_to_source_verified_work(case):
    plan = build_repair_plan(MANIFEST, FIXTURE["works"], FIXTURE["composers"])
    composers = {c["id"]: c for c in FIXTURE["composers"]}
    catalogue = {w["id"]: dict(w) for w in FIXTURE["catalogue"]}
    for work in plan["new_works"]:
        c = composers[work["composer_id"]]
        catalogue[work["id"]] = {
            "id": work["id"],
            "slug": work["slug"],
            "titles": [t for t in (work["title"], work["title_ko"]) if t],
            "composers": [n for n in (c["name"], c.get("name_ko")) if n],
            "catalogue": work["catalogue"],
            "aliases": [],
        }
    for update in plan["updates"]:
        catalogue[update["id"]]["catalogue"] = update["catalogue"]
    for alias in plan["aliases"]:
        catalogue[alias["work_id"]]["aliases"] = [
            *catalogue[alias["work_id"]]["aliases"],
            alias["alias"],
        ]
    matcher = MusicMatcher(
        [
            CanonicalWork(
                **{
                    **w,
                    **{k: tuple(w[k]) for k in ("titles", "composers", "aliases")},
                    "requires_review": False,
                }
            )
            for w in catalogue.values()
        ]
    )
    results = split_program_block(case, matcher)
    assert len(results) == 1
    assert catalogue[results[0]["work_id"]]["slug"] == case["expected_slug"]


def test_repair_plan_rejects_wrong_composer_and_changed_catalogue():
    repair = MANIFEST["repairs"][1]
    composer = {"id": "c", "name": repair["composer"]}
    work = {
        "id": "w",
        "slug": repair["slug"],
        "composer_id": "c",
        "catalogue": "Op. 100",
    }
    with pytest.raises(ValueError, match="catalogue"):
        build_repair_plan({"repairs": [repair]}, [work], [composer])
    work["catalogue"] = None
    work["composer_id"] = "other"
    with pytest.raises(ValueError, match="composer"):
        build_repair_plan({"repairs": [repair]}, [work], [composer])


def test_new_work_has_stable_identity_and_source_and_is_not_duplicated():
    repair = MANIFEST["repairs"][6]
    composer = {"id": "c", "name": repair["composer"]}
    plan = build_repair_plan({"repairs": [repair]}, [], [composer])
    assert plan["new_works"][0]["composer_id"] == "c"
    assert plan["provenance"][0]["payload"]["source_url"] == repair["source_url"]
    again = build_repair_plan({"repairs": [repair]}, plan["new_works"], [composer])
    assert again["new_works"] == []
    assert again["updates"] == []


def test_catalogue_repair_is_idempotent_and_requires_a_source():
    repair = MANIFEST["repairs"][1]
    work = {
        "id": "w",
        "slug": repair["slug"],
        "composer_id": "c",
        "catalogue": repair["catalogue"],
    }
    composer = {"id": "c", "name": repair["composer"]}
    assert build_repair_plan({"repairs": [repair]}, [work], [composer])["updates"] == []
    with pytest.raises(ValueError, match="source"):
        build_repair_plan(
            {"repairs": [{**repair, "source_url": ""}]}, [work], [composer]
        )
