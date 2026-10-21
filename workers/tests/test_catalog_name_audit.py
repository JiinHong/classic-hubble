import json

import httpx
import pytest
from classic_hubble_pipeline import catalog_name_audit


def test_fetches_every_identity_in_bounded_batches_and_reuses_evidence(tmp_path):
    requested = []

    def respond(request):
        ids = request.url.params["ids"].split("|")
        requested.extend(ids)
        return httpx.Response(
            200,
            json={
                "entities": {
                    qid: {"id": qid, "lastrevid": 123, "labels": {}} for qid in ids
                }
            },
        )

    ids = [f"Q{i}" for i in range(1, 54)]
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        rows = catalog_name_audit.fetch_entities(client, ids, tmp_path, delay=0)
        again = catalog_name_audit.fetch_entities(client, ids, tmp_path, delay=0)
    assert set(rows) == set(ids)
    assert requested == ids
    assert rows == again
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert all(row["fetched_at"] and len(row["sha256"]) == 64 for row in rows.values())
    assert rows["Q1"]["entity"]["lastrevid"] == 123


@pytest.mark.parametrize(
    "payload",
    [
        {"error": {"code": "maxlag"}},
        {"entities": {}},
        {"entities": {"Q2": {"id": "Q2"}}},
        {"entities": {"Q1": {"id": "Q2"}}},
    ],
)
def test_failed_or_incomplete_source_cannot_be_called_no_korean_name(payload, tmp_path):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
        ) as client,
        pytest.raises(ValueError),
    ):
        catalog_name_audit.fetch_entities(client, ["Q1"], tmp_path, delay=0)
    assert not list(tmp_path.glob("*.json"))


def test_missing_entity_is_explicit_evidence_not_an_empty_success(tmp_path):
    payload = {"entities": {"Q1": {"id": "Q1", "missing": ""}}}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        result = catalog_name_audit.fetch_entities(client, ["Q1"], tmp_path, delay=0)
    assert "missing" in result["Q1"]["entity"]
    assert json.loads(next(tmp_path.glob("*.json")).read_text())["requested_ids"] == [
        "Q1"
    ]


def test_exact_recording_name_can_resolve_a_work_without_catalogue():
    row = {
        "composer": "Claude Debussy",
        "title_en": "Syrinx, L. 129",
        "title_ko": "시링크스, L. 129",
    }
    works = [
        {
            "id": "one",
            "composer": "Claude Debussy",
            "title": "Syrinx",
            "catalogue": None,
        }
    ]
    assert catalog_name_audit.match_exact_name(row, works, []) == "one"


@pytest.mark.parametrize(
    "other",
    [
        {
            "id": "two",
            "composer": "Claude Debussy",
            "title": "Syrinx",
            "catalogue": None,
        },
        {
            "id": "two",
            "composer": "Claude Debussy",
            "title": "Another work",
            "catalogue": None,
        },
    ],
)
def test_exact_name_rejects_duplicate_titles_and_ambiguous_aliases(other):
    row = {"composer": "Claude Debussy", "title_en": "Syrinx", "title_ko": "시링크스"}
    works = [
        {
            "id": "one",
            "composer": "Claude Debussy",
            "title": "Syrinx",
            "catalogue": None,
        },
        other,
    ]
    aliases = [{"work_id": "two", "alias": "Syrinx"}]
    assert catalog_name_audit.match_exact_name(row, works, aliases) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"composer": "Maurice Ravel"},
        {"title_en": "Syrinx: I. Allegro"},
        {"title_ko": "시링크스 다장조", "title_en": "Syrinx in D Major"},
        {"title_en": "Syrinx, Op. 99"},
    ],
)
def test_exact_name_never_discards_composer_scope_key_or_catalogue_conflicts(changes):
    row = {
        "composer": "Claude Debussy",
        "title_en": "Syrinx, Op. 1",
        "title_ko": "시링크스, Op. 1",
        **changes,
    }
    works = [
        {
            "id": "one",
            "composer": "Claude Debussy",
            "title": "Syrinx",
            "catalogue": "Op. 1",
        }
    ]
    assert catalog_name_audit.match_exact_name(row, works, []) is None


def test_an_alias_cannot_silently_turn_incidental_music_into_its_suite():
    row = {
        "composer": "Aram Khachaturian",
        "title_en": "Masquerade, Suite, Op. 48a",
        "title_ko": "가면무도회, 모음곡, Op. 48a",
    }
    works = [
        {
            "id": "one",
            "composer": "Aram Khachaturian",
            "title": "Masquerade",
            "catalogue": None,
        }
    ]
    aliases = [{"work_id": "one", "alias": "Masquerade, Suite"}]
    assert catalog_name_audit.match_exact_name(row, works, aliases) is None


def test_unknown_catalogue_suffix_version_is_held_even_when_main_title_matches():
    row = {
        "composer": "Alberto Ginastera",
        "title_en": "Estancia, Op. 8a",
        "title_ko": "에스탄시아, Op. 8a",
    }
    works = [
        {
            "id": "one",
            "composer": "Alberto Ginastera",
            "title": "Estancia",
            "catalogue": None,
        }
    ]
    assert catalog_name_audit.match_exact_name(row, works, []) is None


