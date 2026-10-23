import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork, _composer_matches


def piece(identity="Pablo de Sarasate", work_id="sarasate"):
    return CanonicalWork(work_id, work_id, ("Zigeunerweisen",), (identity,), "Op.20")


@pytest.mark.parametrize("printed", ["P. Sarasate", "P.Sarasate", "Pablo Sarasate"])
def test_observed_name_can_omit_middle_de(printed):
    assert MusicMatcher([piece()]).match("Zigeunerweisen", printed, catalogue="Op.20").work_id == "sarasate"


@pytest.mark.parametrize("printed", ["Pablo de Sarasate", "P. de Sarasate", "Sarasate"])
def test_existing_full_and_surname_spellings_remain_supported(printed):
    assert MusicMatcher([piece()]).match("Zigeunerweisen", printed, catalogue="Op.20").work_id == "sarasate"


@pytest.mark.parametrize("printed", ["R. Sarasate", "Peter Sarasate", "R. Schumann"])
def test_omitted_particle_does_not_discard_given_name(printed):
    assert MusicMatcher([piece()]).match("Zigeunerweisen", printed, catalogue="Op.20").work_id is None


def test_middle_personal_name_is_not_treated_as_particle():
    assert MusicMatcher([piece("Pablo Maria Sarasate")]).match("Zigeunerweisen", "P. Sarasate", catalogue="Op.20").work_id is None


def test_abbreviation_collision_stays_ambiguous():
    matcher = MusicMatcher([piece(), piece("Pedro de Sarasate", "other")])
    result = matcher.match("Zigeunerweisen", "P. Sarasate", catalogue="Op.20")
    assert result.work_id is None


def test_omitted_particle_does_not_override_catalogue():
    result = MusicMatcher([piece()]).match("Zigeunerweisen", "P. Sarasate", catalogue="Op.21")
    assert result.work_id is None


def test_legacy_name_matching_is_unchanged():
    assert _composer_matches("P. Sarasate", ("Pablo de Sarasate",)) is False


def beethoven(identity="Ludwig van Beethoven", work_id="beethoven"):
    return CanonicalWork(work_id, work_id, ("Romance No.2 in F major",), (identity,), "Op.50")


@pytest.mark.parametrize("printed", ["L.Beethoven", "L. Beethoven", "Ludwig Beethoven"])
def test_observed_beethoven_name_can_omit_middle_van(printed):
    result = MusicMatcher([beethoven()]).match("Romance No.2 in F major", printed, catalogue="Op.50")
    assert result.work_id == "beethoven"


@pytest.mark.parametrize("printed", ["L.v.Beethoven", "L. van Beethoven", "Ludwig van Beethoven", "Beethoven"])
def test_existing_beethoven_spellings_are_preserved(printed):
    result = MusicMatcher([beethoven()]).match("Romance No.2 in F major", printed, catalogue="Op.50")
    assert result.work_id == "beethoven"


@pytest.mark.parametrize("printed", ["R.Beethoven", "Louis Beethoven", "Ludwig Maria Beethoven"])
def test_omitting_van_does_not_discard_conflicting_given_names(printed):
    assert MusicMatcher([beethoven()]).match("Romance No.2 in F major", printed, catalogue="Op.50").work_id is None


def test_beethoven_initial_collision_is_not_forced():
    matcher = MusicMatcher([beethoven(), beethoven("Louis van Beethoven", "other")])
    assert matcher.match("Romance No.2 in F major", "L.Beethoven", catalogue="Op.50").work_id is None


def test_beethoven_omitted_particle_keeps_catalogue_constraint():
    assert MusicMatcher([beethoven()]).match("Romance No.2 in F major", "L.Beethoven", catalogue="Op.51").work_id is None


def test_beethoven_middle_personal_name_and_legacy_rules_are_unchanged():
    result = MusicMatcher([beethoven("Ludwig Maria Beethoven")]).match("Romance No.2 in F major", "L.Beethoven", catalogue="Op.50")
    assert result.work_id is None
    assert _composer_matches("L.Beethoven", ("Ludwig van Beethoven",)) is False
