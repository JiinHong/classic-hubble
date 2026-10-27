import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CATALOGUE, CanonicalWork


WORK = CanonicalWork(
    "boccherini-g98", "boccherini-g98", ("String Trio in D major",),
    ("Luigi Boccherini",), "G. 98",
)


@pytest.mark.parametrize("code", ["G. 98", "G98", "g 98"])
def test_gerard_number_matches_explicit_canonical_identity(code):
    matcher = MusicMatcher([WORK])
    assert matcher.match("String Trio in D Major", "Boccherini", catalogue=code).work_id == WORK.id
    assert matcher.match("String Trio in D Major, " + code, "Boccherini").work_id == WORK.id


@pytest.mark.parametrize("code", [
    "G. 99", "G. 98a", "G. 98.1", "G. 98/1", "G. 98,1", "G. 98-99", "G. 98; G. 99",
])
def test_gerard_conflict_or_component_is_not_ignored(code):
    matcher = MusicMatcher([WORK])
    assert matcher.match(WORK.titles[0], "Boccherini", catalogue=code).work_id is None
    assert matcher.match(WORK.titles[0] + " " + code, "Boccherini").work_id is None


@pytest.mark.parametrize("title,composer", [
    ("String Trio in G major, G. 98", "Boccherini"),
    ("String Quartet in D major, G. 98", "Boccherini"),
    ("String Trio in D major, G. 98", "F. Schubert"),
])
def test_gerard_does_not_override_key_genre_or_composer(title, composer):
    assert MusicMatcher([WORK]).match(title, composer).work_id is None


def test_gerard_requires_canonical_evidence_and_does_not_expand_legacy_parser():
    unnumbered = CanonicalWork("u", "u", WORK.titles, WORK.composers, None)
    assert MusicMatcher([unnumbered]).match(WORK.titles[0], "Boccherini", catalogue="G. 98").work_id is None
    assert CATALOGUE.search("G. 98") is None


@pytest.mark.parametrize("scope,expected_items", [("full_work", 1), ("excerpt", 0), ("arrangement", 0)])
def test_gerard_publication_rechecks_grounded_identity_and_scope(scope, expected_items):
    from test_music_extraction import quote
    from test_paddle_publication import module, save, setup

    def change(doc):
        doc["lines"][1]["text"] = "Boccherini"
        doc["lines"][2]["text"] = "String Trio in D Major, G. 98"

    repo, store, data = setup(change)
    repo.load_work_catalog = lambda: [WORK]
    data["items"][0].update(
        composer=quote(1, "Boccherini"), title=quote(2, "String Trio in D Major"),
        catalogue=quote(2, "G. 98"), key=quote(2, "D Major"), scope=scope,
    )
    review = save(repo, store, data)
    result = module().publish(repo, store, None, "p1", review)
    assert result["items"] == expected_items
    assert not repo.writes
