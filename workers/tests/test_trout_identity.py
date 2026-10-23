"""PF301008: an explicit quintet must not resolve to the namesake song."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SONG = CanonicalWork(
    "song", "wikidata-q630565", ("Die Forelle in D-flat major", "송어"),
    ("Franz Schubert", "프란츠 슈베르트"), "Op. 32",
    ("Die Forelle", "숭어", "D. 550", "Die Forelle Quintet", "피아노 5중주곡 숭어"),
)
QUINTET = CanonicalWork(
    "quintet", "wikidata-q1349941", ("Trout Quintet in A major", "피아노 오중주"),
    SONG.composers, "D. 667",
    ("Piano Quintet", "Trout Quintet", "피아노 5중주 '숭어'", "Piano Quintet 'Trout'"),
)


@pytest.mark.parametrize("title", [
    "피아노 5중주 '숭어'", "피아노 오중주 '숭어'", "피아노 5중주곡 숭어",
    "Die Forelle Quintet", "Piano Quintet 'Die Forelle'",
])
@pytest.mark.parametrize("scoped", [False, True])
def test_quintet_needs_primary_identity_not_a_contaminated_song_alias(title, scoped):
    result = MusicMatcher([SONG]).match(title, "F. Schubert", scoped=scoped)
    assert result.work_id is None
    assert result.candidate_ids == ()


@pytest.mark.parametrize("title", ["피아노 5중주 '숭어'", "Piano Quintet 'Trout'"])
def test_verified_quintet_alias_resolves_even_with_contaminated_song_aliases(title):
    assert MusicMatcher([SONG, QUINTET]).match(title, "F. Schubert").work_id == QUINTET.id


def test_quintet_label_cannot_be_overridden_by_the_song_catalogue():
    result = MusicMatcher([SONG, QUINTET]).match(
        "피아노 5중주 '숭어'", "F. Schubert", catalogue="D. 550",
    )
    assert result.work_id is None
    assert result.candidate_ids == ()


@pytest.mark.parametrize("title,catalogue,expected", [
    ("Die Forelle", "D. 550", "song"),
    ("Trout Quintet", "D. 667", "quintet"),
    ("Piano Quintet", "D. 667", "quintet"),
])
def test_song_and_quintet_keep_their_distinct_catalogue_identities(title, catalogue, expected):
    assert MusicMatcher([SONG, QUINTET]).match(
        title, "F. Schubert", catalogue=catalogue,
    ).work_id == expected


def test_quintet_missing_primary_metadata_is_not_guessed_from_alias():
    incomplete = replace(QUINTET, titles=("Trout",))
    assert MusicMatcher([incomplete]).match("Piano Quintet", "F. Schubert").work_id is None


def test_quintet_is_not_a_distinctive_composerless_title():
    assert MusicMatcher([QUINTET]).match("Piano Quintet", None).work_id is None


def test_quintet_keeps_review_duplicate_and_key_guards():
    assert MusicMatcher([replace(QUINTET, requires_review=True)]).match(
        "Trout Quintet", "F. Schubert",
    ).reason == "catalog_review_required"
    assert MusicMatcher([QUINTET, replace(QUINTET, id="duplicate")]).match(
        "Trout Quintet", "F. Schubert",
    ).reason == "ambiguous"
    assert MusicMatcher([QUINTET]).match(
        "Trout Quintet in D-flat major", "F. Schubert",
    ).work_id is None


@pytest.mark.parametrize("filename,bad_alias", [
    ("english-wikipedia-names.json", "Die Forelle Quintet"),
    ("korean-wikipedia-names.json", "피아노 5중주곡 숭어"),
])
def test_import_manifests_do_not_reintroduce_quintet_aliases_on_song(filename, bad_alias):
    manifest = json.loads((Path(__file__).parents[1] / "data" / filename).read_text())
    song = next(work for work in manifest["works"] if work["qid"] == "Q630565")
    assert bad_alias not in [alias["text"] for alias in song["aliases"]]
