import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize("heading", [
    "2026.10.10.SAT6:00PM부산문화회관 챔버홀",
    "2026.10.10SAT18:00부산문화회관",
    "2026.10.10토18:00부산문화회관",
    "2026.10.10Saturday6:00 PM부산문화회관",
])
def test_joined_clock_accepts_korean_text_boundary(heading):
    assert date_headings([heading]) == ({(2026, 10, 10)}, False)
    assert _date_matches({"lines": [{"text": heading}]}, "2026-10-10")


@pytest.mark.parametrize("heading", [
    "2026.10.10.SUN6:00PM부산문화회관", "2026.10.10.SAT13:00PM부산",
    "2026.10.10.SAT00:00AM부산", "2026.10.10.SAT6:60PM부산",
    "2026.10.10.SAT6:000PM부산", "2026.10.10.SAT6:0PM부산",
    "2026.10.10.SAT6:00PMX부산", "2026.10.10.SAT24:00부산",
])
def test_korean_suffix_does_not_accept_invalid_clock_or_weekday(heading):
    assert date_headings([heading])[1]
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-10")


@pytest.mark.parametrize("heading", [
    "2026.10.10.SAT6:00PM부산 2026.10.11.SUN6:00PM서울",
    "2026.10.10.SAT6:00PM부산 & 10.11SUN6:00PM서울",
])
def test_joined_venue_never_hides_another_date(heading):
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-10")


def test_biography_with_joined_korean_date_is_not_a_heading():
    assert date_headings(["데뷔 2026.10.10.SAT6:00PM부산"]) == (set(), False)
