from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_extraction import validate_response
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.paddle_publication import _bundle_eligible
from classic_hubble_pipeline.work_matching import CanonicalWork
from test_music_extraction import document, quote, response


WORK = CanonicalWork(
    "suppe", "suppe", ("Poet and Peasant Overture",),
    ("Franz von Suppe",), None,
)
PRINTED = "Poet and Peasant Overture for 2 Pianos 8 Hands"


@pytest.mark.parametrize("suffix", ["for 2 Pianos 8 Hands", "for 2 Pianos 4 hands", "for 1 Piano 4 Hands"])
def test_scoped_identity_accepts_explicit_piano_hand_suffix(suffix):
    result = MusicMatcher([WORK]).match(
        f"Poet and Peasant Overture {suffix}", "F. Suppe", scoped=True,
    )
    assert result.work_id == WORK.id
    assert result.reason == "composer_and_alias"


def test_piano_suffix_is_not_stripped_from_full_work_identity():
    assert MusicMatcher([WORK]).match(PRINTED, "F. Suppe").work_id is None


@pytest.mark.parametrize("title,composer", [
    ("Le Carnaval des Animaux", "Camille Saint-Saens"),
    ("Hungarian Rhapsody No. 2 in C-sharp minor", "Franz Liszt"),
])
def test_other_observed_multi_piano_titles_keep_exact_parent_identity(title, composer):
    work = replace(WORK, titles=(title,), composers=(composer,))
    assert MusicMatcher([work]).match(
        title + " for 2 Pianos 4 Hands", composer, scoped=True,
    ).work_id == work.id


@pytest.mark.parametrize("suffix", [
    "for 2 Pianos 8 Hands and another work", "for 2 Pianos 8 Voices",
    "for 2 Pianos", "for Pianos 8 Hands",
])
def test_incomplete_or_different_scoring_suffix_is_not_guessed(suffix):
    assert MusicMatcher([WORK]).match(
        f"Poet and Peasant Overture {suffix}", "F. Suppe", scoped=True,
    ).work_id is None


def test_piano_suffix_preserves_composer_and_ambiguity_guards():
    assert MusicMatcher([WORK]).match(PRINTED, "R. Suppe", scoped=True).work_id is None
    other = replace(WORK, id="other", slug="other")
    result = MusicMatcher([WORK, other]).match(PRINTED, "F. Suppe", scoped=True)
    assert result.work_id is None and result.reason == "ambiguous"


@pytest.mark.parametrize("title,key", [
    ("Hungarian Rhapsody No. 3", None),
    ("Hungarian Rhapsody No. 2", "C major"),
])
def test_piano_suffix_retains_work_number_and_key_conflicts(title, key):
    work = replace(WORK, titles=("Hungarian Rhapsody No. 2 in C-sharp minor",), composers=("Franz Liszt",))
    assert MusicMatcher([work]).match(
        title + " for 2 Pianos 8 Hands", "F. Liszt", key=key, scoped=True,
    ).work_id is None


@pytest.mark.parametrize("scope", ["arrangement", "full_work"])
def test_grounded_piano_arrangement_keeps_original_scope_and_evidence(scope):
    doc = document()
    doc["lines"][1]["text"] = "F. Suppe"
    doc["lines"][2]["text"] = PRINTED
    for line in doc["lines"]:
        line["score"] = .99
    data = response()
    data["items"][0].update(
        scope=scope, composer=quote(1, "F. Suppe"), title=quote(2, PRINTED),
        catalogue=None, key=None,
    )
    item = validate_response(data, doc, "b" * 64, [WORK], automatic=True)["items"][0]
    assert item["suggested_work_id"] is None
    assert item["scope"] == scope
    assert item["fields"]["title"] == PRINTED
    assert item["evidence"]["title"] == quote(2, PRINTED)
    if scope == "arrangement":
        assert item["scoped_work_id"] == WORK.id
        assert _bundle_eligible(item, doc) is None
    else:
        assert item["scoped_work_id"] is None
        assert _bundle_eligible(item, doc) is not None
