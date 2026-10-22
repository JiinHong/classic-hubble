from dataclasses import replace

import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork

GOLDBERG = CanonicalWork(
    "goldberg",
    "goldberg",
    ("Goldberg Variations", "골드베르크 변주곡"),
    ("Johann Sebastian Bach", "요한 제바스티안 바흐"),
    "BWV 988",
)
OTHER_BACH = CanonicalWork(
    "other",
    "other",
    ("Keyboard Sonata",),
    ("Carl Philipp Emanuel Bach", "카를 필리프 에마누엘 바흐"),
    "Wq. 55",
)
NESSUN = CanonicalWork(
    "nessun",
    "nessun",
    ("Nessun dorma",),
    ("Giacomo Puccini", "자코모 푸치니"),
    None,
)


def test_shared_surname_is_disambiguated_by_specific_exact_title():
    result = MusicMatcher([GOLDBERG, OTHER_BACH]).match(
        "골드베르크 변주곡",
        "바흐",
        scoped=True,
    )
    assert result.work_id == GOLDBERG.id
    assert result.reason == "surname_and_distinctive_title"


def test_missing_composer_can_use_globally_unique_distinctive_title():
    result = MusicMatcher([NESSUN, GOLDBERG]).match("Nessun dorma", None)
    assert result.work_id == NESSUN.id
    assert result.reason == "unique_distinctive_title"


@pytest.mark.parametrize(
    "title",
    [
        "Sonata",
        "Piano Sonata",
        "Violin Concerto No. 2",
        "Adagio",
        "봄",
        "피아노 협주곡 2번",
        "Op. 18",
    ],
)
def test_missing_composer_never_uses_generic_or_number_only_title(title):
    work = replace(NESSUN, titles=(title,))
    assert MusicMatcher([work]).match(title, None).work_id is None


def test_title_only_lookup_does_not_extract_a_nickname_from_prose():
    assert MusicMatcher([NESSUN]).match('Not "Nessun dorma"', None).work_id is None


def test_unknown_explicit_composer_is_not_ignored_for_a_unique_title():
    assert (
        MusicMatcher([NESSUN]).match("Nessun dorma", "Unknown Composer").work_id is None
    )


def test_same_title_by_two_composers_stays_ambiguous():
    second = replace(NESSUN, id="second", composers=("Someone Else",))
    assert MusicMatcher([NESSUN, second]).match("Nessun dorma", None).work_id is None


def test_surname_plus_catalogue_alone_does_not_disambiguate():
    assert MusicMatcher([GOLDBERG, OTHER_BACH]).match("BWV 988", "Bach").work_id is None


def test_specific_title_with_wrong_catalogue_stays_unlinked():
    assert (
        MusicMatcher([GOLDBERG, OTHER_BACH])
        .match(
            "Goldberg Variations",
            "Bach",
            catalogue="BWV 999",
        )
        .work_id
        is None
    )


def test_review_flag_is_respected_even_for_unique_title():
    result = MusicMatcher([replace(NESSUN, requires_review=True)]).match(
        "Nessun dorma", None
    )
    assert result.work_id is None


def test_distinctive_title_index_returns_a_short_candidate_list_for_unknown_composer():
    result = MusicMatcher([NESSUN]).match("Nessun dorma", "unknown")
    assert result.work_id is None
    assert result.candidate_ids == (NESSUN.id,)


def test_composer_name_pollution_is_not_a_distinctive_work_title():
    work = replace(NESSUN, aliases=("Giacomo Puccini",))
    assert MusicMatcher([work]).match("Giacomo Puccini", None).work_id is None
