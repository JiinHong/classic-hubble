from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SPRING = CanonicalWork(
    "spring", "spring", ("Frühlingsstimmen", "봄의 소리"),
    ("Johann Strauss Jr", "요한 슈트라우스 2세"), "Op. 410", ("봄의 소리",),
)
POLKA = CanonicalWork(
    "polka", "polka", ("Tritsch-Tratsch Polka", "트리치 트라치 폴카"),
    SPRING.composers, "Op. 214", (),
)


@pytest.mark.parametrize("title,expected", [
    ("봄의 소리 작품 410", "spring"),
    ("봄의 소리 작품410", "spring"),
    ("봄의소리 작품번호 410", "spring"),
    ("봄의 소리 작품 번호410", "spring"),
    ("트리치 트라치 폴카 작품 214", "polka"),
])
def test_literal_trailing_korean_number_confirms_named_work(title, expected):
    assert MusicMatcher([SPRING, POLKA]).match(title, SPRING.composers[1]).work_id == expected


@pytest.mark.parametrize("title", [
    "봄의 소리 작품 411", "봄의 소리 작품 410/2", "봄의 소리 작품410.2",
    "봄의 소리 작품410-411", "봄의 소리 작품410a", "봄의 소리 작품410 No.2",
    "봄의 소리 작품410번", "봄의 소리 작품410 2", "봄의 소리 작품410 작품411",
    "알 수 없는 곡 작품410", "봄의노래 작품410", "봄의 소리 Op.411 작품410",
])
def test_trailing_number_never_removes_conflicting_identity(title):
    assert not MusicMatcher([SPRING]).match(title, SPRING.composers[1]).candidate_ids


@pytest.mark.parametrize("composer", [None, "Beethoven", "Richard Strauss"])
def test_embedded_number_still_needs_confirmed_composer(composer):
    assert not MusicMatcher([SPRING]).match("봄의 소리 작품410", composer).candidate_ids


def test_untyped_number_does_not_choose_between_same_named_works():
    other = replace(SPRING, id="other", catalogue="Op.411")
    assert not MusicMatcher([SPRING, other]).match("봄의 소리 작품410", SPRING.composers[1]).candidate_ids


@pytest.mark.parametrize("catalogue", [None, "Op.411", "Op.410 No.1"])
def test_embedded_number_needs_complete_owned_canonical_number(catalogue):
    assert not MusicMatcher([replace(SPRING, catalogue=catalogue)]).match(
        "봄의 소리 작품410", SPRING.composers[1],
    ).candidate_ids


def test_review_and_scoped_matching_are_preserved():
    work = replace(SPRING, requires_review=True)
    result = MusicMatcher([work]).match("봄의 소리 작품410", work.composers[1], scoped=True)
    assert result.work_id is None and result.candidate_ids == (work.id,)
    assert result.reason == "catalog_review_required"


def test_embedded_korean_label_does_not_imply_opus():
    mozart = CanonicalWork(
        "k364", "k364", ("Sinfonia concertante in E-flat major",),
        ("Wolfgang Amadeus Mozart", "모차르트"), "K.364", ("신포니아 콘체르탄테",),
    )
    assert MusicMatcher([mozart]).match("신포니아 콘체르탄테 작품364", "모차르트").work_id == mozart.id


def test_separate_catalogue_conflict_is_not_overwritten():
    assert not MusicMatcher([SPRING]).match(
        "봄의 소리 작품410", SPRING.composers[1], catalogue="Op.411",
    ).candidate_ids


def test_explicit_key_conflict_is_preserved():
    work = replace(SPRING, titles=("Frühlingsstimmen in D major", "봄의 소리"))
    assert not MusicMatcher([work]).match(
        "봄의 소리 작품410", work.composers[1], key="C major",
    ).candidate_ids
