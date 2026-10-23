import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher, _variants
from classic_hubble_pipeline.work_matching import CanonicalWork, _composer_matches


def capriccio(identity="니콜라이 림스키코르사코프", work_id="rimsky"):
    return CanonicalWork(
        work_id, work_id, ("Capriccio espagnol", "스페인 기상곡"),
        ("Nikolai Rimsky-Korsakov", identity), "Op.34",
    )


@pytest.mark.parametrize("printed", [
    "림스키-코르사코프", "림스키 - 코르사코프", "니콜라이 림스키-코르사코프",
    "Nikolai Rimsky-Korsakov (림스키-코르사코프)",
])
def test_observed_korean_compound_surname_is_kept_together(printed):
    result = MusicMatcher([capriccio()]).match("스페인 기상곡", printed, catalogue="Op.34")
    assert result.work_id == "rimsky"


@pytest.mark.parametrize("printed", [
    "림스키", "코르사코프", "림스키-모차르트", "베토벤-코르사코프",
    "표트르 림스키-코르사코프", "림스키-코르사코프-베토벤",
])
def test_unknown_or_conflicting_compound_names_are_not_guessed(printed):
    result = MusicMatcher([capriccio()]).match("스페인 기상곡", printed, catalogue="Op.34")
    assert result.work_id is None


def test_catalogue_conflict_is_preserved():
    result = MusicMatcher([capriccio()]).match("스페인 기상곡", "림스키-코르사코프", catalogue="Op.35")
    assert result.work_id is None


def test_shared_surname_does_not_choose_between_composers():
    other = CanonicalWork("other", "other", ("스페인 기상곡",), ("알렉산드르 림스키코르사코프",), "Op.34")
    assert MusicMatcher([capriccio(), other]).match("스페인 기상곡", "림스키-코르사코프", catalogue="Op.34").work_id is None


def test_distinct_bilingual_composer_evidence_stays_conflicting():
    other = CanonicalWork("mozart", "mozart", ("Other",), ("Wolfgang Amadeus Mozart", "모차르트"), "K.1")
    result = MusicMatcher([capriccio(), other]).match(
        "스페인 기상곡", "W. A. Mozart (림스키-코르사코프)", catalogue="Op.34",
    )
    assert result.work_id is None
    assert result.reason == "conflicting_composers"


def test_title_variants_and_legacy_composer_matching_are_unchanged():
    assert _variants("림스키-코르사코프") == ("림스키", "-", "코르사코프")
    assert not _composer_matches("림스키-코르사코프", ("니콜라이 림스키코르사코프",))
