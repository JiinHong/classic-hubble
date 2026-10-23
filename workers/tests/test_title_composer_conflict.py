import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SARASATE = CanonicalWork("sar", "sar", ("Zigeunerweisen",), ("Pablo de Sarasate",), "Op.20")
SCHUMANN = CanonicalWork("sch", "sch", ("Humoreske",), ("Robert Schumann",), "Op.20")


@pytest.mark.parametrize("title", ["Zigeunerweisen", "Zigeunerweisen, Op.20"])
def test_known_primary_title_cannot_be_reassigned_by_opus(title):
    match = MusicMatcher([SARASATE, SCHUMANN]).match(title, "R. Schumann", catalogue="Op.20")
    assert match.work_id is None and match.reason == "title_composer_conflict"


def test_known_primary_title_cannot_override_bilingual_composer_evidence():
    match = MusicMatcher([SARASATE, SCHUMANN]).match("치고이네르바이젠 Zigeunerweisen", "R. Schumann", catalogue="Op.20")
    assert match.work_id is None and match.reason == "title_composer_conflict"


@pytest.mark.parametrize("title,composer,identity", [
    ("Zigeunerweisen", "P. Sarasate", "sar"), ("Humoreske", "R. Schumann", "sch")])
def test_consistent_primary_title_and_composer_are_preserved(title, composer, identity):
    assert MusicMatcher([SARASATE, SCHUMANN]).match(title, composer, catalogue="Op.20").work_id == identity


def test_shared_primary_title_is_not_exclusive_composer_identity():
    other = CanonicalWork("other", "other", ("Zigeunerweisen",), ("Robert Schumann",), "Op.20")
    assert MusicMatcher([SARASATE, other]).match("Zigeunerweisen", "R. Schumann", catalogue="Op.20").work_id == "other"


def test_alias_alone_cannot_veto_another_composers_catalogue():
    alias_only = CanonicalWork("alias", "alias", ("Piano Piece",), ("Other Composer",), "Op.10", ("Humoreske",))
    assert MusicMatcher([SCHUMANN, alias_only]).match("Humoreske", "R. Schumann", catalogue="Op.20").work_id == "sch"


def test_unreviewed_catalogue_entry_cannot_assert_exclusive_title_identity():
    uncertain = CanonicalWork("uncertain", "uncertain", ("Unknown Title",), ("Other Composer",), "Op.9", (), True)
    assert MusicMatcher([SCHUMANN, uncertain]).match("Unknown Title", "R. Schumann", catalogue="Op.20").work_id == "sch"


def test_generic_primary_title_does_not_veto_catalogue_matching():
    generic = CanonicalWork("generic", "generic", ("Romance",), ("Other Composer",), "Op.20")
    unknown = CanonicalWork("target", "target", ("Untranslated",), ("Robert Schumann",), "Op.20")
    assert MusicMatcher([generic, unknown]).match("Romance", "R. Schumann", catalogue="Op.20").work_id == "target"


def test_unknown_title_retains_existing_catalogue_fallback():
    assert MusicMatcher([SARASATE, SCHUMANN]).match("A translated title", "R. Schumann", catalogue="Op.20").work_id == "sch"


@pytest.mark.parametrize("title,catalogue,composer,canonical_title", [
    ("Divertimento", "KV.563", "Wolfgang Amadeus Mozart", "Divertimento in E flat major"),
    ("String Quartet No.7", "Op.59 No.1", "Ludwig van Beethoven", "String Quartet No.7 in F major"),
    ("Ballade", "Op.52", "Frederic Chopin", "Ballade No.4 in F minor"),
    ("Impromptu", "Op.86", "Gabriel Faure", "Impromptu for Harp"),
    ("Requiem", "K.626", "Wolfgang Amadeus Mozart", "Requiem in D minor"),
])
def test_replayed_generic_titles_do_not_assert_foreign_ownership(title, catalogue, composer, canonical_title):
    target = CanonicalWork("target", "target", (canonical_title,), (composer,), catalogue)
    other = CanonicalWork("other", "other", (title,), ("Other Composer",), "Op.999")
    assert MusicMatcher([target, other]).match(title, composer, catalogue=catalogue).work_id == "target"


def test_foreign_alias_catalogue_cannot_assert_primary_identity():
    other = CanonicalWork("other", "other", ("Unknown Title",), ("Other Composer",), "Op.999", ("Unknown Title Op.20",))
    assert MusicMatcher([SCHUMANN, other]).match("Unknown Title", "R. Schumann", catalogue="Op.20").work_id == "sch"
