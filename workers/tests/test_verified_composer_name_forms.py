import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


DVORAK = CanonicalWork(
    "dvorak", "dvorak", ("Symphony No. 9 in E minor",),
    ("Antonin Dvorak", "안토닌 드보르자크"), "Op. 95",
)
GLINKA = CanonicalWork(
    "glinka", "glinka", ("Grand Sextet in E flat major",),
    ("Mikhail Ivanovich Glinka", "미하일 글린카"), None,
)


@pytest.mark.parametrize("composer", ["드보르작", "안토닌 드보르작", "안토닌드보르작"])
def test_verified_korean_dvorak_form_matches_observed_symphony(composer):
    assert MusicMatcher([DVORAK]).match(
        "Symphony No.9 in e minor", composer, catalogue="Op.95",
    ).work_id == "dvorak"


@pytest.mark.parametrize("composer", ["M. Glinka", "M.Glinka", "Mikhail Glinka"])
def test_verified_glinka_short_name_does_not_require_patronymic(composer):
    assert MusicMatcher([GLINKA]).match("Grand Sextet in E flat major", composer).work_id == "glinka"


@pytest.mark.parametrize("composer", ["A. Glinka", "M. Glink", "Mikhail Petrovich Glinka"])
def test_glinka_wrong_initial_spelling_or_patronymic_is_not_repaired(composer):
    assert MusicMatcher([GLINKA]).match("Grand Sextet in E flat major", composer).work_id is None


@pytest.mark.parametrize("composer", ["피터 드보르작", "드보르쟉", "A. Dvork"])
def test_dvorak_wrong_name_or_ocr_spelling_is_not_repaired(composer):
    assert MusicMatcher([DVORAK]).match(
        "Symphony No.9 in e minor", composer, catalogue="Op.95",
    ).work_id is None


def test_name_alias_is_not_a_rule_for_all_middle_personal_names():
    other = CanonicalWork("other", "other", GLINKA.titles, ("Mikhail Petrovich Glinka",), None)
    assert MusicMatcher([other]).match(GLINKA.titles[0], "M. Glinka").work_id is None


def test_verified_names_still_require_work_details_to_agree():
    assert MusicMatcher([DVORAK]).match(
        "Symphony No.8 in e minor", "드보르작", catalogue="Op.95",
    ).work_id is None
    assert MusicMatcher([GLINKA]).match("Grand Sextet in E major", "M. Glinka").work_id is None


def test_conflicting_bilingual_composer_stays_unlinked():
    other = CanonicalWork("brahms", "brahms", ("Symphony No.4",), ("Johannes Brahms",), "Op.98")
    result = MusicMatcher([DVORAK, other]).match(
        "Symphony No.9", "드보르작 Johannes Brahms", catalogue="Op.95",
    )
    assert result.work_id is None and result.reason == "conflicting_composers"


def test_existing_canonical_full_names_still_match():
    assert MusicMatcher([GLINKA]).match(GLINKA.titles[0], GLINKA.composers[0]).work_id == "glinka"
    assert MusicMatcher([DVORAK]).match(DVORAK.titles[0], DVORAK.composers[0], catalogue="Op.95").work_id == "dvorak"
