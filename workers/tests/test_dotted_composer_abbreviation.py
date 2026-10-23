import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork, _composer_matches


FAUST = CanonicalWork("gounod", "gounod", ("Faust",), ("Charles Gounod", "구노"), None)


@pytest.mark.parametrize("printed", ["Ch. Gounod", "Ch.Gounod", "CH. GOUNOD", "Ch. Gounod (1818-1893)"])
def test_observed_dotted_two_letter_composer_abbreviation(printed):
    assert MusicMatcher([FAUST]).match("Faust", printed).work_id == "gounod"


@pytest.mark.parametrize("printed", ["Ch Gounod", "Ch.. Gounod", "Ch. Gou", "Ch. Gounodd", "Cl. Gounod", "Chris Gounod"])
def test_abbreviation_does_not_repair_literal_names_or_surnames(printed):
    assert MusicMatcher([FAUST]).match("Faust", printed).work_id is None


@pytest.mark.parametrize("printed", ["Charles Gounod", "C. Gounod", "Gounod"])
def test_existing_composer_spellings_remain_valid(printed):
    assert MusicMatcher([FAUST]).match("Faust", printed).work_id == "gounod"


def test_dotted_abbreviation_retains_ambiguous_composer_identity():
    other = CanonicalWork("other", "other", ("Faust",), ("Christian Gounod",), None)
    assert MusicMatcher([FAUST, other]).match("Faust", "Ch. Gounod").work_id is None


def test_dotted_abbreviation_does_not_drop_middle_personal_names():
    other = CanonicalWork("other", "other", ("Faust",), ("Charles Francois Gounod",), None)
    assert MusicMatcher([other]).match("Faust", "Ch. Gounod").work_id is None


def test_dotted_abbreviation_retains_bilingual_conflict():
    other = CanonicalWork("sch", "sch", ("Carnaval",), ("Robert Schumann", "슈만"), "Op.9")
    match = MusicMatcher([FAUST, other]).match("Faust", "Ch. Gounod 슈만")
    assert match.work_id is None and match.reason == "conflicting_composers"


def test_dotted_abbreviation_cannot_override_catalogue():
    assert MusicMatcher([FAUST]).match("Faust", "Ch. Gounod", catalogue="Op.9").work_id is None


def test_observed_aria_context_can_identify_parent_without_losing_scope():
    match = MusicMatcher([FAUST]).match(
        "Avant de quitter ces lieux - 오페라 'Faust'중", "Ch. Gounod", scoped=True,
    )
    assert match.work_id == "gounod"


def test_legacy_name_matching_is_unchanged():
    assert not _composer_matches("Ch. Gounod", ("Charles Gounod",))
