"""Batch015 cb2fe6fd prints Honegger's Sonatine with H.42."""
from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SONATINE = CanonicalWork(
    'honegger-sonatine', 'honegger-sonatine',
    ('Sonatine pour clarinette et piano',), ('Arthur Honegger',), 'H. 42',
)


@pytest.mark.parametrize('catalogue', ['H. 42', 'H42', 'h.42'])
def test_verified_honegger_catalogue_identifies_programme_work(catalogue):
    result = MusicMatcher([SONATINE]).match(
        'Sonatine for Clarinet and Piano, H. 42', 'Arthur Honegger',
        catalogue=catalogue,
    )
    assert result.work_id == SONATINE.id
    assert result.reason == 'composer_and_catalogue'


@pytest.mark.parametrize('catalogue', [
    'H.43', 'Op.42', 'HWV42', 'Hob.42', 'H42.2', 'H42/2', 'H42-43',
    'H42a', 'H42 A', 'H4Z',
])
def test_h_catalogue_keeps_wrong_codes_and_unhandled_suffixes_unmatched(catalogue):
    assert MusicMatcher([SONATINE]).match(
        SONATINE.titles[0], 'Arthur Honegger', catalogue=catalogue,
    ).work_id is None


@pytest.mark.parametrize('suffix', ['.2', '/2', '-43'])
def test_h_in_title_does_not_drop_member_or_range(suffix):
    assert MusicMatcher([SONATINE]).match(
        SONATINE.titles[0] + ' H42' + suffix, 'Arthur Honegger',
    ).work_id is None


def test_h_catalogue_keeps_composer_and_duplicate_guards():
    assert MusicMatcher([SONATINE]).match(
        SONATINE.titles[0], 'Paul Hindemith', catalogue='H42',
    ).work_id is None
    assert MusicMatcher([SONATINE, replace(SONATINE, id='duplicate')]).match(
        SONATINE.titles[0], 'Arthur Honegger', catalogue='H42',
    ).reason == 'ambiguous'


def test_unverified_catalogue_row_still_requires_review():
    result = MusicMatcher([replace(SONATINE, requires_review=True)]).match(
        SONATINE.titles[0], 'Arthur Honegger', catalogue='H42',
    )
    assert result.work_id is None
    assert result.candidate_ids == (SONATINE.id,)
    assert result.reason == 'catalog_review_required'
