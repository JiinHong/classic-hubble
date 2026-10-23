import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


@pytest.mark.parametrize("title", ["Three Romances for Violin and Piano", "Romance", "Romances"])
def test_romance_cannot_match_same_composers_sonata_number(title):
    work = CanonicalWork("sonata", "sonata", ("Piano Sonata No. 2 in G minor",), ("Robert Schumann",), "Op.22")
    assert MusicMatcher([work]).match(title, "R.Schumann", catalogue="Op.22").work_id is None


def test_romance_title_and_catalogue_still_identify_verified_work():
    work = CanonicalWork("romance", "romance", ("Three Romances for Violin and Piano",), ("Clara Schumann",), "Op.22")
    assert MusicMatcher([work]).match("Three Romances for Violin and Piano", "C.Schumann", catalogue="Op.22").work_id == work.id


def test_existing_other_composer_sonata_remains_distinct():
    works = [
        CanonicalWork("clara", "clara", ("Three Romances for Violin and Piano",), ("Clara Schumann",), "Op.22"),
        CanonicalWork("robert", "robert", ("Piano Sonata No. 2 in G minor",), ("Robert Schumann",), "Op.22"),
    ]
    m = MusicMatcher(works)
    assert m.match("Piano Sonata No.2", "R.Schumann", catalogue="Op.22").work_id == "robert"
    assert m.match("Three Romances for Violin and Piano", "R.Schumann", catalogue="Op.22").work_id is None


def test_romance_with_unknown_canonical_genre_is_not_invented():
    work = CanonicalWork("w", "w", ("Three Pieces",), ("Composer",), "Op.1")
    assert MusicMatcher([work]).match("Romance", "Composer", catalogue="Op.1").work_id == "w"
