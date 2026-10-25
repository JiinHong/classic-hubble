import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.program_catalog_repairs import build_repair_plan
from classic_hubble_pipeline.work_matching import CanonicalWork


SLUG = "reviewed-liszt-transcendental-etudes-s139"
COLLECTION_ID = str(uuid5(NAMESPACE_URL, "https://classichubble.com/works/" + SLUG))
COMPOSERS = [{"id": "liszt", "name": "Franz Liszt"}]
# Existing catalogue has the individual studies but no complete collection.
MEMBER = CanonicalWork(
    id="member-4", slug="wikidata-q8843614",
    titles=("Transcendental Étude No. 4 in D minor",),
    composers=("Franz Liszt", "프란츠 리스트"), catalogue=None,
    aliases=("Études d’exécution transcendante, S. 139: Étude No. 4, Mazeppa",
             "Transcendental Etude No. 4", "Mazeppa"), requires_review=False,
)


def repaired_catalogue():
    manifest = json.loads(
        (Path(__file__).parents[1] / "data/ocr-catalog-repairs-20261025.json").read_text()
    )
    plan = build_repair_plan(manifest, [], COMPOSERS)
    works = [MEMBER]
    for row in plan["new_works"]:
        aliases = tuple(a["alias"] for a in plan["aliases"] if a["work_id"] == row["id"])
        works.append(CanonicalWork(
            id=row["id"], slug=row["slug"],
            titles=tuple(t for t in (row["title"], row["title_ko"]) if t),
            composers=MEMBER.composers, catalogue=row["catalogue"],
            aliases=aliases, requires_review=False,
        ))
    return works, plan


@pytest.mark.parametrize("title", [
    "Transcendental Etudes 초절기교 연습곡 전곡",
    "Transcendental Studies", "Études d’exécution transcendante",
])
def test_poster_complete_collection_resolves_without_selecting_a_member(title):
    assert MusicMatcher([MEMBER]).match(title, "Liszt").work_id is None
    works, _ = repaired_catalogue()
    assert MusicMatcher(works).match(title, "Liszt").work_id == COLLECTION_ID


def test_individual_etude_and_other_composer_are_not_widened_to_collection():
    works, _ = repaired_catalogue()
    matcher = MusicMatcher(works)
    assert matcher.match("Transcendental Etude No. 4", "Liszt").work_id == MEMBER.id
    assert matcher.match("Transcendental Etudes", "Chopin").work_id is None
    assert matcher.match("Etudes", "Liszt").work_id is None


def test_repair_adds_only_collection_with_verified_provenance_and_is_idempotent():
    _, plan = repaired_catalogue()
    assert len(plan["new_works"]) == 1
    assert plan["new_works"][0]["id"] == COLLECTION_ID
    assert plan["updates"] == []
    evidence = plan["provenance"][0]["payload"]
    assert evidence["source_url"] == "https://www.henle.de/us/Transcendental-Studies/HN-717"
    assert evidence["corroboration_url"].startswith("https://www.deutschegrammophon.com/")
    assert evidence["catalogue"] == "S. 139"
    repeated = build_repair_plan({"repairs": [evidence]}, plan["new_works"], COMPOSERS)
    assert repeated["new_works"] == [] and repeated["updates"] == []
