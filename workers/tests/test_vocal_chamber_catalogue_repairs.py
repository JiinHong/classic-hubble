import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.program_catalog_repairs import build_repair_plan
from classic_hubble_pipeline.work_matching import CanonicalWork


CASES = [
    ("reviewed-schumann-dichterliebe-op48", "Robert Schumann", "R. Schumann", "Dichterliebe", "Op.48"),
    ("reviewed-bruckner-locus-iste-wab23", "Anton Bruckner", "A. Bruckner", "Locus iste", None),
    ("reviewed-schubert-der-tanz-d826", "Franz Schubert", "F.Schubert", "Der Tanz", None),
    ("reviewed-widor-flute-suite-op34", "Charles-Marie Widor", "C.M.Widor", "Suite for Flute and Piano", None),
]
COMPOSERS = [{"id": name, "name": name} for _, name, *_ in CASES]


def repaired_catalogue():
    manifest = json.loads(
        (Path(__file__).parents[1] / "data/ocr-vocal-chamber-repairs-20261025.json").read_text()
    )
    plan = build_repair_plan(manifest, [], COMPOSERS)
    works = [CanonicalWork(
        id=w["id"], slug=w["slug"], titles=(w["title"],), composers=(w["composer_id"],),
        catalogue=w["catalogue"],
        aliases=tuple(a["alias"] for a in plan["aliases"] if a["work_id"] == w["id"]),
    ) for w in plan["new_works"]]
    return works, plan


@pytest.mark.parametrize("slug,name,printed,title,catalogue", CASES)
def test_verified_missing_work_matches_existing_ocr_selection(slug, name, printed, title, catalogue):
    assert MusicMatcher([]).match(title, printed, catalogue=catalogue).work_id is None
    works, _ = repaired_catalogue()
    expected = str(uuid5(NAMESPACE_URL, "https://classichubble.com/works/" + slug))
    assert MusicMatcher(works).match(title, printed, catalogue=catalogue).work_id == expected


@pytest.mark.parametrize("title,composer,catalogue", [
    ("Dichterliebe", "Clara Schumann", "Op.48"),
    ("Dichterliebe", "R. Schumann", "Op.48 No.1"),
    ("Locus iste", "A. Bruckner", "WAB 24"),
    ("Der Tanz", "F.Schubert", "D827"),
    ("Suite for Flute and Piano", "C.M.Widor", "Op.35"),
    ("Suite for Violin and Piano", "C.M.Widor", "Op.34"),
])
def test_new_works_do_not_override_conflicting_identity(title, composer, catalogue):
    works, _ = repaired_catalogue()
    assert MusicMatcher(works).match(title, composer, catalogue=catalogue).work_id is None


def test_vocal_chamber_repair_is_additive_provenanced_and_idempotent():
    _, plan = repaired_catalogue()
    assert len(plan["new_works"]) == 4
    assert plan["updates"] == []
    assert {p["payload"]["composer"] for p in plan["provenance"]} == {c["name"] for c in COMPOSERS}
    for p in plan["provenance"]:
        assert p["payload"]["source_url"].startswith("https://")
        assert p["payload"]["corroboration_url"].startswith("https://")
    again = build_repair_plan({"repairs": [p["payload"] for p in plan["provenance"]]}, plan["new_works"], COMPOSERS)
    assert again["new_works"] == [] and again["updates"] == []
