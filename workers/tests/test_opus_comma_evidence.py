import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


@pytest.mark.parametrize("printed", ["Op, 18", "Op,18", "op, 18"])
def test_cached_opus_prefix_comma_keeps_the_explicit_number(printed):
    # Cached source 09063694 prints Op, 18 for Rachmaninoff's second concerto.
    work = CanonicalWork("r2", "r2", ("Piano Concerto No.2 in C minor",),
                         ("Sergei Rachmaninoff",), "Op.18")
    result = MusicMatcher([work]).match(
        "Piano concerto No.2 in c minor", "S. Rachmaninoff",
        catalogue=printed, key="c minor",
    )
    assert result.work_id == "r2"
    assert result.reason == "composer_and_catalogue"


def test_cached_opus_comma_in_title_and_catalogue_agree():
    # Source 0c450a0d prints the same punctuation in both grounded fields.
    work = CanonicalWork("c22", "c22", ("Andante spianato et Grande Polonaise brillante",),
                         ("Frederic Chopin",), "Op.22")
    result = MusicMatcher([work]).match(
        "Andante spianato et Grande Polonaise brillante, Op,22", "F.Chopin",
        catalogue="Op,22",
    )
    assert result.work_id == "c22"


@pytest.mark.parametrize("printed", ["Hop,18", "Op,1B", "Op,18-19", "Op,18,19", "Op,18/2", "No,18"])
def test_comma_repair_does_not_drop_uncertain_prefix_digits_or_members(printed):
    work = CanonicalWork("r2", "r2", ("Piano Concerto No.2 in C minor",),
                         ("Sergei Rachmaninoff",), "Op.18")
    result = MusicMatcher([work]).match(
        "Piano Concerto No.2 in C minor", "S. Rachmaninoff", catalogue=printed,
    )
    assert result.work_id is None


@pytest.mark.parametrize("title,composer,catalogue", [
    ("Piano Concerto No.3 in C minor", "S. Rachmaninoff", "Op,18"),
    ("Piano Concerto No.2 in C major", "S. Rachmaninoff", "Op,18"),
    ("Piano Concerto No.2 in C minor", "Frederic Chopin", "Op,18"),
    ("Piano Concerto No.2 in C minor", "S. Rachmaninoff", "Op,19"),
])
def test_comma_repair_preserves_other_identity_constraints(title, composer, catalogue):
    work = CanonicalWork("r2", "r2", ("Piano Concerto No.2 in C minor",),
                         ("Sergei Rachmaninoff",), "Op.18")
    assert MusicMatcher([work]).match(title, composer, catalogue=catalogue).work_id is None
