import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize("heading", [
    "2024.08.30.19:00",
    "2024.8.30. 19:00",
    "2024. 08. 30. 19:00",
])
def test_observed_full_date_with_clock_without_weekday(heading):
    assert date_headings([heading]) == ({(2024, 8, 30)}, False)
    assert _date_matches({"lines": [{"text": heading}]}, "2024-08-30")
    assert not _date_matches({"lines": [{"text": heading}]}, "2025-08-30")


@pytest.mark.parametrize("heading", [
    "08.30.19:00", "2024.08.30", "2024.08.30.19", "2024.08.30.25:00",
    "2024.08.30.19:60", "2024.02.30.19:00", "2024.08.30.19:00 Graduated",
    "2024.08.30.19:00 & 08.31", "2024.08.30.19:00 SAT", "2024.08.30.19:00 PM",
    "2024.08.30.19:000", "2024.08.30.1900", "2024.08.30.9:0",
])
def test_clock_heading_does_not_guess_missing_or_conflicting_parts(heading):
    assert date_headings([heading])[1] is True
    assert not _date_matches({"lines": [{"text": heading}]}, "2024-08-30")


def test_clock_heading_does_not_hide_a_second_date_or_weekday_conflict():
    for other in ("2024.08.31 SAT", "2024.08.31.19:00", "2024.08.30 SAT"):
        reading = {"lines": [{"text": "2024.08.30.19:00"}, {"text": other}]}
        assert not _date_matches(reading, "2024-08-30")


def test_embedded_biography_clock_date_is_not_a_heading():
    assert date_headings(["Debuted on 2024.08.30.19:00"]) == (set(), False)


@pytest.mark.parametrize("following", ["SAT", "(토)", "SAT 19:00"])
def test_full_clock_cannot_hide_a_conflicting_adjacent_weekday(following):
    reading = {"lines": [{"text": "2024.08.30.19:00"}, {"text": following}]}
    assert not _date_matches(reading, "2024-08-30")


@pytest.mark.parametrize("following", ["SAT Lotte Concert Hall", "(토) 예술의전당", "SAT 19:00 Main Hall"])
def test_full_clock_cannot_hide_adjacent_weekday_with_venue(following):
    reading = {"lines": [{"text": "2024.08.30.19:00"}, {"text": following}]}
    assert not _date_matches(reading, "2024-08-30")
