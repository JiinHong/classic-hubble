import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CATALOGUE, CanonicalWork


WORK = CanonicalWork(
    "poulenc-fp151", "poulenc-fp151", ("Thème varié",),
    ("Francis Poulenc", "프랑시스 풀랑크"), "FP 151",
)


@pytest.mark.parametrize("code", ["FP 151", "FP.151", "fp151"])
def test_poulenc_explicit_number_matches_bilingual_programme(code):
    matcher = MusicMatcher([WORK])
    assert matcher.match("피아노를 위한 주제와 변주곡," + code, "프랑시스 풀랑크").work_id == WORK.id
    assert matcher.match("Thème varié", "Francis Poulenc", catalogue=code).work_id == WORK.id


@pytest.mark.parametrize("code", [
    "FP 152", "FP 151a", "FP 151.1", "FP 151/1", "FP 151,1", "FP 151-152", "FP 151; FP 152",
])
def test_poulenc_conflicting_or_component_number_never_uses_alias_fallback(code):
    matcher = MusicMatcher([WORK])
    assert matcher.match("Thème varié " + code, "Poulenc").work_id is None
    assert matcher.match("Thème varié", "Poulenc", catalogue=code).work_id is None


def test_poulenc_number_does_not_override_composer_or_canonical_review():
    from dataclasses import replace

    assert MusicMatcher([WORK]).match("Thème varié FP151", "Maurice Ravel").work_id is None
    held = MusicMatcher([replace(WORK, requires_review=True)]).match("Thème varié FP151", "Poulenc")
    assert held.work_id is None and held.candidate_ids == (WORK.id,)


def test_poulenc_requires_canonical_number_without_expanding_legacy_parser():
    from dataclasses import replace

    assert MusicMatcher([replace(WORK, catalogue=None)]).match("Thème varié", "Poulenc", catalogue="FP151").work_id is None
    assert CATALOGUE.search("FP 151") is None


@pytest.mark.parametrize("scope,expected", [("full_work", 1), ("excerpt", 0), ("arrangement", 0)])
def test_poulenc_publication_revalidates_scope_and_grounded_number(scope, expected):
    from test_music_extraction import quote
    from test_paddle_publication import module, save, setup

    def change(doc):
        doc["lines"][1]["text"] = "Francis Poulenc"
        doc["lines"][2]["text"] = "Thème varié FP151"

    repo, store, data = setup(change)
    repo.load_work_catalog = lambda: [WORK]
    data["items"][0].update(
        composer=quote(1, "Francis Poulenc"), title=quote(2, "Thème varié"),
        catalogue=quote(2, "FP151"), key=None, scope=scope,
    )
    review = save(repo, store, data)
    assert module().publish(repo, store, None, "p1", review)["items"] == expected
    assert not repo.writes
