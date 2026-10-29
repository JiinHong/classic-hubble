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
    ["2026", "10.15"],
    ["10.15", "(Thu)"],
])
def test_split_date_does_not_guess_or_hide_conflicts(lines):
    assert date_headings(lines, fallback_year=2026)[1] is True


def test_another_split_date_remains_visible():
    lines = ["2026.10.15 Thu", "2026", "10.16", "(Fri)"]
    assert date_headings(lines) == ({(2026, 10, 15), (2026, 10, 16)}, False)
    assert not _date_matches({"lines": [{"text": line} for line in lines]}, "2026-10-15")


@pytest.mark.parametrize("year,suffix", [
    ("2026.", "MON 7:30PM"),
    ("2026", "MON 7:30PM"),
    ("2026.", "(Mon)19:30"),
    ("2026.", "[월] 7PM"),
    ("2026", "월요일 19:30"),
    ("2026.", "MON"),
])
def test_observed_split_year_heading_with_clock(year, suffix):
    lines = [year, "9.28", suffix]
    original = list(lines)
    assert date_headings(lines, fallback_year=2026) == ({(2026, 9, 28)}, False)
    assert lines == original
    assert _date_matches({"lines": [{"text": line} for line in lines]}, "2026-09-28")


def test_existing_bare_split_year_accepts_a_valid_clock():
    assert date_headings(["2026", "10.15", "(Thu)19:30"]) == ({(2026, 10, 15)}, False)


@pytest.mark.parametrize("lines", [
    ["2026.", "9.28", "TUE 7:30PM"],
    ["2026.", "9.28", "MON 25:30"],
    ["2026.", "9.28", "MON 7:60PM"],
    ["2026.", "9.28", "MON 13:30PM"],
    ["2026.", "9.28", "MON 0PM"],
    ["2026.", "9.28", "MON 19"],
    ["2026.", "9.28", "MON 7:30PM biography"],
    ["2026.", "9.28", "MON 7:30PM & 9.29 TUE"],
    ["2026. biography", "9.28", "MON 7:30PM"],
    ["2026..", "9.28", "MON 7:30PM"],
    ["2026.", "9.28", "", "MON 7:30PM"],
    ["2026.", "9.28", "Programme", "MON 7:30PM"],
    ["2026.", "2.30", "MON 7:30PM"],
])
def test_split_clock_heading_preserves_conflicts_and_boundaries(lines):
    assert date_headings(lines, fallback_year=2026)[1] is True


def test_split_clock_heading_preserves_printed_year_and_other_dates():
    lines = ["2020.", "9.28", "MON 7:30PM"]
    assert date_headings(lines, fallback_year=2026) == ({(2020, 9, 28)}, False)
    assert not _date_matches({"lines": [{"text": line} for line in lines]}, "2026-09-28")
    lines = ["2026.", "9.28", "MON 7:30PM", "2026.9.29 TUE"]
    assert date_headings(lines) == ({(2026, 9, 28), (2026, 9, 29)}, False)
    assert not _date_matches({"lines": [{"text": line} for line in lines]}, "2026-09-28")
