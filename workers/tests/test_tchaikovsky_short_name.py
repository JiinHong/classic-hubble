from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SONG = CanonicalWork('song', 'song', ('None but the Lonely Heart',),
                     ('Pyotr Ilyich Tchaikovsky',), 'Op. 6 No. 6')


@pytest.mark.parametrize('name', ['P. Tchaikovsky', 'P.Tchaikovsky', 'Pyotr Tchaikovsky'])
def test_verified_short_name_identifies_same_composer(name):
    result = MusicMatcher([SONG]).match('None, but the lonely heart', name, catalogue='Op. 6 No. 6')
    assert result.work_id == SONG.id


@pytest.mark.parametrize('name', ['B. Tchaikovsky', 'Boris Tchaikovsky', 'P. Tchaikovskyy'])
def test_short_form_does_not_accept_other_composer_or_typo(name):
    assert MusicMatcher([SONG]).match('None but the Lonely Heart', name, catalogue='Op.6').work_id is None


def test_duplicate_song_identities_remain_ambiguous():
    result = MusicMatcher([SONG, replace(SONG, id='other')]).match(
        'None but the Lonely Heart', 'P. Tchaikovsky', catalogue='Op.6 No.6')
    assert result.work_id is None
    assert result.reason == 'ambiguous'


def test_member_catalogue_conflict_is_preserved():
    assert MusicMatcher([SONG]).match('None but the Lonely Heart', 'P. Tchaikovsky',
                                      catalogue='Op.6 No.5').work_id is None


def test_observed_poster_does_not_invent_omitted_song_number():
    matcher = MusicMatcher([SONG])
    assert matcher._composers('P. Tchaikovsky')[0] == {SONG.composers}
    result = matcher.match('None, but the lonely heart', 'P. Tchaikovsky', catalogue='Op.6')
    assert result.work_id is None
    assert result.reason == 'no_candidate'