def test_roman_series_number_must_agree_with_korean_arabic_number():
    row = {
        "composer": "Luciano Berio",
        "title_en": "Sequenza VII",
        "title_ko": "세쿠엔차 12",
    }
    works = [
        {
            "id": "one",
            "composer": "Luciano Berio",
            "title": "Sequenza VII",
            "catalogue": None,
        }
    ]
    assert catalog_name_audit.match_exact_name(row, works, []) is None
    assert (
        catalog_name_audit.match_exact_name(
            {**row, "title_ko": "세쿠엔차 7"}, works, []
        )
        == "one"
    )


def artist_html(
    locale="kr", artist_id="123", work_key="debussy-pp1", composer_id="123"
):
    composer = "드뷔시" if locale == "kr" else "Claude Debussy"
    title = "시링크스" if locale == "kr" else "Syrinx"
    header = {
        "type": "work",
        "title": title,
        "subtitle": "L. 129 · ignored note",
        "composerName": composer,
        "composerAction": {"url": f"/query/view/{locale}/artist/{composer_id}"},
    }
    item = {
        "type": "work",
        "url": f"/{locale}/work/{work_key}",
        "action": {"header": header},
    }
    payload = {
        "data": [
            {
                "intent": {"id": artist_id, "storefront": locale},
                "data": {
                    "header": {"id": artist_id, "type": "artist", "title": composer},
                    "sections": [
                        {
                            "items": [
                                item,
                                {
                                    "type": "recording",
                                    "url": f"/{locale}/recording/other",
                                },
                            ]
                        }
                    ],
                },
            }
        ]
    }
    return (
        '<script id="serialized-server-data" type="application/json">'
        + json.dumps(payload)
        + "</script>"
    )


def test_public_artist_metadata_pairs_work_ids_not_positions_or_recordings():
    ko = catalog_name_audit.parse_apple_names(artist_html(), "kr", "123")
    en = catalog_name_audit.parse_apple_names(artist_html("us"), "us", "123")
    rows = catalog_name_audit.pair_apple_names(ko, en)
    assert rows == [
        {
            "work_key": "debussy-pp1",
            "title_ko": "시링크스, L. 129",
            "title_en": "Syrinx, L. 129",
            "composer": "Claude Debussy",
            "composer_ko": "드뷔시",
            "composer_id": "123",
        }
    ]
    assert (
        catalog_name_audit.pair_apple_names(
            ko,
            catalog_name_audit.parse_apple_names(
                artist_html("us", work_key="other"), "us", "123"
            ),
        )
        == []
    )


def test_public_metadata_must_belong_to_requested_page_and_composer():
    with pytest.raises(ValueError):
        catalog_name_audit.parse_apple_names(artist_html(), "kr", "999")
    assert (
        catalog_name_audit.parse_apple_names(
            artist_html(composer_id="999"), "kr", "123"
        )
        == {}
    )
    with pytest.raises(ValueError):
        catalog_name_audit.parse_apple_names(
            "<html>service unavailable</html>", "kr", "123"
        )


def audit_row(qid="Q1"):
    return {
        "qid": qid,
        "composer": "Composer",
        "expected_title": "Work",
        "status": "no_korean_evidence",
        "reason": "No Korean name in the checked sources.",
        "sources": ["source"],
    }


def test_audit_requires_exact_complete_target_set_and_explicit_evidence():
    sources = {
        "source": {
            "url": "https://www.wikidata.org/wiki/Q1",
            "kind": "entity",
            "sha256": "a" * 64,
        }
    }
    audit = catalog_name_audit.build_audit(["Q1"], [audit_row()], sources, "test.1")
    assert audit["summary"] == {"total": 1, "no_korean_evidence": 1}
    assert audit["target_sha256"]
    for rows in ([], [audit_row("Q2")], [audit_row(), audit_row()]):
        with pytest.raises(ValueError):
            catalog_name_audit.build_audit(["Q1"], rows, sources, "test.1")
    with pytest.raises(ValueError):
        catalog_name_audit.build_audit(["Q1"], [audit_row()], {}, "test.1")


def test_audit_named_status_requires_the_applied_dictionary_identity():
    sources = {
        "source": {
            "url": "https://www.wikidata.org/wiki/Q1",
            "kind": "entity",
            "sha256": "a" * 64,
        }
    }
    with pytest.raises(ValueError):
        catalog_name_audit.build_audit(
            ["Q1"], [{**audit_row(), "status": "named"}], sources, "test.1"
        )


def test_audit_plan_preserves_work_tables_and_guards_canonical_identity():
    sources = {
        "source": {
            "url": "https://www.wikidata.org/wiki/Q1",
            "kind": "entity",
            "sha256": "a" * 64,
        }
    }
    audit = catalog_name_audit.build_audit(["Q1"], [audit_row()], sources, "test.1")
    works = [{"id": "work", "composer_id": "composer", "title": "Work"}]
    composers = [{"id": "composer", "name": "Composer"}]
    links = [{"provider_id": "Q1", "payload": {"work_id": "work"}}]
    rows = catalog_name_audit.plan_audit(audit, works, composers, links)
    assert len(rows) == 1
    assert rows[0]["entity_type"] == "work_name_audit"
    assert rows[0]["payload"]["work_id"] == "work"
    assert rows == catalog_name_audit.plan_audit(audit, works, composers, links)
    with pytest.raises(ValueError):
        catalog_name_audit.plan_audit(
            audit, [{**works[0], "title": "Different work"}], composers, links
        )
    audit["works"][0]["reason"] = "tampered"
    with pytest.raises(ValueError):
        catalog_name_audit.plan_audit(audit, works, composers, links)
