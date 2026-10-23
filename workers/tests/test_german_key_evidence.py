import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher, _keys
from classic_hubble_pipeline.music_extraction import validate_response
from classic_hubble_pipeline.work_matching import CanonicalWork


CASES = [
    ("Es-Dur", "E flat major", "eb:major"),
    ("cis-Moll", "C sharp minor", "c#:minor"),
    ("fis-Moll", "F sharp minor", "f#:minor"),
    ("B-Dur", "B flat major", "bb:major"),
    ("g-moll", "G minor", "g:minor"),
    ("F-Dur", "F major", "f:major"),
    ("As-Dur", "A flat major", "ab:major"),
    ("f-moll", "F minor", "f:minor"),
]


@pytest.mark.parametrize("printed,english,normalized", CASES)
def test_observed_german_key_spellings(printed, english, normalized):
    assert _keys(printed) == _keys(english) == {normalized}


@pytest.mark.parametrize("printed,english,normalized", CASES)
def test_german_key_field_preserves_catalogue_identity(printed, english, normalized):
    work = CanonicalWork("w", "w", ("Piano Sonata in " + english,), ("Composer",), "Op.11")
    match = MusicMatcher([work]).match("Klaviersonate", "Composer", catalogue="Op.11", key=printed)
    assert match.work_id == "w"


@pytest.mark.parametrize("printed,english,normalized", CASES)
def test_recognized_german_key_cannot_override_conflicting_mode(printed, english, normalized):
    other = english.replace("major", "minor") if "major" in english else english.replace("minor", "major")
    work = CanonicalWork("w", "w", ("Piano Sonata in " + other,), ("Composer",), "Op.11")
    assert MusicMatcher([work]).match("Klaviersonate", "Composer", catalogue="Op.11", key=printed).work_id is None


@pytest.mark.parametrize("printed", ["fisis-Moll", "cis-Mol", "Es-D", "H-Dur", "B-D", "abcfis-Moll", "asas-Dur", "abg-moll"])
def test_unverified_or_malformed_german_spelling_stays_unresolved(printed):
    work = CanonicalWork("w", "w", ("Piano Sonata in F sharp minor",), ("Composer",), "Op.11")
    result = MusicMatcher([work]).match("Klaviersonate", "Composer", catalogue="Op.11", key=printed)
    assert result.work_id is None and result.reason == "key_requires_review"


def test_conflicting_english_and_german_keys_are_not_silently_collapsed():
    work = CanonicalWork("w", "w", ("Piano Sonata in C sharp minor",), ("Composer",), "Op.11")
    result = MusicMatcher([work]).match("Piano Sonata in C major", "Composer", catalogue="Op.11", key="cis-Moll")
    assert result.work_id is None and result.reason == "conflicting_keys"


def test_canonical_german_key_also_constrains_english_evidence():
    work = CanonicalWork("w", "w", ("Klaviersonate fis-Moll",), ("Composer",), "Op.11")
    matcher = MusicMatcher([work])
    assert matcher.match("Piano Sonata", "Composer", catalogue="Op.11", key="F sharp minor").work_id == "w"
    assert matcher.match("Piano Sonata", "Composer", catalogue="Op.11", key="F minor").work_id is None


def test_german_b_dur_never_means_english_b_natural():
    work = CanonicalWork("w", "w", ("Partita in B major",), ("Bach",), "BWV825")
    result = MusicMatcher([work]).match("Partita", "Bach", catalogue="BWV825", key="B-Dur")
    assert result.work_id is None and result.reason == "no_candidate"
    assert _keys("B-Dur") != _keys("B major")


def test_b_flat_and_b_natural_in_one_reference_remain_conflicting():
    work = CanonicalWork("w", "w", ("Partita in B flat major",), ("Bach",), "BWV825")
    result = MusicMatcher([work]).match("Partita in B major", "Bach", catalogue="BWV825", key="B-Dur")
    assert result.work_id is None and result.reason == "conflicting_keys"


@pytest.mark.parametrize("printed,english,normalized", CASES)
def test_grounded_excerpt_retains_literal_key_and_private_scope(printed, english, normalized):
    work = CanonicalWork("w", "w", ("Piano Sonata in " + english,), ("Composer",), "Op.11")
    document = {"status": "text_extracted", "pipeline_version": "test", "source_sha256": "a" * 64,
                "lines": [{"text": t} for t in ["Composer", "Klaviersonate", "Op.11", printed]]}

    def quote(index):
        return [{"line_id": f"L{index:06}", "quote": document["lines"][index]["text"]}]

    response = {"document_sha256": "b" * 64, "status": "items_extracted", "items": [{
        "context": "program", "scope": "excerpt", "composer": quote(0), "title": quote(1),
        "catalogue": quote(2), "key": quote(3), "movements": []}]}
    result = validate_response(response, document, "b" * 64, [work], automatic=True)
    item = result["items"][0]
    assert item["fields"]["key"] == printed and item["evidence"]["key"] == quote(3)
    assert item["suggested_work_id"] is None and item["scoped_work_id"] == "w"
    assert item["reason"] == "scope_requires_review" and result["publishable"] is False
