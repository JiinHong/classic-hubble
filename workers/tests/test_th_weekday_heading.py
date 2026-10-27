import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize('heading', ['2026.10.22 [TH]', '2026.10.22 (Th)', '2026.10.22 TH 19:30'])
def test_observed_viola_poster_th_abbreviation(heading):
    assert date_headings([heading]) == ({(2026, 10, 22)}, False)
    assert _date_matches({'lines': [{'text': heading}]}, '2026-10-22')


def test_th_calendar_conflict_is_not_ignored():
    assert date_headings(['2026.10.23 [TH]']) == ({(2026, 10, 23)}, True)
    assert not _date_matches({'lines': [{'text': '2026.10.23 [TH]'}]}, '2026-10-23')


def test_yearless_th_uses_target_year_and_rejects_conflict():
    assert date_headings(['10.22 [TH]'], fallback_year=2026) == ({(2026, 10, 22)}, False)
    assert date_headings(['10.22 [TH]'], fallback_year=2025) == ({(2025, 10, 22)}, True)


@pytest.mark.parametrize('heading', ['2026.10.22 [THE]', '2026.10.22 THEATRE', '2026.10.22 [T]'])
def test_th_does_not_accept_word_prefix_or_guess_one_letter(heading):
    assert date_headings([heading])[1] is True


def test_th_does_not_hide_another_programme_date():
    doc = {'lines': [{'text': '2026.10.22 [TH]'}, {'text': '2026.10.23 [FRI]'}]}
    assert not _date_matches(doc, '2026-10-22')
