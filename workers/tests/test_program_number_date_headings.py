import pytest

from classic_hubble_pipeline.performance_dates import date_headings


def test_observed_dated_program_number_list_is_not_a_second_date():
    lines = ["2026.09.19.SAT.17:00",
             "9월 19일(토) 공연에서는 모차르트 피아노 협주곡 27번, 23번, 21번을 연주합니다."]
    original = list(lines)
    assert date_headings(lines, fallback_year=2026) == ({(2026, 9, 19)}, False)
    assert lines == original


@pytest.mark.parametrize("tail", [
    "협주곡 27번,23번,21번", "교향곡 2번 및 3번", "소나타 1번 & 2번",
    "프로그램 1번~3번", "협주곡 27번, 23 번, 21 번",
])
def test_explicit_korean_number_suffix_is_not_a_date_continuation(tail):
    assert date_headings(["2026.9.19.(토) " + tail]) == ({(2026, 9, 19)}, False)


@pytest.mark.parametrize("tail", [", 9.20.(일)", " & 9.20.(일)", " 및 9.20.(일)"])
def test_program_numbers_cannot_hide_a_later_dated_performance(tail):
    assert date_headings(["2026.9.19.(토) 협주곡 27번, 23번" + tail]) == (
        {(2026, 9, 19), (2026, 9, 20)}, False)


@pytest.mark.parametrize("tail", [", 20", " & 9.20", ", 9.20.(월)", ", 9.31.(월)",
                                  ", 23.5.(월)", ", 23버", ", 23.번"])
def test_malformed_or_conflicting_dates_still_hold(tail):
    assert date_headings(["2026.9.19.(토) 협주곡 27번" + tail])[1] is True


def test_numbered_program_without_date_never_establishes_event_binding():
    assert date_headings(["협주곡 27번, 23번, 21번"]) == (set(), False)


def test_wrong_first_weekday_is_not_hidden_by_program_numbers():
    assert date_headings(["2026.9.19.(일) 협주곡 27번, 23번"])[1] is True
