from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


GHOST = CanonicalWork(
    "ghost", "graceful-ghost-rag", ("Graceful Ghost Rag",), ("William Bolcom",), None,
)


@pytest.mark.parametrize("composer", ["W. Bolcom", "William Bolcom"])
def test_repeated_explicit_composer_prefix_is_not_part_of_work_title(composer):
    result = MusicMatcher([GHOST]).match(f"{composer} - Graceful Ghost Rag", composer)
    assert result.work_id == "ghost"


@pytest.mark.parametrize("title,composer", [
    ("W. Bolcom - Graceful Ghost Rag", None),
    ("W. Mozart - Graceful Ghost Rag", "W. Bolcom"),
    ("A. Bolcom - Graceful Ghost Rag", "A. Bolcom"),
    ("W. Bolcom: Graceful Ghost Rag", "W. Bolcom"),
    ("W. Bolcom - ", "W. Bolcom"),
])
def test_prefix_does_not_infer_missing_or_conflicting_composer(title, composer):
    assert MusicMatcher([GHOST]).match(title, composer).work_id is None


def test_prefix_keeps_duplicate_work_ambiguity():
    result = MusicMatcher([GHOST, replace(GHOST, id="duplicate")]).match(
        "W. Bolcom - Graceful Ghost Rag", "W. Bolcom",
    )
    assert result.work_id is None
    assert result.reason == "ambiguous"


def test_prefix_does_not_promote_unreviewed_catalogue():
    result = MusicMatcher([replace(GHOST, requires_review=True)]).match(
        "W. Bolcom - Graceful Ghost Rag", "W. Bolcom",
    )
    assert result.work_id is None
    assert result.reason == "catalog_review_required"


@pytest.mark.parametrize("title,catalogue,key", [
    ("Violin Concerto No. 1 in D major", "Op.36", None),
    ("Violin Concerto No. 1 in D major", "Op.35", "D minor"),
    ("Violin Concerto No. 2 in D major", "Op.35", None),
    ("Piano Concerto No. 1 in D major", "Op.35", None),
    ("Violin Sonata No. 1 in D major", "Op.35", None),
])
def test_prefix_preserves_identity_constraints(title, catalogue, key):
    work = CanonicalWork(
        "concerto", "concerto", ("Violin Concerto No. 1 in D major",),
        ("Pyotr Ilyich Tchaikovsky",), "Op.35",
    )
    assert MusicMatcher([work]).match(
        f"P. I. Tchaikovsky - {title}", "P. I. Tchaikovsky", catalogue=catalogue, key=key,
    ).work_id is None
