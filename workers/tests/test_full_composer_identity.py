import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


CLARA = CanonicalWork(
    "clara", "clara", ("Three Romances for Violin and Piano",),
    ("Clara Schumann",), "Op.22",
)


@pytest.mark.parametrize("name", [
    "Clara Josephine Schumann (1819\u20131896)",
    "Clara Josephine Schumann", "C. J. Schumann",
])
def test_verified_full_name_identifies_existing_clara_work(name):
    result = MusicMatcher([CLARA]).match(CLARA.titles[0], name, catalogue="Op.22")
    assert result.work_id == "clara"


@pytest.mark.parametrize("name", [
    "Clara Johanna Schumann", "Clara Marie Schumann", "Robert Josephine Schumann",
])
def test_unverified_personal_names_are_not_discarded(name):
    assert MusicMatcher([CLARA]).match(CLARA.titles[0], name).work_id is None


def test_verified_name_keeps_catalogue_constraint():
    assert MusicMatcher([CLARA]).match(
        CLARA.titles[0], "Clara Josephine Schumann", catalogue="Op.13",
    ).work_id is None


def test_full_name_does_not_override_other_named_composer():
    robert = CanonicalWork("robert", "robert", ("Other Work",), ("Robert Schumann", "로베르트 슈만"), None)
    result = MusicMatcher([CLARA, robert]).match(
        CLARA.titles[0], "Clara Josephine Schumann 로베르트 슈만",
    )
    assert result.work_id is None


def test_full_name_initial_collision_stays_ambiguous():
    other = CanonicalWork("other", "other", CLARA.titles, ("Carla Josephine Schumann",), "Op.22")
    assert MusicMatcher([CLARA, other]).match(CLARA.titles[0], "C. J. Schumann").work_id is None


def test_legacy_clara_name_still_matches():
    assert MusicMatcher([CLARA]).match(CLARA.titles[0], "Clara Schumann").work_id == "clara"


@pytest.mark.parametrize("canonical,observed", [
    ("Ethel Smyth", "Ethel Mary Smyth (1858\u20131944)"),
    ("Cécile Chaminade", "Cécile Louise Stéphanie Chaminade (1857\u20131944)"),
    ("Fanny Hensel", "Fanny Mendelssohn-Hensel (1805\u20131847)"),
])
def test_other_observed_full_names_use_verified_identity(canonical, observed):
    work = CanonicalWork("work", "work", ("Distinctive Song",), (canonical,), None)
    assert MusicMatcher([work]).match("Distinctive Song", observed).work_id == "work"


@pytest.mark.parametrize("canonical,observed", [
    ("Ethel Smyth", "Ethel Maria Smyth"),
    ("Cécile Chaminade", "Cécile Louise Sophie Chaminade"),
    ("Fanny Hensel", "Felix Mendelssohn-Hensel"),
])
def test_verified_full_names_do_not_generalize_to_similar_people(canonical, observed):
    work = CanonicalWork("work", "work", ("Distinctive Song",), (canonical,), None)
    assert MusicMatcher([work]).match("Distinctive Song", observed).work_id is None
