"""Batch014 e1cfd6f5 has explicit Op.23 members under a plural genre."""
import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


def matcher():
    return MusicMatcher([
        CanonicalWork('generic', 'generic', ('Preludes',), ('Sergei Rachmaninoff',), None),
        CanonicalWork('collection', 'collection', ('Preludes, Op. 23',), ('Sergei Rachmaninoff',), 'Op. 23'),
        CanonicalWork('d', 'd', ('Prelude in D major',), ('Sergei Rachmaninoff',), 'Op. 23 No. 4'),
        CanonicalWork('bb', 'bb', ('Prelude in B-flat major',), ('Sergei Rachmaninoff',), 'Op. 23 No. 2'),
    ])


@pytest.mark.parametrize('key,number,expected', [('D', 4, 'd'), ('B-flat', 2, 'bb')])
def test_plural_genre_does_not_override_explicit_member(key, number, expected):
    result = matcher().match(f'Preludes in {key} Major, Op. 23 No.{number}',
                             'S.Rachmaninoff', catalogue=f'Op. 23 No.{number}')
    assert result.work_id == expected
    assert result.reason == 'composer_and_catalogue'


@pytest.mark.parametrize('title', [
    'Preludes in D Major, Op. 23 No.2',
    'Preludes in D minor, Op. 23 No.4',
    'Preludes in D Major, Op. 32 No.4',
    'Preludes in D Major, Op. 23 No.3',
])
def test_plural_genre_keeps_member_catalogue_and_key_guards(title):
    assert matcher().match(title, 'S.Rachmaninoff').work_id is None


def test_plural_genre_alone_does_not_identify_composerless_collection():
    assert matcher().match('Preludes', None).work_id is None


def test_parent_collection_number_does_not_identify_single_member():
    assert matcher().match('Preludes, Op. 23', 'S.Rachmaninoff', catalogue='Op. 23').work_id == 'collection'
