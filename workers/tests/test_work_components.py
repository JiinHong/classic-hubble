import json

import pytest
from classic_hubble_pipeline.work_components import (
    apply_component_plan,
    build_component_plan,
    pair_album_parts,
    parse_album_parts,
)


def test_apply_is_opt_in_additive_and_never_writes_concerts():
    class Repository:
        def __init__(self):
            self.calls = []

        def _request(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    repo = Repository()
    plan = build_component_plan([observation()], [parent()], [], [])
    apply_component_plan(repo, plan)
    assert repo.calls == []
    apply_component_plan(repo, plan, apply=True)
    assert [args[1] for args, _ in repo.calls] == [
        "works",
        "work_aliases",
        "provider_records",
    ]
    assert all(
        kwargs["prefer"] == "resolution=ignore-duplicates,return=minimal"
        for _, kwargs in repo.calls
    )


def album(locale, titles, *, work="schumann-waldszenen", artist="317946"):
    return (
        '<script id="serialized-server-data">'
        + json.dumps(
            {
                "data": [
                    {
                        "intent": {"id": "123", "storefront": locale},
                        "data": {
                            "screenId": "123",
                            "screenType": "album",
                            "sections": [
                                {
                                    "header": {
                                        "kind": "work",
                                        "item": {
                                            "firstRowText": "Robert Schumann",
                                            "secondRowText": "Waldszenen, Op. 82",
                                            "firstRowLinks": [
                                                {
                                                    "segue": {
                                                        "destination": {
                                                            "id": artist,
                                                            "contentDescriptor": {
                                                                "url": f"/{locale}/artist/{artist}"
                                                            },
                                                        }
                                                    }
                                                }
                                            ],
                                            "secondRowLinks": [
                                                {
                                                    "segue": {
                                                        "destination": {
                                                            "id": work,
                                                            "pageType": "work",
                                                            "contentDescriptor": {
                                                                "url": f"/{locale}/work/{work}"
                                                            },
                                                        }
                                                    }
                                                }
                                            ],
                                        },
                                    },
                                    "items": [
                                        {
                                            "id": f"track-lockup - 123 - {tid}",
                                            "title": title,
                                            "composer": "Robert Schumann",
                                        }
                                        for tid, title in titles
                                    ],
                                }
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )
        + "</script>"
    )


def test_tracks_pair_by_recording_identity_not_order_and_preserve_piece_number():
    en = parse_album_parts(
        album("us", [(11, "No. 3, Einsame Blumen"), (12, "VII. Vogel als Prophet")]),
        "us",
        "123",
    )
    ko = parse_album_parts(
        album("kr", [(12, "7. 예언의 새"), (11, "3. 고독한 꽃")]), "kr", "123"
    )
    rows = pair_album_parts(ko, en)
    assert [(r["position"], r["title_en"], r["title_ko"]) for r in rows] == [
        (3, "Einsame Blumen", "고독한 꽃"),
        (7, "Vogel als Prophet", "예언의 새"),
    ]
    assert all(r["parent_key"] == "schumann-waldszenen" for r in rows)


def test_tracks_without_explicit_piece_numbers_are_not_numbered_by_track_position():
    rows = parse_album_parts(
        album(
            "us",
            [
                (11, "Einsame Blumen"),
                (12, "I-II. Allegro"),
                (13, "No. 2, Adagio (arr. for violin)"),
            ],
        ),
        "us",
        "123",
    )
    assert rows == []


def test_recording_track_numbers_and_combined_movements_are_not_composition_numbers():
    rows = parse_album_parts(
        album("us", [(11, "10. Var. 8, Tempo I"), (12, "11. Var. 9")]), "us", "123"
    )
    assert rows == []
    assert (
        parse_album_parts(
            album("us", [(11, "I. —"), (12, "I. Adagio - II. Allegro")]), "us", "123"
        )
        == []
    )


def test_inconsistent_localization_and_wrong_page_identity_fail_closed():
    en = parse_album_parts(album("us", [(11, "No. 3, Einsame Blumen")]), "us", "123")
    ko = parse_album_parts(album("kr", [(11, "4. 고독한 꽃")]), "kr", "123")
    assert pair_album_parts(ko, en) == []
    with pytest.raises(ValueError, match="identity"):
        parse_album_parts(album("us", []), "kr", "123")


def parent():
    return {
        "id": "parent",
        "slug": "waldszenen",
        "composer_id": "schumann",
        "title": "Waldszenen",
        "title_ko": "숲의 정경",
        "catalogue": "Op. 82",
    }


def observation(**overrides):
    return {
        "parent_id": "parent",
        "expected_parent_title": "Waldszenen",
        "composer_id": "schumann",
        "position": 3,
        "title": "Einsame Blumen",
        "title_ko": "고독한 꽃",
        "catalogue": "Op. 82 No. 3",
        "aliases": [{"alias": "Lonely Flowers", "locale": "en"}],
        "sources": [{"url": "https://example.org/score", "sha256": "a" * 64}],
        **overrides,
    }


def test_component_is_a_distinct_work_and_never_an_alias_of_parent():
    plan = build_component_plan([observation()], [parent()], [], [])
    child = plan["works"][0]
    assert child["id"] != "parent"
    assert child["title"] == "Einsame Blumen"
    assert child["catalogue"] == "Op. 82 No. 3"
    assert all(a["work_id"] == child["id"] for a in plan["aliases"])
    assert "고독한 꽃" in [a["alias"] for a in plan["aliases"]]
    assert plan["relations"][0]["parent_slug"] == "waldszenen"
    assert plan["relations"][0]["child_slug"] == child["slug"]
    again = build_component_plan(
        [observation()], [parent(), child], plan["aliases"], plan["relations"]
    )
    assert again["works"] == again["aliases"] == again["relations"] == []


def test_existing_component_is_linked_without_rewriting_its_title():
    child = {
        **parent(),
        "id": "child",
        "slug": "existing-child",
        "title": "Einsame Blumen",
        "title_ko": "외로운 꽃",
        "catalogue": "Op. 82 No. 3",
    }
    plan = build_component_plan(
        [observation(existing_child_id="child")], [parent(), child], [], []
    )
    assert plan["works"] == []
    assert plan["relations"][0]["child_slug"] == "existing-child"
    assert all(a["work_id"] == "child" for a in plan["aliases"])


@pytest.mark.parametrize(
    "changes",
    [
        {"composer_id": "chopin"},
        {"expected_parent_title": "Other"},
        {"position": 0},
        {"existing_child_id": "parent"},
        {"sources": []},
    ],
)
def test_invalid_or_unproven_relationships_never_write(changes):
    plan = build_component_plan([observation(**changes)], [parent()], [], [])
    assert not plan["works"] and not plan["aliases"] and not plan["relations"]
    assert plan["held"]


def test_conflicting_names_for_same_parent_and_number_are_held_not_first_wins():
    plan = build_component_plan(
        [observation(), observation(title="Different piece")], [parent()], [], []
    )
    assert plan["works"] == []
    assert len(plan["held"]) == 2


def test_cycle_and_cross_composer_relationships_are_rejected():
    child = {**parent(), "id": "child", "slug": "child", "title": "Other"}
    existing = [{"parent_slug": "child", "child_slug": "waldszenen", "position": 1}]
    plan = build_component_plan(
        [observation(existing_child_id="child")], [parent(), child], [], existing
    )
    assert plan["held"] and not plan["relations"]
    child["composer_id"] = "chopin"
    plan = build_component_plan(
        [observation(existing_child_id="child")], [parent(), child], [], []
    )
    assert plan["held"] and not plan["relations"]


def test_new_wikidata_component_keeps_stable_identity_without_guessed_number():
    from classic_hubble_pipeline.work_catalog import source_id

    row = observation(child_qid="Q12345", position=None, catalogue=None)
    plan = build_component_plan([row], [parent()], [], [])
    assert plan["works"][0]["id"] == source_id("Q12345")
    assert plan["works"][0]["slug"] == "wikidata-q12345"
    assert plan["works"][0]["catalogue"] is None


def test_number_does_not_invent_an_opus_subnumber():
    plan = build_component_plan([observation(catalogue=None)], [parent()], [], [])
    assert plan["works"][0]["catalogue"] is None


def test_same_parent_number_cannot_point_to_two_existing_works():
    children = [{**parent(), "id": n, "slug": n} for n in ("one", "two")]
    plan = build_component_plan(
        [observation(existing_child_id=n) for n in ("one", "two")],
        [parent(), *children],
        [],
        [],
    )
    assert not plan["relations"] and len(plan["held"]) == 2
