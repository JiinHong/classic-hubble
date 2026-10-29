from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


WEBER = CanonicalWork(
    "weber-clarinet-2", "weber-clarinet-2", ("Clarinet Concerto No. 2",),
    ("Carl Maria von Weber",), "Op. 74",
)


@pytest.mark.parametrize("composer", ["C.v.Weber", "C. von Weber", "Carl von Weber"])
def test_middle_given_name_may_be_omitted_before_particle(composer):
    assert MusicMatcher([WEBER]).match("Clarinet Concerto No.2", composer).work_id == WEBER.id


@pytest.mark.parametrize("composer", ["M.v.Weber", "A.v.Weber", "C.de.Weber", "C.m.Weber", "C.v.Webern"])
def test_particle_abbreviation_cannot_change_given_initial_particle_or_surname(composer):
    assert MusicMatcher([WEBER]).match("Clarinet Concerto No.2", composer).work_id is None


def test_middle_name_omission_keeps_composer_and_work_ambiguity():
    other_composer = replace(WEBER, id="other", composers=("Charles Louis von Weber",))
    assert MusicMatcher([WEBER, other_composer]).match("Clarinet Concerto No.2", "C.v.Weber").work_id is None
    duplicate = replace(WEBER, id="duplicate")
    assert MusicMatcher([WEBER, duplicate]).match("Clarinet Concerto No.2", "C.v.Weber").work_id is None


def test_middle_name_omission_preserves_explicit_work_number():
    assert MusicMatcher([WEBER]).match("Clarinet Concerto No.1", "C.v.Weber", catalogue="Op.74").work_id is None
