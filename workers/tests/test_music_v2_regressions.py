"""Small, grounded reproductions of the saved v2 pilot regressions."""

import copy

import pytest
from classic_hubble_pipeline.music_extraction import validate_response
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork

NINTH = CanonicalWork(
    "ninth",
    "ninth",
    ("Symphony No. 9 in D minor", "교향곡 9번 '합창'"),
    ("Ludwig van Beethoven", "루트비히 판 베토벤"),
    "Op. 125",
    ("교향곡 9번", "Symphony No. 9"),
)
TANGO = CanonicalWork(
    "tango",
    "tango",
    ("Histoire du Tango", "탱고의 역사"),
    ("Astor Piazzolla", "아스토르 피아졸라"),
    None,
)
SEASONS = CanonicalWork(
    "seasons",
    "seasons",
    ("The Four Seasons", "사계"),
    ("Antonio Vivaldi", "안토니오 비발디"),
    "Op. 8",
)
SPRING = CanonicalWork(
    "spring",
    "spring",
    ("Violin Concerto No. 1 in E major",),
    SEASONS.composers,
    "RV 269",
)
SUMMER = CanonicalWork(
    "summer",
    "summer",
    ("Violin Concerto No. 2 in G minor",),
    SEASONS.composers,
    "RV 315",
)


def evaluate(
    title,
    composer,
    *,
    catalogue=None,
    scope="full_work",
    movements=(),
    context="program",
    extra_lines=(),
    status="items_extracted",
):
    lines = [composer, title, *movements, *extra_lines]
    if catalogue:
        lines.append(catalogue)

    def q(index):
        return [{"line_id": f"L{index:06}", "quote": lines[index]}]

    payload = {
        "document_sha256": "b" * 64,
        "status": status,
        "items": [
            {
                "context": context,
                "scope": scope,
                "composer": q(0),
                "title": q(1),
                "catalogue": q(len(lines) - 1) if catalogue else None,
                "key": None,
                "movements": [q(i + 2) for i in range(len(movements))],
            }
        ],
    }
    original = copy.deepcopy(payload)
    report = validate_response(
        payload,
        {"status": "text_extracted", "lines": [{"text": t} for t in lines]},
        "b" * 64,
        [NINTH, TANGO, SEASONS, SPRING, SUMMER],
        automatic=True,
    )
    assert payload == original
    assert report["items"][0]["evidence"] == original["items"][0]
    return report


@pytest.mark.parametrize("catalogue", ["Op. 125 0p.125", "0p.125", "0P 125"])
def test_ocr_catalogue_prefix_is_normalized_only_for_matching(catalogue):
    item = evaluate("Symphony No. 9", "Beethoven", catalogue=catalogue)["items"][0]
    assert item["suggested_work_id"] == NINTH.id
    assert item["fields"]["catalogue"] == catalogue


@pytest.mark.parametrize(
    "catalogue",
    [
        "Op. 125 0p.126",
        "0p.1250",
        "0p.12S",
        "0p.125 xyz",
        "x0p.125",
    ],
)
def test_catalogue_repair_does_not_repair_digits_or_discard_conflicts(catalogue):
    item = evaluate("Symphony No. 9", "Beethoven", catalogue=catalogue)["items"][0]
    assert item["suggested_work_id"] is None


@pytest.mark.parametrize(
    "title",
    [
        "교향곡9번 합창 '환희의 송가",
        "교향곡9번 합창'환희의 송가",
        "Symphony No. 9: IV. Finale",
    ],
)
def test_scoped_title_recovers_parent_without_full_work_claim(title):
    item = evaluate(title, "Beethoven", scope="excerpt")["items"][0]
    assert item["scoped_work_id"] == NINTH.id
    assert item["suggested_work_id"] is None
    assert item["fields"]["title"] == title


def test_bilingual_excerpt_markers_are_not_part_of_the_work_name():
    item = evaluate(
        "{탱고의 역사»중 from Histoire du tango",
        "아스토르피아졸라 Astor Piazzolla",
        scope="excerpt",
        movements=['II. "Café 1930", III. "Nightclub 1960"'],
    )["items"][0]
    assert item["scoped_work_id"] == TANGO.id
    assert item["suggested_work_id"] is None


@pytest.mark.parametrize(
    "title,catalogue",
    [
        ("Symphony No. 9: Symphony No. 8", None),
        ("Symphony No. 9: Violin Sonata", None),
        ("Symphony No. 9: in E major", None),
        ("Symphony No. 9: Op. 126", None),
        ("Symphony No. 9: Finale", "0p.126"),
        ("Not Symphony No. 9: Finale", None),
        ("Symphony No. 9: from Histoire du Tango", None),
    ],
)
def test_scoped_title_does_not_discard_conflicts_or_negation(title, catalogue):
    item = evaluate(title, "Beethoven", scope="excerpt", catalogue=catalogue)["items"][
        0
    ]
    assert item["scoped_work_id"] is None


def test_excerpt_fallback_is_not_used_for_ordinary_full_work_labels():
    result = MusicMatcher([NINTH]).match("Symphony No. 9: Finale", "Beethoven")
    assert result.work_id is None


LISTED_WORKS = (
    "바이올린 협주곡 제1번 E장조 '봄' Violin Concerto No. 1 in E Major, RV 269",
    "바이올린 협주곡 제2번 g단조 '여름' Violin Concerto No. 2 in g minor, RV 315",
)


def test_explicit_works_misfiled_as_movements_retain_individual_grounded_links():
    report = evaluate(
        "사계 The Four Seasons", "비발디 A. Vivaldi", movements=LISTED_WORKS
    )
    derived = [i for i in report["items"] if i.get("derived_from")]
    assert {i["scoped_work_id"] for i in derived} == {SPRING.id, SUMMER.id}
    assert all(
        i["suggested_work_id"] is None and i["scope"] == "unknown" for i in derived
    )
    assert report["publishable"] is False
    for index, item in enumerate(derived):
        assert item["source_index"] == 0
        assert item["derived_from"] == {"field": "movements", "index": index}
        assert item["fields"]["title"] == LISTED_WORKS[index]
        assert (
            item["evidence"]["title"]
            == report["items"][0]["evidence"]["movements"][index]
        )


@pytest.mark.parametrize(
    "options",
    [
        {"context": "biography"},
        {"context": "unknown"},
        {"status": "uncertain"},
        {"extra_lines": ["2.26(목)", "3.26(목)"]},
    ],
)
def test_derived_references_obey_document_and_context_gates(options):
    report = evaluate("The Four Seasons", "Vivaldi", movements=LISTED_WORKS, **options)
    assert not any(
        i["suggested_work_id"] or i["scoped_work_id"] for i in report["items"]
    )


@pytest.mark.parametrize(
    "movements",
    [
        ["I. Allegro", "II. Adagio"],
        ["II. Allegro RV 269"],
        ["Violin Concerto No. 1 in G minor, RV 269"],
        ["Violin Concerto No. 1 RV 269 RV 315"],
    ],
)
def test_movements_and_conflicting_child_descriptions_are_not_expanded(movements):
    report = evaluate("The Four Seasons", "Vivaldi", movements=movements)
    assert not any(i.get("derived_from") for i in report["items"])


def test_repeated_child_evidence_does_not_multiply_links():
    report = evaluate("The Four Seasons", "Vivaldi", movements=LISTED_WORKS * 2)
    assert len([i for i in report["items"] if i.get("derived_from")]) == 2
