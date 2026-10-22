import importlib
import importlib.util
from dataclasses import replace

import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork

BEETHOVEN = CanonicalWork(
    "beethoven-8",
    "beethoven-8",
    ("Violin Sonata No. 8 in G major", "바이올린 소나타 8번"),
    ("Ludwig van Beethoven", "루트비히 판 베토벤"),
    "Op. 30",
    ("Sonata for Violin and Piano No. 8 in G Major, Op. 30, No. 3",),
)


def matcher(works):
    name = "classic_hubble_pipeline.music_matching"
    assert importlib.util.find_spec(name), "Structured music matcher is missing"
    return importlib.import_module(name).MusicMatcher(works)


def test_bilingual_composer_lifespan_and_catalogue_alias_identify_work():
    result = matcher([BEETHOVEN]).match(
        "Violin Sonata No.8 in G major 바이올린 소나타 8번",
        "Ludwig van Beethoven (1770 - 1827) 루트비히판 베토벤",
        catalogue="Op.30 No.3",
        key="in G major 사장조",
    )
    assert result.work_id == BEETHOVEN.id


def numbered_ballades():
    return [
        replace(
            BEETHOVEN, id=f"chopin-{number}", slug=f"chopin-{number}",
            titles=(f"Ballade No. {number} in {key}",),
            composers=("Frederic Chopin",), catalogue=catalogue, aliases=(),
        )
        for number, key, catalogue in (
            (1, "G minor", "Op. 23"),
            (2, "F major", "Op. 38"),
            (3, "A-flat major", "Op. 47"),
        )
    ]


@pytest.mark.parametrize("number", [1, 2, 3])
def test_numbered_ballades_plural_matches_only_its_number(number):
    result = matcher(numbered_ballades()).match(f"Ballades No. {number}", "F. Chopin")
    assert result.work_id == f"chopin-{number}"


@pytest.mark.parametrize("title", ["Ballades", "Ballades No. 1,2,3", "Ballades No. 1-3", "Ballades No. 5"])
def test_ballades_collection_or_missing_number_is_not_collapsed_to_one_work(title):
    assert matcher(numbered_ballades()).match(title, "F. Chopin").work_id is None


def test_ballades_plural_keeps_composer_catalogue_key_and_ambiguity_guards():
    works = numbered_ballades()
    m = matcher(works)
    assert m.match("Ballades No. 1", "F. Mendelssohn").work_id is None
    assert m.match("Ballades No. 1", "F. Chopin", catalogue="Op. 38").work_id is None
    assert m.match("Ballades No. 1", "F. Chopin", key="F major").work_id is None
    duplicate = replace(works[0], id="different-ballade")
    assert matcher([*works, duplicate]).match("Ballades No. 1", "F. Chopin").work_id is None


def test_ballades_plural_does_not_create_composerless_title_fallback():
    works = [
        replace(work, aliases=(f"Ballade No. {index}",))
        for index, work in enumerate(numbered_ballades(), start=1)
    ]
    assert matcher(works).match("Ballades No. 1", None).work_id is None


@pytest.mark.parametrize(
    "catalogue", ["Op.30 No.2", "Op.300 No.3", "Op.30 No.3; Op.31"]
)
def test_catalogue_alias_never_falls_back_to_wrong_parent_or_sibling(catalogue):
    assert (
        matcher([BEETHOVEN])
        .match(
            BEETHOVEN.titles[0],
            "Beethoven",
            catalogue=catalogue,
        )
        .work_id
        is None
    )


def test_duplicate_bilingual_catalogue_and_keys_are_not_conflicts():
    work = replace(BEETHOVEN, catalogue="Op.29", aliases=())
    result = matcher([work]).match(
        work.titles[0],
        "L. van Beethoven 베토벤",
        catalogue="op.29 op.29",
        key="G major 사장조",
    )
    assert result.work_id == work.id


@pytest.mark.parametrize("key", ["in c minor 다단조", "G major 다단조"])
def test_conflicting_key_abstains(key):
    assert (
        matcher([BEETHOVEN])
        .match(
            BEETHOVEN.titles[0],
            "Beethoven",
            catalogue="Op.30 No.3",
            key=key,
        )
        .work_id
        is None
    )


