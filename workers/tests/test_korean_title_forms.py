import pytest
from classic_hubble_pipeline import korean_title_forms as module


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Symphony No. 12 in D minor", "교향곡 12번 D단조"),
        ("Piano Concerto No.2 in B-flat major", "피아노 협주곡 2번 B♭장조"),
        (
            "Violin concerto in F-sharp minor (RV 297)",
            "바이올린 협주곡 F♯단조 (RV 297)",
        ),
        ("String Quartet No. 8", "현악 사중주 8번"),
        ("Cello Sonata in G minor, Op. 65", "첼로 소나타 G단조, Op. 65"),
        ("Piano Trio in B-flat Major, Op. 11", "피아노 삼중주 B♭장조, Op. 11"),
        ("Symphony No. 0", "교향곡 0번"),
        (
            "Waltz No. 13 in D-flat major, Op. 70, No. 3",
            "왈츠 13번 D♭장조, Op. 70, No. 3",
        ),
        ("Piano Sonata No. 2: Allegro", None),
        ("Symphony No. 5 (arrangement)", None),
        ("Symphony No. 5 in C minor in C major", None),
        ("Piano Concerto", None),
        ("Keyboard Sonata in C major", None),
        ("Sonata in C major", None),
        ("Symphony No. 5 and No. 6", None),
        ("The Storm", None),
    ],
)
def test_only_complete_supported_formal_titles_are_rendered(title, expected):
    assert module.render_title(title) == expected


def test_formal_manifest_fills_empty_titles_without_overwriting_reviewed_names():
    works = [
        {"id": "w1", "composer_id": "c", "title": "Symphony No. 12", "title_ko": None},
        {
            "id": "w2",
            "composer_id": "c",
            "title": "Symphony No. 9",
            "title_ko": "교향곡 9번 '합창'",
        },
        {"id": "w3", "composer_id": "c", "title": "Symphony No. 8", "title_ko": None},
    ]
    composers = [{"id": "c", "name": "Composer"}]
    links = [
        {"provider_id": "Q1", "payload": {"work_id": "w1"}},
        {"provider_id": "Q2", "payload": {"work_id": "w2"}},
    ]
    manifest = module.build_manifest(works, composers, links)
    assert manifest["origin"] == "formal-rendering"
    assert [e["qid"] for e in manifest["works"]] == ["Q1", "Q2"]
    assert manifest["works"][0]["title_ko"] == "교향곡 12번"
    assert manifest["works"][1]["title_ko"] == "교향곡 9번 '합창'"
    assert manifest["works"][1]["aliases"][0]["text"] == "교향곡 9번"
    assert all(s["kind"] != "community_usage" for s in manifest["sources"].values())


def test_rendering_terms_are_grounded_in_bilingual_reference_examples():
    import json
    from pathlib import Path

    manifest = json.loads(
        (Path(__file__).parents[1] / "data/korean-wikipedia-names.json").read_text()
    )
    works = {entry["qid"]: entry for entry in manifest["works"]}
    for english, korean, qid in module.FORMS:
        entry = works[qid]
        assert entry["expected_title"].lower().startswith(english.lower())
        assert korean in entry["title_ko"]
