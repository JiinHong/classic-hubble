import pytest

from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.work_matching import CanonicalWork


@pytest.mark.parametrize("title", ("Part I", "PART II", "Part III", "Part IV", "Part 1"))
def test_numbered_part_heading_is_not_unique_work_identity(title):
    # Source 0c450a0d line 25 is a concert section, not a named composition.
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    result = MusicMatcher([work]).match(title, None)
    assert result.work_id is None
    assert result.reason != "unique_distinctive_title"


@pytest.mark.parametrize("title", ("Part I", "Part II"))
def test_explicit_composer_still_resolves_numbered_component(title):
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert MusicMatcher([work]).match(title, "Example Composer").work_id == "w"


@pytest.mark.parametrize("title", ("Messiah Part I", "Partita", "The Better Part"))
def test_lexically_distinct_titles_remain_identifiable(title):
    work = CanonicalWork("w", "w", (title,), ("Example Composer",), None)
    assert MusicMatcher([work]).match(title, None).work_id == "w"
