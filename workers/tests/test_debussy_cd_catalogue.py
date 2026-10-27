from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


ISLE = CanonicalWork(
    "isle", "isle", ("L'isle joyeuse",), ("Claude Debussy",), "L. 106",
    aliases=("L'isle joyeuse, CD 109",),
)
LENTE = CanonicalWork(
    "lente", "lente", ("La plus que lente",), ("Claude Debussy",), None,
    aliases=("La plus que lente, L. 121, CD 128",),
)


@pytest.mark.parametrize("title,catalogue,expected", [
    ("Lisle Joyeuse, L. 106 CD 109 기의 섬", "L. 106 CD 109", "isle"),
    ("La plus que lente, L.121 CD 128 렌토보다 더 천천히", "L.121 CD 128", "lente"),
    ("L'isle joyeuse", "CD109", "isle"),
    ("La plus que lente", "cd. 128", "lente"),
])
def test_actual_poster_cd_scheme_requires_matching_verified_catalogue(title, catalogue, expected):
    # Source 9b2a6c4a; HMM902309 confirms CD 109 and CD 128 as piano works.
    result = MusicMatcher([ISLE, LENTE]).match(title, "C. Debussy", catalogue=catalogue)
    assert result.work_id == expected
    assert result.reason == "composer_and_catalogue"


@pytest.mark.parametrize("catalogue", ["L.106 CD128", "L.121 CD109", "CD110", "CD 109.2", "CD109/2", "CD109-110", "CD109a", "CD 10g"])
def test_cd_scheme_never_drops_wrong_numbers_or_member_suffixes(catalogue):
    assert MusicMatcher([ISLE, LENTE]).match("L'isle joyeuse", "C. Debussy", catalogue=catalogue).work_id is None


def test_cd_in_title_cannot_drop_dot_member():
    assert MusicMatcher([ISLE]).match("L'isle joyeuse CD109.2", "C. Debussy").work_id is None


def test_l_number_does_not_implicitly_establish_cd_equivalence():
    unverified = replace(ISLE, aliases=())
    assert MusicMatcher([unverified]).match("L'isle joyeuse", "C. Debussy", catalogue="L.106 CD109").work_id is None


def test_cd_preserves_composer_and_duplicate_guards():
    matcher = MusicMatcher([ISLE, replace(ISLE, id="other")])
    assert matcher.match("L'isle joyeuse", "C. Debussy", catalogue="CD109").reason == "ambiguous"
    assert MusicMatcher([ISLE]).match("L'isle joyeuse", "Maurice Ravel", catalogue="CD109").work_id is None


def test_existing_l_only_matching_still_works():
    assert MusicMatcher([ISLE]).match("L'isle joyeuse", "C. Debussy", catalogue="L.106").work_id == "isle"
