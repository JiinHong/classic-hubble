import pytest

from classic_hubble_pipeline.performance_dates import date_headings


def test_observed_quartet_compact_weekday_hour_preserves_ocr():
    lines = ['9.20. SUN4PM', '2026.', '음악의집']
    assert date_headings(lines, fallback_year=2026) == ({(2026, 9, 20)}, False)
    assert lines == ['9.20. SUN4PM', '2026.', '음악의집']


@pytest.mark.parametrize('clock', ['4PM', '4pm', '12AM', '12 PM', '4:00PM'])
def test_compact_hour_requires_a_literal_meridiem(clock):
    assert date_headings(['2026.9.20.SUN' + clock]) == ({(2026, 9, 20)}, False)


@pytest.mark.parametrize('tail', [
    '0PM', '13PM', '24AM', '123PM', '4', '4P', '4P M', '4PMx', '4PM30',
    '4:60PM', '4:00:99PM', '4:0PM', '4:00P',
])
def test_malformed_compact_clock_cannot_establish_a_date(tail):
    assert date_headings(['2026.9.20.SUN' + tail])[1] is True


def test_compact_clock_preserves_weekday_conflict_and_second_event():
    assert date_headings(['2026.9.20.MON4PM'])[1] is True
    assert date_headings(['2026.9.20.SUN4PM & 9.21.MON7PM']) == (
        {(2026, 9, 20), (2026, 9, 21)}, False)


def test_compact_clock_preserves_wrapping_and_explicit_year():
    assert date_headings(['2026.9.20.', 'SUN4PM'], fallback_year=2025) == (
        {(2026, 9, 20)}, False)
    assert date_headings(['2026.9.20.SUN4PM', '2026.9.21.MON7PM']) == (
        {(2026, 9, 20), (2026, 9, 21)}, False)
