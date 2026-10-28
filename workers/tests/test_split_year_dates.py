import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


def test_observed_three_line_date_uses_the_printed_year():
    lines = ["2026", "10.15", "(Thu)"]
    assert date_headings(lines) == ({(2026, 10, 15)}, False)
    assert lines == ["2026", "10.15", "(Thu)"]


def test_split_source_year_is_not_replaced_by_target_year():
    lines = ["2020", "10.15", "(Thu)"]
    assert date_headings(lines, fallback_year=2026) == ({(2020, 10, 15)}, False)
    assert not _date_matches({"lines": [{"text": line} for line in lines]}, "2026-10-15")


@pytest.mark.parametrize("lines", [
    ["2026", "10.15", "(Fri)"],
    ["2026", "13.15", "(Thu)"],
    ["2026", "10.15", "Programme", "(Thu)"],
    ["2026", "", "10.15", "(Thu)"],
    ["2026 biography", "10.15", "(Thu)"],
    ["2026", "10.15 biography", "(Thu)"],
    ["2026", "10.15", "(Thu) biography"],
    ["2026", "10.15", "(Thu)25:99"],
    ["2026", "10.15", "(Thu)19:30"],
    ["2026", "10.15"],
    ["10.15", "(Thu)"],
])
def test_split_date_does_not_guess_or_hide_conflicts(lines):
    assert date_headings(lines, fallback_year=2026)[1] is True


def test_another_split_date_remains_visible():
    lines = ["2026.10.15 Thu", "2026", "10.16", "(Fri)"]
    assert date_headings(lines) == ({(2026, 10, 15), (2026, 10, 16)}, False)
    assert not _date_matches({"lines": [{"text": line} for line in lines]}, "2026-10-15")