def test_conflicting_bilingual_composers_never_pick_one_side():
    other = replace(
        BEETHOVEN, id="mozart", composers=("Wolfgang Amadeus Mozart", "모차르트")
    )
    result = matcher([BEETHOVEN, other]).match(
        BEETHOVEN.titles[0],
        "Ludwig van Beethoven 모차르트",
        catalogue="Op.30 No.3",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_shared_surname_is_ambiguous_even_when_only_one_catalogue_matches():
    robert = replace(BEETHOVEN, id="robert", composers=("Robert Schumann",))
    clara = replace(
        BEETHOVEN,
        id="clara",
        composers=("Clara Schumann",),
        catalogue="Op.22",
        aliases=(),
    )
    assert matcher([robert, clara]).match("Op.30 No.3", "Schumann").work_id is None


def test_quoted_nickname_inside_long_title_matches_without_arbitrary_substring():
    work = replace(
        BEETHOVEN,
        id="tartini",
        titles=("Violin Sonata in G minor",),
        catalogue=None,
        composers=("Giuseppe Tartini",),
        aliases=("Devil's Trill",),
    )
    result = matcher([work]).match(
        'Violin Sonata in g minor, "Devil\'s Trill"', "G. Tartini"
    )
    assert result.work_id == "tartini"
    assert (
        matcher([work])
        .match("Not Devil's Trill but a different sonata", "G. Tartini")
        .work_id
        is None
    )


def test_conflicting_work_number_not_hidden_by_matching_nickname():
    work = replace(BEETHOVEN, aliases=("Spring",), catalogue=None)
    assert (
        matcher([work]).match('Violin Sonata No.9 "Spring"', "Beethoven").work_id
        is None
    )


def test_ocr_typo_only_returns_candidate_not_unverified_auto_link():
    work = replace(
        BEETHOVEN,
        id="prokofiev",
        composers=("Sergei Prokofiev",),
        catalogue="Op.56",
        aliases=(),
    )
    result = matcher([work]).match(
        "Sonata for two violins", "S.Prokofev", catalogue="Op.56"
    )
    assert result.work_id is None
    assert result.candidate_ids == ("prokofiev",)
    assert result.reason == "composer_spelling_candidate"


def test_multiple_exact_titles_remain_ambiguous():
    other = replace(BEETHOVEN, id="second")
    assert matcher([BEETHOVEN, other]).match("Op.30 No.3", "Beethoven").work_id is None


def test_alias_catalogue_conflicting_with_primary_catalogue_is_ignored():
    work = replace(BEETHOVEN, catalogue="Op.18")
    assert matcher([work]).match("Op.30 No.3", "Beethoven").work_id is None


def test_distinct_catalogue_systems_require_both_to_belong_to_same_work():
    work = replace(BEETHOVEN, catalogue="Op.104", aliases=("Cello Concerto B.191",))
    # Unsupported catalogue systems must not be silently treated as verified.
    assert (
        matcher([work])
        .match("Cello Concerto", "Beethoven", catalogue="Op.104 Op.105")
        .work_id
        is None
    )


def test_korean_numbered_title_never_degrades_to_generic_genre():
    five = replace(
        BEETHOVEN,
        id="five",
        titles=("Symphony No. 5", "교향곡 5번"),
        aliases=(),
        catalogue=None,
    )
    six = replace(five, id="six", titles=("Symphony No. 6", "교향곡 6번"))
    assert matcher([five, six]).match("교향곡 5번", "Beethoven").work_id == "five"


@pytest.mark.parametrize("title", ["Liszt", "왈츠"])
def test_polluted_composer_or_genre_only_alias_never_identifies_a_work(title):
    work = replace(
        BEETHOVEN,
        composers=("Franz Liszt",),
        titles=("Totentanz", title),
        aliases=(title,),
    )
    result = matcher([work]).match(title, "Liszt")
    assert result.work_id is None
    assert result.reason == "insufficient_title"


def test_korean_number_conflict_is_not_hidden_by_another_language():
    result = matcher([BEETHOVEN]).match(
        "Violin Sonata No.8 바이올린 소나타 9번",
        "Beethoven",
        catalogue="Op.30 No.3",
    )
    assert result.work_id is None


def test_bilingual_title_conflict_is_not_ignored_when_one_alias_matches():
    work = replace(BEETHOVEN, aliases=("Spring",), catalogue=None)
    assert (
        matcher([work]).match("Spring 피아노 협주곡 2번", "Beethoven").work_id is None
    )


@pytest.mark.parametrize("title", ["바이올린소나타제8번", "바이올린 소나타 No.08"])
def test_korean_spacing_and_number_styles_preserve_number(title):
    work = replace(BEETHOVEN, catalogue=None, aliases=())
    assert matcher([work]).match(title, "Beethoven").work_id == work.id
    assert matcher([work]).match(title.replace("8", "9"), "Beethoven").work_id is None


def test_two_catalogue_systems_recorded_on_one_work_are_both_usable():
    work = replace(
        BEETHOVEN,
        titles=("Four Impromptus, D. 899 (Op. 90)",),
        catalogue="Op.90",
        aliases=(),
    )
    assert (
        matcher([work]).match("Four Impromptus", "Beethoven", catalogue="D.899").work_id
        == work.id
    )
    assert (
        matcher([work]).match("Four Impromptus", "Beethoven", catalogue="D.900").work_id
        is None
    )
    assert (
        matcher([work])
        .match("Four Impromptus", "Beethoven", catalogue="D.899 Op.91")
        .work_id
        is None
    )


def test_single_quoted_nickname_is_recognized_but_apostrophes_do_not_split_names():
    work = replace(
        BEETHOVEN,
        titles=("Symphony No. 1 in D major",),
        catalogue=None,
        aliases=("Titan",),
    )
    assert (
        matcher([work]).match("Symphony No. 1 in D Major 'Titan'", "Beethoven").work_id
        == work.id
    )


def test_polluted_sibling_catalogue_alias_cannot_override_specific_primary_code():
    work = replace(BEETHOVEN, catalogue="Op.30 No.3", aliases=("Sonata Op.30 No.2",))
    assert (
        matcher([work]).match("Sonata", "Beethoven", catalogue="Op.30 No.2").work_id
        is None
    )


def test_catalogue_cannot_override_explicitly_conflicting_work_genre():
    assert (
        matcher([BEETHOVEN])
        .match("Piano Concerto", "Beethoven", catalogue="Op.30 No.3")
        .work_id
        is None
    )


@pytest.mark.parametrize(
    "title", ["Violin Sonata K. 301 / 293a", "Violin Sonata K.301 (293a)"]
)
def test_koechel_alternate_numbers_require_both_numbers_in_catalogue(title):
    work = CanonicalWork("w", "w", ("Violin Sonata",), ("Mozart",), "K.301; K.293a")
    assert MusicMatcher([work]).match(title, "Mozart").work_id == "w"
    wrong = CanonicalWork("x", "x", ("Violin Sonata",), ("Mozart",), "K.301")
    assert MusicMatcher([wrong]).match(title, "Mozart").work_id is None


def test_different_koechel_alternate_is_not_ignored():
    work = CanonicalWork("w", "w", ("Violin Sonata",), ("Mozart",), "K.301; K.293a")
    assert (
        MusicMatcher([work]).match("Violin Sonata K.301/293b", "Mozart").work_id is None
    )


def test_opus_slash_still_means_member_not_alternate_number():
    work = CanonicalWork("w", "w", ("Sonata",), ("Beethoven",), "Op.102 No.2")
    assert MusicMatcher([work]).match("Sonata Op.102/2", "Beethoven").work_id == "w"


def test_catalogue_number_cannot_turn_an_overture_into_an_unrelated_aria():
    m = MusicMatcher(
        [
            CanonicalWork(
                "aria",
                "aria",
                ("Welche Wonne, welche Lust",),
                ("Wolfgang Amadeus Mozart",),
                "K.384",
            )
        ]
    )
    assert (
        m.match(
            "Die Entführung aus dem Serail, K.384: Overture", "Mozart", scoped=True
        ).work_id
        is None
    )


def test_catalogue_number_with_conflicting_genre_is_not_sufficient():
    m = MusicMatcher(
        [CanonicalWork("pc", "pc", ("Piano Concerto",), ("Samuel Barber",), "Op.38")]
    )
    assert (
        m.match("Canzone for Flute and Piano, Op.38", "Samuel Barber").work_id is None
    )


def test_composer_can_omit_first_given_name_but_not_change_it():
    m = MusicMatcher(
        [CanonicalWork("h", "h", ("Example",), ("Franz Joseph Haydn",), "Op.1")]
    )
    assert m.match("Example Op.1", "Joseph Haydn").work_id == "h"
    assert m.match("Example Op.1", "J. Haydn").work_id == "h"
    assert m.match("Example Op.1", "Michael Haydn").work_id is None


def test_overture_catalogue_with_an_explicit_overture_alias_is_supported():
    m = MusicMatcher(
        [
            CanonicalWork(
                "m",
                "m",
                ("A Midsummer Night's Dream",),
                ("Felix Mendelssohn",),
                "Op.21",
                ("A Midsummer Night's Dream Overture",),
            )
        ]
    )
    assert m.match("Overture to , Op.21", "Mendelssohn", scoped=True).work_id == "m"
