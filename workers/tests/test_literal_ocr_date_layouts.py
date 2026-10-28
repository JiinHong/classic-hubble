import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize("heading", [
    "2026.10.14.()19:30", "2026.10.14 ( ) 19:30",
    "2026.10.14()7:30PM", "2026.10.14.() 7 PM",
])
def test_empty_weekday_brackets_with_explicit_valid_date_and_clock(heading):
    assert date_headings([heading]) == ({(2026, 10, 14)}, False)
    assert _date_matches({"lines": [{"text": heading}]}, "2026-10-14")


@pytest.mark.parametrize("heading", [
    "202610.2(금)오후6시", "202610.02(Fri) 18:00",
    "202610월2일(금) 18:00",
])
def test_compact_four_digit_year_two_digit_month_is_unambiguous(heading):
    assert date_headings([heading]) == ({(2026, 10, 2)}, False)
    assert _date_matches({"lines": [{"text": heading}]}, "2026-10-02")


@pytest.mark.parametrize("heading", [
    "2026.10.14.()", "2026.10.14.()19", "2026.10.14.()24:00",
    "2026.10.14.()19:60", "2026.10.14.()00:30AM",
    "2026.10.14.()13:30PM", "2026.10.14.(X)19:30",
    "2026.10.14.(목)19:30", "2026.10.14.()19:300",
    "2026.10.14.()19:30PMX", "2026.10.14.()19:30 10.15(목)",
    "10.14.()19:30", "202613.2(금)", "202610.32(금)",
    "202610.2(목)", "202610.2(금) & 10.3(토)", "2026102(금)",
])
def test_unsupported_or_conflicting_layout_is_not_a_date_match(heading):
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-14")
    assert not _date_matches({"lines": [{"text": heading}]}, "2026-10-02")


def test_literal_formats_embedded_in_biography_do_not_count():
    assert date_headings(["데뷔 202610.2(금)", "연주 2026.10.14.()19:30"]) == (set(), False)


def test_empty_day_layout_does_not_hide_wrapped_conflicting_weekday():
    assert not _date_matches({"lines": [
        {"text": "2026.10.14.()19:30"}, {"text": "(목)"},
    ]}, "2026-10-14")
