import pytest

from classic_hubble_pipeline.performance_dates import date_headings


def test_observed_date_venue_weekday_clock_layout_preserves_source():
    lines = ['2026.09.22.', '흥학관', '아트스페이스', 'Tuesday at 7:30 pm']
    assert date_headings(lines) == ({(2026, 9, 22)}, False)
    assert lines == ['2026.09.22.', '흥학관', '아트스페이스', 'Tuesday at 7:30 pm']


@pytest.mark.parametrize('venue', [['흥학관'], ['아트스페이스'], ['흥학관', '아트스페이스']])
def test_only_bounded_venue_lines_may_separate_full_date_and_weekday(venue):
    assert date_headings(['2026.09.22.', *venue, 'Tuesday at 19:30']) == ({(2026, 9, 22)}, False)


@pytest.mark.parametrize('lines', [
    ['2026.09.22.', '흥학관', 'Monday at 7:30 pm'],
    ['2026.09.22.', '흥학관', 'Tuesday at 7:60 pm'],
    ['2026.09.22.', '흥학관', 'Tuesday at 13:30 pm'],
    ['2026.09.22.', '흥학관', 'Tuesday at 7:3o pm'],
    ['2026.09.22.', '흥학관', 'Tuesday rehearsal'],
    ['2026.09.22.', '흥학관', 'PROGRAM', 'Tuesday at 7:30 pm'],
    ['2026.09.22.', '흥학관', '', 'Tuesday at 7:30 pm'],
    ['2026.09.22.', '흥학관', '아트스페이스', '음악홀', 'Tuesday at 7:30 pm'],
    ['2026.09.22.', '흥학관에서 데뷔', 'Tuesday at 7:30 pm'],
    ['9.22.', '흥학관', 'Tuesday at 7:30 pm'],
    ['2026.02.30.', '흥학관', 'Monday at 7:30 pm'],
])
def test_venue_wrapping_does_not_guess_or_hide_conflicting_evidence(lines):
    assert date_headings(lines)[1] is True


def test_venue_wrapping_preserves_other_dates_and_explicit_year():
    dates, invalid = date_headings(
        ['2026.09.22.', '흥학관', 'Tuesday at 7:30 pm', '2026.9.23 Wed'],
        fallback_year=2025,
    )
    assert (dates, invalid) == ({(2026, 9, 22), (2026, 9, 23)}, False)


@pytest.mark.parametrize('echo', ['2026.9.22.', '2026년 9월 22일'])
def test_bare_date_echo_of_validated_event_is_not_a_new_invalid_heading(echo):
    assert date_headings(['9.22.(화)19:00', '초대의 글', echo], fallback_year=2026) == ({(2026, 9, 22)}, False)


@pytest.mark.parametrize('lines', [
    ['2026.9.22.'],
    ['2026.9.22.', '2026.9.22.'],
    ['2026.9.22.(화)', '2026.9.23.'],
    ['2026.9.22.(월)', '2026.9.22.'],
    ['2026.9.22.(화)', '2026.2.30.'],
    ['2026.9.22.(화)', '2026.9.22. Graduated'],
    ['2026.9.22.(화)', '9.22.'],
])
def test_bare_date_echo_cannot_supply_missing_date_or_hide_conflict(lines):
    assert date_headings(lines)[1] is True


@pytest.mark.parametrize('weekday', ['Wednesday 7PM', 'Tuesday 7:60PM'])
def test_repeated_date_cannot_hide_an_unresolved_nearby_weekday(weekday):
    lines = ['2026.9.22.(화)', '2026.9.22.', 'Unrecognized heading', weekday]
    assert date_headings(lines)[1] is True


def test_bare_echo_supplies_year_to_an_independently_recognized_heading():
    assert date_headings(['9.22.(화)19:00', '초대의 글', '2026.9.22.']) == ({(2026, 9, 22)}, False)


@pytest.mark.parametrize('lines', [
    ['9.22.(월)19:00', '초대의 글', '2026.9.22.'],
    ['9.22.(화)19:00', '2025.9.22.', '2026.9.22.'],
    ['9.22.(화)19:00', '2026.9.23.'],
    ['초대의 글', '2026.9.22.'],
])
def test_echo_year_does_not_hide_weekday_or_date_conflicts(lines):
    assert date_headings(lines)[1] is True
