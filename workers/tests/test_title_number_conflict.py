import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


SCHUBERT = CanonicalWork(
    "d959", "d959", ("Sonata in A major, D. 959", "피아노 소나타 20번 가장조"),
    ("Franz Schubert", "슈베르트"), "D. 959",
)
BEETHOVEN = CanonicalWork(
    "op37", "op37", ("Piano Concerto No. 3 in C minor",),
    ("Ludwig van Beethoven", "베토벤"), "Op. 37",
)


@pytest.mark.parametrize("title", [
    "Piano Sonata in A Major No.22", "Piano Sonata No. 22 in A major, D.959",
])
def test_observed_schubert_number_conflict_has_a_specific_reason(title):
    result = MusicMatcher([SCHUBERT]).match(title, "FRANZ SCHUBERT", catalogue="D.959")
    assert result.work_id is None and not result.candidate_ids
    assert result.reason == "title_number_conflict"


def test_observed_bilingual_concerto_number_conflict_is_not_a_missing_work():
    result = MusicMatcher([BEETHOVEN]).match(
        "피아노협주곡제2번c단조 Piano Concerto No.3 in c minor",
        "베토벤 L.v. Beethoven", catalogue="Op. 37",
    )
    assert result.work_id is None and result.reason == "title_number_conflict"


@pytest.mark.parametrize("catalogue", [None, "D. 999"])
def test_missing_catalogue_identity_is_not_a_number_conflict(catalogue):
    result = MusicMatcher([SCHUBERT]).match("Piano Sonata No.22", "Franz Schubert", catalogue=catalogue)
    assert result.work_id is None and result.reason == "no_candidate"


def test_wrong_composer_does_not_get_a_foreign_number_diagnostic():
    result = MusicMatcher([SCHUBERT, BEETHOVEN]).match(
        "Piano Sonata No.22", "L. v. Beethoven", catalogue="D.959",
    )
    assert result.work_id is None and result.reason == "no_candidate"


def test_correct_catalogue_and_number_still_match():
    result = MusicMatcher([SCHUBERT]).match("Piano Sonata No.20", "Franz Schubert", catalogue="D.959")
    assert result.work_id == "d959" and result.reason == "composer_and_catalogue"


def test_title_without_number_still_matches_catalogue():
    assert MusicMatcher([SCHUBERT]).match("Sonata in A major", "Franz Schubert", catalogue="D.959").work_id == "d959"


def test_supported_same_catalogue_identity_is_not_overridden_by_other_number():
    alternative = CanonicalWork("other", "other", ("Piano Sonata No.22",), ("Franz Schubert", "슈베르트"), "D.959")
    assert MusicMatcher([SCHUBERT, alternative]).match("Piano Sonata No.22", "Franz Schubert", catalogue="D.959").work_id == "other"


def test_unknown_number_in_canonical_titles_does_not_claim_a_conflict():
    unnumbered = CanonicalWork("sonata", "sonata", ("Sonata in A major",), ("Franz Schubert",), "D.959")
    assert MusicMatcher([unnumbered]).match("Sonata No.22 in A major", "Franz Schubert", catalogue="D.959").work_id == "sonata"
