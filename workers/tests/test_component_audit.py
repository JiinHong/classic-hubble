from classic_hubble_pipeline.component_audit import (
    resolve_album_parent,
    wikidata_components,
)


def claim(value, position=None):
    result = {"rank": "normal", "mainsnak": {"datavalue": {"value": {"id": value}}}}
    if position is not None:
        result["qualifiers"] = {"P1545": [{"datavalue": {"value": str(position)}}]}
    return result


def entity(qid, claims):
    return {
        "entity": {"id": qid, "labels": {"en": {"value": qid}}, "claims": claims},
        "url": "https://www.wikidata.org/w/api.php",
        "sha256": "a" * 64,
    }


def catalog():
    return {
        "works": [
            {
                "id": "parent",
                "slug": "parent",
                "title": "Waldszenen",
                "composer_id": "composer",
                "catalogue": "Op. 82",
            }
        ],
        "composers": [{"id": "composer", "name": "Robert Schumann"}],
        "work_aliases": [],
        "links": [
            {
                "provider_id": "Q1",
                "payload": {"work_id": "parent", "record": {"composers": ["Q10"]}},
            }
        ],
    }


def test_explicit_musical_parts_keep_number_and_composer():
    entities = {
        "Q1": entity("Q1", {"P527": [claim("Q2", 3)]}),
        "Q2": entity("Q2", {"P86": [claim("Q10")], "P31": [claim("Q929848")]}),
    }
    rows, held = wikidata_components(catalog(), entities)
    assert not held
    assert rows[0]["position"] == 3 and rows[0]["child_qid"] == "Q2"
    assert rows[0]["composer_id"] == "composer"


def test_nonmusic_cross_composer_missing_evidence_and_conflicting_numbers_are_held():
    for extra in (
        {"P31": [claim("Q5")]},
        {"P86": [claim("Q11")]},
        {"P86": []},
        {"P361": [claim("Q1", 4)]},
    ):
        entities = {
            "Q1": entity("Q1", {"P527": [claim("Q2", 3)]}),
            "Q2": entity(
                "Q2", {"P86": [claim("Q10")], "P31": [claim("Q929848")], **extra}
            ),
        }
        rows, held = wikidata_components(catalog(), entities)
        assert not rows and held


def test_album_parent_requires_exact_composer_and_unambiguous_catalogue():
    row = {
        "parent_title_en": "Waldszenen, Op. 82",
        "parent_title_ko": "숲의 정경, Op. 82",
        "composer": "Robert Schumann",
    }
    data = catalog()
    assert resolve_album_parent(row, data) == "parent"
    assert resolve_album_parent({**row, "composer": "Clara Schumann"}, data) is None
    data["works"].append({**data["works"][0], "id": "duplicate"})
    assert resolve_album_parent(row, data) is None
