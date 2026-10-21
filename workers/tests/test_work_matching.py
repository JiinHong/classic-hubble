from dataclasses import replace

import pytest

from classic_hubble_pipeline.work_matching import CanonicalWork, match_work


RACH = CanonicalWork(
    id="rach-2",
    slug="rachmaninoff-piano-concerto-2",
    titles=("Piano Concerto No. 2 in C minor", "피아노 협주곡 2번"),
    composers=("Sergei Rachmaninoff", "세르게이 라흐마니노프"),
    catalogue="Op. 18",
    aliases=("라흐 피협 2번",),
)


def test_composer_and_catalogue_identify_the_database_work():
    result = match_work(
        "Piano Concerto No. 2 in C minor, Op.18\nI. Moderato", "S. Rachmaninoff", [RACH]
    )
    assert result.work_id == "rach-2"
    assert result.reason == "composer_and_catalogue"


def test_composer_and_exact_alias_identify_the_database_work():
    result = match_work("라흐 피협 2번", "라흐마니노프", [RACH])
    assert result.work_id == "rach-2"


@pytest.mark.parametrize(
    ("title", "composer"),
    [
        ("Violin Sonata, Op.18", "R. Strauss"),
        ("Piano Concerto No. 2 in C minor, Op. 18", None),
        ("Piano Concerto No. 2 in C minor, Op. 180", "Sergei Rachmaninoff"),
        ("Piano Concerto No. 2 in C minor, Op. 18 No. 1", "Sergei Rachmaninoff"),
        ("Piano Concerto No. 2 in C minor, Op. 45", "Sergei Rachmaninoff"),
        ("Piano Concerto No. 2, Op.18\nSymphonic Dances, Op.45", "Sergei Rachmaninoff"),
        ("Piano Concerto No. 2 in C minor\nVocalise", "Sergei Rachmaninoff"),
        ("", "Sergei Rachmaninoff"),
        ("Intermission", None),
    ],
)
def test_unsafe_or_insufficient_input_is_not_linked(title, composer):
    assert match_work(title, composer, [RACH]).work_id is None


def test_duplicate_candidates_require_review():
    duplicate = replace(RACH, id="another-edition")
    result = match_work(
        "Piano Concerto No. 2 in C minor, Op.18", "Rachmaninoff", [RACH, duplicate]
    )
    assert result.work_id is None
    assert result.reason == "ambiguous"
    assert result.candidate_ids == ("rach-2", "another-edition")


def test_surname_shared_by_different_composers_does_not_auto_link():
    robert = replace(RACH, id="robert", composers=("Robert Schumann",))
    clara = replace(RACH, id="clara", composers=("Clara Schumann",))
    assert match_work("Op. 18", "Schumann", [robert, clara]).work_id is None
    assert match_work("Op. 18", "R. Schumann", [robert, clara]).work_id == "robert"


def test_catalogue_number_does_not_resolve_an_ambiguous_composer():
    robert = replace(RACH, id="robert", composers=("Robert Schumann",))
    clara = replace(RACH, id="clara", composers=("Clara Schumann",), catalogue="Op. 22")
    result = match_work("Op. 18", "Schumann", [robert, clara])
    assert result.work_id is None
    assert result.reason == "ambiguous_composer"
    assert match_work("Op. 18", "R. Schumann", [robert, clara]).work_id == "robert"


def test_diacritics_are_normalized_without_losing_korean():
    work = replace(RACH, composers=("Antonín Dvořák", "안토닌 드보르자크"))
    assert match_work("Op.18", "Antonin Dvorak", [work]).work_id == "rach-2"
    assert match_work("라흐 피협 2번", "드보르자크", [work]).work_id == "rach-2"


def test_unknown_alias_can_only_suggest_not_invent_a_work():
    result = match_work("라흐 피협 2번", None, [RACH])
    assert result.work_id is None
    assert result.candidate_ids == ("rach-2",)
    assert result.reason == "composer_unconfirmed"


def test_catalogue_mapping_preserves_movement_granularity_for_review():
    # A movement-only announcement must not silently become a complete-work match.
    assert (
        match_work(
            "Piano Concerto No. 2, Op. 18: II. Adagio", "Rachmaninoff", [RACH]
        ).work_id
        is None
    )


@pytest.mark.parametrize(
    "title",
    [
        "Piano Concerto No. 3 in C minor, Op.18",
        "Piano Concerto No. 2 in D major, Op.18",
        "Piano Concerto No. 2 Op.18; Symphony No. 2",
    ],
)
def test_conflicting_title_details_do_not_override_catalogue_match(title):
    assert match_work(title, "Rachmaninoff", [RACH]).work_id is None


def test_catalogue_spacing_is_not_semantic():
    assert (
        match_work("Piano Concerto No. 2 Op18", "Rachmaninoff", [RACH]).work_id
        == "rach-2"
    )
