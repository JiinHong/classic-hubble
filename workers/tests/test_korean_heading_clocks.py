import pytest

from classic_hubble_pipeline.performance_dates import date_headings


@pytest.mark.parametrize("clock", [
    "토11시.14시", "토 11시, 14시", "(토) 오전 11시 · 오후 2시",
    "토요일 11시 30분 및 14시 30분", "[토] 11시 / 14시",
])
def test_wrapped_korean_clock_list_binds_the_observed_event_date(clock):
    lines = ["2026.9.19", clock, "강남씨어터"]
    original = list(lines)
    assert date_headings(lines) == ({(2026, 9, 19)}, False)
    assert lines == original


@pytest.mark.parametrize("clock", ["토11시.14시", "(토) 11시, 14시", "토요일 오후 2시"])
def test_same_line_korean_clocks_do_not_start_another_date(clock):
    assert date_headings(["2026.9.19 " + clock]) == ({(2026, 9, 19)}, False)


@pytest.mark.parametrize("clock", [
    "토25시, 14시", "토 11시 60분, 14시", "(토) 오후 14시",
    "(일) 11시, 14시", "토11시.14", "토 11시, 9.20.(일)",
])
def test_invalid_clock_or_another_date_cannot_establish_single_event(clock):
    dates, invalid = date_headings(["2026.9.19", clock])
    assert invalid or dates != {(2026, 9, 19)}


def test_korean_clock_without_a_date_does_not_create_one():
    assert date_headings(["토11시.14시"]) == (set(), False)


def test_split_year_and_korean_clock_keeps_all_evidence():
    assert date_headings(["2026", "9.19", "토11시.14시"]) == ({(2026, 9, 19)}, False)


def test_korean_clock_does_not_hide_another_dated_source_line():
    assert date_headings(["2026.9.19", "토11시.14시", "2026.9.20.(일) 14:00"]) == (
        {(2026, 9, 19), (2026, 9, 20)}, False)
