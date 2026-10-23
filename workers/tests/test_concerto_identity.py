import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


def cello_concerto(*, titles=("Cello Concerto in A minor",), aliases=()):
    return CanonicalWork("schumann-129", "schumann-129", titles, ("Robert Schumann",), "Op.129", aliases)


@pytest.mark.parametrize("title", [
    "Piano Concerto", "피아노 협주곡", "Concerto for Piano and Orchestra",
    "Violin Concerto", "바이올린 협주곡",
])
def test_catalogue_cannot_override_conflicting_concerto_solo_instrument(title):
    result = MusicMatcher([cello_concerto()]).match(title, "Robert Schumann", catalogue="Op.129", key="A minor")
    assert result.work_id is None


def test_misleading_alias_cannot_override_primary_concerto_instrument():
    work = cello_concerto(aliases=("Piano Concerto",))
    assert MusicMatcher([work]).match("Piano Concerto", "Robert Schumann", catalogue="Op.129").work_id is None


@pytest.mark.parametrize("title", ["Cello Concerto", "Violoncello Concerto", "첼로 협주곡", "Concerto for Cello and Orchestra"])
@pytest.mark.parametrize("primary", ["Cello Concerto in A minor", "첼로 협주곡 A단조", "Concerto for Violoncello and Orchestra in A minor"])
def test_consistent_concerto_instrument_remains_supported(title, primary):
    work = cello_concerto(titles=(primary,))
    assert MusicMatcher([work]).match(title, "Robert Schumann", catalogue="Op.129").work_id == work.id


def test_missing_canonical_instrument_is_not_invented():
    work = cello_concerto(titles=("Concerto in A minor",))
    assert MusicMatcher([work]).match("Cello Concerto", "Robert Schumann", catalogue="Op.129").work_id == work.id


def test_accompaniment_in_sonata_is_not_a_concerto_conflict():
    work = CanonicalWork("sonata", "sonata", ("Cello Sonata",), ("Composer",), "Op.1")
    assert MusicMatcher([work]).match("Sonata for Cello and Piano", "Composer", catalogue="Op.1").work_id == work.id


def test_multiple_solo_instruments_are_preserved():
    work = CanonicalWork("double", "double", ("Concerto for Violin and Cello in A minor",), ("Brahms",), "Op.102")
    assert MusicMatcher([work]).match("Concerto for Violin and Cello", "Brahms", catalogue="Op.102").work_id == work.id
    assert MusicMatcher([work]).match("Concerto for Piano and Cello", "Brahms", catalogue="Op.102").work_id is None


@pytest.mark.parametrize("english,korean", [
    ("Viola", "비올라"), ("Flute", "플루트"), ("Clarinet", "클라리넷"),
    ("Oboe", "오보에"), ("Bassoon", "바순"), ("Horn", "호른"),
    ("Trumpet", "트럼펫"), ("Harp", "하프"),
])
def test_explicit_other_solo_instruments_do_not_turn_into_cello(english, korean):
    for title in (english + " Concerto", korean + " 협주곡"):
        assert MusicMatcher([cello_concerto()]).match(title, "Robert Schumann", catalogue="Op.129").work_id is None
