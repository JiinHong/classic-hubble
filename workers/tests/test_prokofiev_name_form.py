from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SONATA = CanonicalWork(
    "prokofiev-7", "prokofiev-7", ("Piano Sonata No. 7 in B-flat major",),
    ("Sergei Prokofiev",), "Op. 83",
)
PRINTED_TITLE = 'Piano Sonata No.7 in B-flat Major, "War Sonata 2/Stalingrad"'


@pytest.mark.parametrize("composer", ["Sergey Prokofiev", "SERGEY PROKOFIEV", "Sergei Prokofiev"])
def test_verified_prokofiev_name_form_retains_identity(composer):
    result = MusicMatcher([SONATA]).match(
        PRINTED_TITLE, composer, catalogue="Op.83", key="B-flat Major",
    )
    assert result.work_id == SONATA.id


@pytest.mark.parametrize("composer", [
    "Sergey Prokofievv", "Sergey Prokoflev", "Alexander Prokofiev", "A. Prokofiev",
])
def test_prokofiev_form_does_not_accept_typos_or_different_person(composer):
    assert MusicMatcher([SONATA]).match(
        PRINTED_TITLE, composer, catalogue="Op.83",
    ).work_id is None


@pytest.mark.parametrize("title,catalogue,key", [
    (PRINTED_TITLE, "Op.84", "B-flat major"),
    (PRINTED_TITLE, "Op.83", "B major"),
    ("Violin Sonata No. 7 in B-flat major", "Op.83", "B-flat major"),
])
def test_prokofiev_form_keeps_conflicting_work_evidence_blocked(title, catalogue, key):
    assert MusicMatcher([SONATA]).match(
        title, "Sergey Prokofiev", catalogue=catalogue, key=key,
    ).work_id is None


def test_prokofiev_form_preserves_duplicate_identity_ambiguity():
    result = MusicMatcher([SONATA, replace(SONATA, id="other")]).match(
        PRINTED_TITLE, "Sergey Prokofiev", catalogue="Op.83",
    )
    assert result.work_id is None
    assert result.reason == "ambiguous"


def test_prokofiev_form_does_not_approve_unreviewed_catalogue():
    result = MusicMatcher([replace(SONATA, requires_review=True)]).match(
        PRINTED_TITLE, "Sergey Prokofiev", catalogue="Op.83",
    )
    assert result.work_id is None
    assert result.reason == "catalog_review_required"
