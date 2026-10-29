from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher, _catalogues
from classic_hubble_pipeline.work_matching import CanonicalWork


FIRST = CanonicalWork(
    "organ-first", "organ-first", ("Prelude and Fugue in C minor, Op. 37 No. 1",),
    ("Felix Mendelssohn",), "Op. 37 No. 1",
)


@pytest.mark.parametrize("title", [
    "Prelude and Fugue in c minor, No. 1, Op. 37",
    "Prelude and Fugue in C minor No.1 Op.37",
])
def test_cached_organ_program_reordered_member_matches_exact_primary_identity(title):
    result = MusicMatcher([FIRST]).match(title, "F. Mendelssohn")
    assert result.work_id == FIRST.id
    assert result.reason == "composer_and_catalogue"


@pytest.mark.parametrize("title", [
    "Prelude and Fugue in C minor, No. 2, Op. 37",
    "Prelude and Fugue in G major, No. 1, Op. 37",
    "Prelude and Fugue, No. 1, Op. 37",
    "Prelude and Fugue in C minor, Op. 37",
    "Prelude and Fugue in C minor, No. 1, Op. 35",
    "Prelude and Fugue in C minor, No. 1, Op. 37 No. 2",
    "Prelude and Fugue in C minor, No. 1, No. 2, Op. 37",
    "Another piece in C minor, No. 1, Op. 37",
    "Prelude and Fugue in C minor, No. 1, Op. 37; Op. 38",
])
def test_reordered_member_rejects_incomplete_or_conflicting_identity(title):
    assert MusicMatcher([FIRST]).match(title, "F. Mendelssohn").work_id is None


@pytest.mark.parametrize("composer", [None, "Other Composer"])
def test_reordered_member_needs_explicit_composer(composer):
    assert MusicMatcher([FIRST]).match(
        "Prelude and Fugue in c minor, No. 1, Op. 37", composer,
    ).work_id is None


def test_alias_cannot_supply_canonical_member_identity():
    work = replace(FIRST, titles=("Organ work",), aliases=FIRST.titles)
    assert MusicMatcher([work]).match(
        "Prelude and Fugue in c minor, No. 1, Op. 37", "F. Mendelssohn",
    ).work_id is None


def test_conflicting_primary_catalogue_cannot_supply_member_identity():
    work = replace(FIRST, titles=("Prelude and Fugue in C minor, Op. 38 No. 1",))
    assert MusicMatcher([work]).match(
        "Prelude and Fugue in c minor, No. 1, Op. 37", "F. Mendelssohn",
    ).work_id is None


def test_reordered_member_preserves_duplicate_and_review_holds():
    title = "Prelude and Fugue in c minor, No. 1, Op. 37"
    duplicate = replace(FIRST, id="duplicate", slug="duplicate")
    assert MusicMatcher([FIRST, duplicate]).match(title, "F. Mendelssohn").reason == "ambiguous"
    assert MusicMatcher([replace(FIRST, requires_review=True)]).match(title, "F. Mendelssohn").work_id is None
    assert MusicMatcher([FIRST]).match(title, "F. Mendelssohn", scoped=True).work_id is None


def test_work_ordinal_is_not_rewritten_as_opus_member():
    title = "Symphony No. 5 in C minor, Op. 67"
    assert _catalogues(title) == frozenset({"op67"})
    work = CanonicalWork("fifth", "fifth", (title,), ("Ludwig van Beethoven",), "Op. 67")
    assert MusicMatcher([work]).match(title, "L. van Beethoven").work_id == work.id


def test_original_member_order_still_matches():
    assert MusicMatcher([FIRST]).match(FIRST.titles[0], "F. Mendelssohn").work_id == FIRST.id
