import pytest

from classic_hubble_pipeline.performance_dates import date_headings


@pytest.mark.parametrize("lines", [
    ["2026.09.18", "FRI.19:00"],
    ["2026.09.18", "FRI. 7:30 pm"],
    ["2026.09.18/ Fri. 7:30 pm"],
    ["2026.09.18 / Friday. 19:30"],
    ["2026", "09.18", "FRI.19:00"],
    ["2026.09.18", "음악홀", "Friday. at 7:30 pm"],
])
def test_literal_weekday_punctuation_does_not_change_date(lines):
    original = list(lines)
    assert date_headings(lines) == ({(2026, 9, 18)}, False)
    assert lines == original


@pytest.mark.parametrize("clock", [
    "SAT.19:00", "FR1.19:00", "FRI.25:00", "FRI.19:60", "FRI.13:30PM",
    "FRI.00:30AM", "FRI.19:0o", "FRI.7.30", "FRI..19:00",
    "FRI.7:30PM 9.19", "FRI.7:30PM & 9.19 SAT", "FRI. 25:00", "FRI. 19:60",
])
def test_weekday_punctuation_cannot_fix_corrupt_or_conflicting_evidence(clock):
    for lines in (["2026.09.18", clock], ["2026.09.18/ " + clock]):
        dates, invalid = date_headings(lines)
        assert invalid or dates != {(2026, 9, 18)}


def test_slash_does_not_hide_another_performance_date():
    dates, invalid = date_headings(["2026.09.18/ Fri. 7:30 pm & 9.19 SAT 7PM"])
    assert dates == {(2026, 9, 18), (2026, 9, 19)}
    assert not invalid


def test_punctuation_without_a_date_does_not_create_one():
    assert date_headings(["FRI.19:00"]) == (set(), False)
