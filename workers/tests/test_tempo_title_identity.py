import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


TEMPO_LABELS = (
    "Lento",
    "Largo",
    "Semplice",
    "Moderato con moto",
    "Rondo: Allegro ma non troppo",
    "Rondo. Allegretto",
    "Allegretto",
    "Andante Grazioso",
)


@pytest.mark.parametrize("title", TEMPO_LABELS)
def test_tempo_label_alone_is_not_a_unique_work_identity(title):
    # Cached source 0e6afc95 has Lento inside an Ornstein sonata, not Rachmaninoff.
    work = CanonicalWork("other", "other", (title,), ("Sergei Rachmaninoff",), None)
    result = MusicMatcher([work]).match(title, None)
    assert result.work_id is None
    assert result.reason != "unique_distinctive_title"


@pytest.mark.parametrize("title", TEMPO_LABELS)
def test_explicit_composer_still_identifies_same_named_work(title):
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert MusicMatcher([work]).match(title, "Example Composer").work_id == "w"


@pytest.mark.parametrize("title", ("Largo al factotum", "Allegro barbaro", "Rondo capriccioso"))
def test_distinctive_words_in_named_works_are_preserved(title):
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert MusicMatcher([work]).match(title, None).work_id == "w"


def test_ensemble_section_heading_is_not_a_unique_work_identity():
    # Source 0cbac8f5 uses ENSEMBLE as the heading above arranged cello works.
    work = CanonicalWork("w", "w", ("Ensemble",), ("Example Composer",), None)
    assert MusicMatcher([work]).match("ENSEMBLE", None).work_id is None


def test_explicit_composer_preserves_a_work_named_ensemble():
    work = CanonicalWork("w", "w", ("Ensemble",), ("Example Composer",), None)
    assert MusicMatcher([work]).match("Ensemble", "Example Composer").work_id == "w"


def test_distinctive_ensemble_title_is_preserved():
    title = "Ensemble of Memories"
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert MusicMatcher([work]).match(title, None).work_id == "w"
