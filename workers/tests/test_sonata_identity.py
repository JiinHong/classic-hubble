import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


def sonata(title, aliases=()):
    return CanonicalWork("flute14", "flute14", (title,), ("Robert Muczynski",), "Op.14", aliases)


@pytest.mark.parametrize("title", [
    "Sonata for Alto Saxophone and Piano", "Alto Saxophone Sonata",
    "Sonata for Alto Sax and Piano", "색소폰 소나타", "Piano Sonata",
    "Violin Sonata", "Sonata for Violin and Piano",
])
def test_catalogue_cannot_turn_flute_sonata_into_another_instrument(title):
    result = MusicMatcher([sonata("Sonata for Flute and Piano")]).match(
        title, "Robert Muczynski", catalogue="Op.14",
    )
    assert result.work_id is None


@pytest.mark.parametrize("actual,canonical", [
    ("Flute Sonata", "Sonata for Flute and Piano"),
    ("Sonata for Flute and Piano", "Flute Sonata"),
    ("플루트와 피아노를 위한 소나타", "Sonata for Flute and Piano"),
    ("Sonata for Alto Saxophone and Piano", "Alto Saxophone Sonata"),
    ("Piano Sonata", "Sonata for Piano"),
    ("Cello Sonata", "Sonata for Violoncello and Piano"),
])
def test_explicit_accompaniment_does_not_change_sonata_identity(actual, canonical):
    assert MusicMatcher([sonata(canonical)]).match(actual, "Robert Muczynski", catalogue="Op.14").work_id == "flute14"


def test_a_misleading_alias_cannot_override_primary_sonata_instrument():
    work = sonata("Sonata for Flute and Piano", ("Sonata for Alto Saxophone and Piano",))
    assert MusicMatcher([work]).match(work.aliases[0], "Robert Muczynski", catalogue="Op.14").work_id is None


def test_missing_primary_instrument_is_not_invented():
    assert MusicMatcher([sonata("Sonata")]).match("Flute Sonata", "Robert Muczynski", catalogue="Op.14").work_id == "flute14"


def test_existing_scoped_arrangement_parent_candidate_is_preserved():
    assert MusicMatcher([sonata("Sonata for Flute and Piano")]).match(
        "Sonata for Alto Saxophone and Piano", "Robert Muczynski", catalogue="Op.14", scoped=True,
    ).work_id == "flute14"


def test_shared_piano_accompaniment_does_not_make_violin_and_flute_agree():
    assert MusicMatcher([sonata("Violin Sonata and Piano")]).match(
        "Sonata for Flute and Piano", "Robert Muczynski", catalogue="Op.14",
    ).work_id is None
