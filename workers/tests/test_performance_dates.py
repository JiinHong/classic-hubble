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


@pytest.mark.parametrize("suffix", ["TUE 6PM", "TUE", "(Tue) 18:00", "[화] 18:00"])
def test_observed_full_date_and_adjacent_weekday_line(suffix):
    lines = ["KookHWA 26th Concert", "2024. 08. 27.", suffix, "고양 아람누리 음악당"]
    assert date_headings(lines) == ({(2024, 8, 27)}, False)
    assert lines[1] == "2024. 08. 27."


@pytest.mark.parametrize("lines", [
    ["2024. 08. 27.", "FRI 6PM"],
    ["2024. 08. 27.", "", "TUE 6PM"],
    ["2024. 08. 27.", "Programme", "TUE 6PM"],
    ["2024. 08. 27.", "TUE rehearsal biography"],
    ["2024. 08. 27. Graduated", "TUE 6PM"],
    ["08. 27.", "TUE 6PM"],
    ["2024. 02. 30.", "FRI 6PM"],
])
def test_wrapped_heading_does_not_guess_across_conflict_or_unrelated_text(lines):
    assert date_headings(lines)[1] is True


def test_wrapped_heading_does_not_hide_another_date():
    dates, invalid = date_headings(["2024. 08. 27.", "TUE 6PM", "2024. 08. 28 WED"])
    assert dates == {(2024, 8, 27), (2024, 8, 28)}
    assert invalid is False


def test_wrapped_heading_retains_explicit_year_against_target_year():
    assert date_headings(["2024. 08. 27.", "TUE 6PM"], fallback_year=2026) == ({(2024, 8, 27)}, False)


@pytest.mark.parametrize("day,weekday", [(21, "Mon."), (22, "Tue."), (23, "Wed."),
    (24, "Thu."), (25, "Fri."), (26, "Sat."), (27, "Sun.")])
@pytest.mark.parametrize("brackets", [("(", ")"), ("[", "]")])
def test_bracketed_abbreviated_weekday_keeps_printed_period(day, weekday, brackets):
    text = f"2026. 9.{day}. {brackets[0]}{weekday}{brackets[1]}"
    assert date_headings([text, "7:30PM"]) == ({(2026, 9, day)}, False)


@pytest.mark.parametrize("lines", [
    ["2026.9.26.(Fri.)"], ["2026.2.30.(Mon.)"],
    ["2026.9.25.(TH.)"],
    ["2026.9.26.(Satr.)"], ["2026.9.26.(Sat..)"],
    ["2026.9.26.(Sat.) 9.27.(Sun.)"],
    ["2026.9.26.", "", "(Sat.)"],
])
def test_period_does_not_hide_wrong_weekday_or_unresolved_heading(lines):
    assert date_headings(lines)[1] is True


def test_abbreviated_weekday_retains_wrapping_and_multiple_dates():
    assert date_headings(["2026.9.26.", "(Sat.) 7:30PM"]) == ({(2026, 9, 26)}, False)
    assert date_headings(["2026.", "9.26", "(Sat.) 7:30PM"]) == ({(2026, 9, 26)}, False)
    assert date_headings(["2026.9.26.(Sat.) & 9.27.(Sun.)"]) == ({(2026, 9, 26), (2026, 9, 27)}, False)
