import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher, _keys
from classic_hubble_pipeline.work_matching import CanonicalWork


@pytest.mark.parametrize("printed,expected", [
    ("F\u2013sharp major", "f#:major"),
    ("E\u2013flat minor", "eb:minor"),
])
def test_en_dash_accidental_has_the_same_key_as_a_hyphen(printed, expected):
    assert _keys(printed) == frozenset({expected})


def test_cached_barcarolle_en_dash_key_matches_with_explicit_opus():
    work = CanonicalWork("barcarolle", "barcarolle", ("Barcarolle in F-sharp major",),
                         ("Frederic Chopin",), "Op.60")
    result = MusicMatcher([work]).match(
        "Barcarolle in F\u2013sharp major", "Frederic Chopin",
        catalogue="Op.60", key="F\u2013sharp major",
    )
    assert result.work_id == "barcarolle"


def test_en_dash_key_cannot_override_a_conflicting_printed_key():
    work = CanonicalWork("barcarolle", "barcarolle", ("Barcarolle in F-sharp major",),
                         ("Frederic Chopin",), "Op.60")
    result = MusicMatcher([work]).match(
        "Barcarolle in F major", "Frederic Chopin",
        catalogue="Op.60", key="F\u2013sharp major",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_keys"


@pytest.mark.parametrize("printed", ["F\u2013\u2013sharp major", "F\u2013shorp major", "NotF\u2013sharp major"])
def test_damaged_accidentals_still_require_review(printed):
    assert not _keys(printed)
