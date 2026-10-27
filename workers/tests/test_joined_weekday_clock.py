import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize("heading", [
    "2026.10.6TUE7:30PM 롯데콘서트홀",
    "2026.10.6.TUE19:30 Main Hall",
    "2026.10.6Tuesday7:30PM",
    "2026.10.6화19:30",
])
def test_observed_joined_weekday_and_clock(heading):
    assert date_headings([heading]) == ({(2026, 10, 6)}, False)
    assert _date_matches({"lines": [{"text": heading}]}, "2026-10-06")
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-07")


@pytest.mark.parametrize("heading", [
    "2026.10.6MON7:30PM", "2026.10.6TUE25:00", "2026.10.6TUE19:60",
    "2026.10.6TUE13:30PM", "2026.10.6TUE00:30AM", "2026.10.6TUE7:30PMX",
    "2026.10.6TUE7:300", "2026.10.6TUE7:3PM", "2026.10.6TUE730PM",
    "2026.10.6TUE7", "2026.10.6TUEfoo", "2026.02.30MON19:30",
    "2026.10.6TUE13:30 PM", "2026.10.6TUE00:30 AM",
])
def test_joined_heading_does_not_guess_or_accept_bad_clock(heading):
    assert date_headings([heading])[1] is True
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-06")


def test_joined_heading_keeps_other_dates_visible():
    heading = "2026.10.6TUE7:30PM & 10.7WED7:30PM"
    assert date_headings([heading]) == ({(2026, 10, 6), (2026, 10, 7)}, False)
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-06")


def test_joined_heading_can_span_adjacent_date_and_weekday_lines():
    assert date_headings(["2026.10.6.", "TUE7:30PM"]) == ({(2026, 10, 6)}, False)


def test_embedded_joined_biography_date_is_not_a_heading():
    assert date_headings(["Debuted 2026.10.6TUE7:30PM"]) == (set(), False)


def test_joined_heading_retains_source_year_and_yearless_validation():
    assert not _date_matches({"lines": [{"text": "2025.10.6MON7:30PM"}]}, "2026-10-06")
    assert date_headings(["10.6TUE7:30PM"], fallback_year=2026) == ({(2026, 10, 6)}, False)


def test_joined_clock_cannot_hide_conflicting_adjacent_weekday():
    assert not _date_matches({"lines": [{"text": "2026.10.6.19:30"}, {"text": "MON7:30PM Hall"}]}, "2026-10-06")
