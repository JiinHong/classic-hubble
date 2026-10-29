import pytest

from classic_hubble_pipeline.performance_dates import date_headings


@pytest.mark.parametrize("lines", [
    ["2026.09.18", "FRI7.30PM"],
    ["2026.09.18 FRI7.30PM"],
    ["2026.09.18 (FRI) 7.30 PM"],
    ["2026", "09.18", "FRI7.30PM"],
    ["2026.09.18", "음악홀", "Friday at 7.30 pm"],
    ["2026.09.18", "FRI12.00AM"],
])
def test_literal_decimal_time_requires_explicit_meridiem(lines):
    original = list(lines)
    assert date_headings(lines) == ({(2026, 9, 18)}, False)
    assert lines == original


@pytest.mark.parametrize("clock", [
    "FRI7.30", "FRI7.3PM", "FRI7.300PM", "FRI7.60PM", "FRI13.30PM",
    "FRI00.30AM", "SAT7.30PM", "FRI7.3oPM", "FRI7.30PMX",
    "FRI7.30PM 9.19", "FRI7.30PM & 9.19 SAT",
])
def test_decimal_clock_does_not_repair_or_discard_conflicting_text(clock):
    for lines in (["2026.09.18", clock], ["2026.09.18 " + clock]):
        dates, invalid = date_headings(lines)
        assert invalid or dates != {(2026, 9, 18)}


def test_decimal_clock_preserves_separate_event_dates():
    assert date_headings(["2026.09.18", "FRI7.30PM", "2026.09.19 SAT 7PM"]) == (
        {(2026, 9, 18), (2026, 9, 19)}, False)


def test_decimal_clock_is_not_a_date_without_a_date_heading():
    assert date_headings(["FRI7.30PM"]) == (set(), False)


def test_decimal_clock_cannot_hide_a_second_date_in_same_heading():
    assert date_headings(["2026.09.18 FRI7.30PM & 9.19 SAT 7PM"]) == (
        {(2026, 9, 18), (2026, 9, 19)}, False)
