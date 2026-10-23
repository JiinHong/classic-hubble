import pytest

from classic_hubble_pipeline.performance_dates import date_headings


@pytest.mark.parametrize("lines,year", [
    (["2024년 2월 6일 금요일 19:30 부산문화회관 중극장"], None),
    (["2026.10.22 FRI 19:30"], None),
    (["10월22일(금) 오후7시30분"], 2026),
    (["2026.10.22 THU", "10.22 FRI"], None),
])
def test_calendar_weekday_conflicts_are_unresolved(lines, year):
    assert date_headings(lines, fallback_year=year)[1] is True


@pytest.mark.parametrize("day,korean,english", [
    (19, "월", "Monday"), (20, "화", "TUE"), (21, "수", "Wednesday"),
    (22, "목", "THUR"), (23, "금", "Friday"), (24, "토", "SAT"), (25, "일", "Sunday"),
])
def test_consistent_calendar_weekdays_remain_supported(day, korean, english):
    for label in (korean, korean + "요일", english):
        assert date_headings([f"2026.10.{day} ({label})"]) == ({(2026, 10, day)}, False)


def test_yearless_weekday_is_not_validated_against_arbitrary_leap_year():
    assert date_headings(["10.22 THU"]) == ({(None, 10, 22)}, False)
    assert date_headings(["10.22 THU"], fallback_year=2026) == ({(2026, 10, 22)}, False)


def test_explicit_source_year_is_not_overridden_by_target_year():
    assert date_headings(["2024.2.6 TUE"], fallback_year=2026) == ({(2024, 2, 6)}, False)


def test_observed_tur_typo_is_not_guessed_to_be_tuesday():
    assert date_headings(["2026.10.22 TUR"]) == ({(2026, 10, 22)}, False)
