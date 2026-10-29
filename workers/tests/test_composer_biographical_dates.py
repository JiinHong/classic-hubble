from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher, _variants
from classic_hubble_pipeline.work_matching import CanonicalWork

BRAHMS = CanonicalWork('brahms-100', 'brahms-100', ('Violin Sonata No. 2',),
                       ('Johannes Brahms',), 'Op. 100', ())
TCHAIKOVSKY = CanonicalWork('tchaikovsky-59', 'tchaikovsky-59', ('Dumka',),
                          ('Pyotr Ilyich Tchaikovsky',), 'Op. 59', ())


@pytest.mark.parametrize('work,name,title', [
    (BRAHMS, 'Johannes Brahms (1833-l897)', 'Violin Sonata No. 2, Op.100'),
    (BRAHMS, 'Johannes Brahms (1833-I897)', 'Violin Sonata No. 2, Op.100'),
    (TCHAIKOVSKY, 'P. Tchaikovsky (184o-1893)', 'Dumka, Op.59'),
    (TCHAIKOVSKY, 'P. Tchaikovsky (184O-1893)', 'Dumka, Op.59'),
])
def test_ocr_year_glyphs_do_not_become_part_of_composer_identity(work, name, title):
    result = MusicMatcher([work]).match(title, name)
    assert result.work_id == work.id
    assert name.endswith(')')


@pytest.mark.parametrize('suffix', ['(b. 1972)', '(b.1972)', '(b. 197o)'])
def test_explicit_birth_annotation_is_not_part_of_name(suffix):
    work = replace(BRAHMS, composers=('Julian Gargiulo',), catalogue=None)
    assert MusicMatcher([work])._composers('Julian Gargiulo ' + suffix)[0] == {work.composers}


@pytest.mark.parametrize('annotation', [
    '(arr. 1972)', '(b. 197)', '(b. 1972 revised)', '(1833-l89x)',
    '(1833-1897 / Robert Schumann)', '(b. 1972 / John Williams)',
])
def test_unrecognized_parentheses_are_not_erased(annotation):
    observed = 'Johannes Brahms ' + annotation
    assert MusicMatcher([BRAHMS])._composers(observed)[0] == set()


def test_birth_annotation_does_not_resolve_ambiguous_surname():
    other = replace(BRAHMS, id='other', composers=('Other Brahms',))
    identities, _ = MusicMatcher([BRAHMS, other])._composers('Brahms (b. 1972)')
    assert identities == {BRAHMS.composers, other.composers}


def test_generation_and_wrong_initial_are_preserved():
    father = replace(BRAHMS, id='strauss-i', composers=('Johann Strauss I',))
    son = replace(BRAHMS, id='strauss-ii', composers=('Johann Strauss II',))
    matcher = MusicMatcher([father, son, BRAHMS])
    assert matcher._composers('Johann Strauss II (1825-l899)')[0] == {son.composers}
    assert not matcher._composers('R. Brahms (1833-l897)')[0]


def test_birth_metadata_cleanup_does_not_modify_work_titles():
    assert _variants('Dumka (b. 1972)') == ('Dumka (b. 1972',)
    assert _variants('Dumka (184o-1893)') == ('Dumka (184o-1893',)


def test_new_composer_metadata_rule_keeps_catalogue_conflicts_blocked():
    assert MusicMatcher([BRAHMS]).match('Violin Sonata No. 2, Op.101',
                                      'Johannes Brahms (1833-l897)').work_id is None
