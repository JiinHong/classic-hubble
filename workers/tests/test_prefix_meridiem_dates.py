import pytest

from classic_hubble_pipeline.performance_dates import date_headings


@pytest.mark.parametrize("lines", [
    ["2026.9.17.THU. PM7:30"],
    ["2026.9.17 THU. am 11:00"],
    ["2026.9.17", "THU. PM7:30"],
    ["2026", "9.17", "THU. PM7:30"],
    ["2026.9.17", "음악홀", "Thursday. at PM7:30"],
])
def test_prefix_meridiem_is_a_clock_not_a_date_conflict(lines):
    original = list(lines)
    assert date_headings(lines) == ({(2026, 9, 17)}, False)
    assert lines == original


@pytest.mark.parametrize("tail", [
    "FRI. PM7:30", "THU. PM13:30", "THU. AM00:30", "THU. PM7:60",
    "THU. PM7:3O", "THU. PM7.30", "THU. PM7:30AM", "THU. PM",
    "THU. PM7:30 9.18", "THU. PM7:30 & 9.18 FRI PM7:30",
    "THU. PM7:30 9.18PM", "THU. PM7:30 AM8:00",
])
def test_prefix_meridiem_cannot_mask_invalid_or_additional_dates(tail):
    for lines in (["2026.9.17 " + tail], ["2026.9.17", tail]):
        dates, invalid = date_headings(lines)
        assert invalid or dates != {(2026, 9, 17)}


def test_prefix_meridiem_keeps_explicit_second_date_visible():
    assert date_headings(["2026.9.17 THU. PM7:30 & 9.18 FRI. PM7:30"]) == (
        {(2026, 9, 17), (2026, 9, 18)}, False
    )
