import pytest
from classic_hubble_pipeline import recording_names


def header(
    locale,
    title,
    composer="Domenico Scarlatti",
    artist="239723",
    work="domenico-scarlatti-1685-pp458",
):
    return f"""<div data-testid="work-header">
      <span data-testid="work-header-first-row"><a href="/{locale}/artist/{artist}">{composer}</a></span>
      <div data-testid="work-header-second-row"><a href="/{locale}/work/{work}">{title}</a></div>
    </div>"""


def test_pairs_work_headers_not_tracks_or_album_positions():
    ko = header("kr", "건반 소나타 사장조, K. 433, Kk 433", "도메니코 스카를라티")
    ko += "<div>Keyboard Sonata in D Minor, K.5</div>"
    en = header("us", "Keyboard Sonata in G Major, K. 433, Kk 433")
    rows = recording_names.pair_album_names(ko, en)
    assert len(rows) == 1
    assert rows[0]["title_ko"] == "건반 소나타 사장조, K. 433, Kk 433"
    assert rows[0]["composer"] == "Domenico Scarlatti"
    assert rows[0]["title_en"] == "Keyboard Sonata in G Major, K. 433, Kk 433"
    assert rows[0]["work_key"] == "domenico-scarlatti-1685-pp458"


@pytest.mark.parametrize(
    "other",
    [
        header("us", "Sonata K. 433", artist="999"),
        header("us", "Sonata K. 433", work="different-work"),
        header("us", "Sonata K. 433") + header("us", "Sonata K. 434"),
    ],
)
def test_does_not_pair_conflicting_or_different_public_identities(other):
    assert recording_names.pair_album_names(header("kr", "소나타 K. 433"), other) == []


def test_unique_catalogue_match_rejects_composer_key_and_scope_errors():
    row = {
        "composer": "Domenico Scarlatti",
        "title_ko": "건반 소나타 사장조, K. 433, Kk 433",
        "title_en": "Keyboard Sonata in G Major, K. 433, Kk 433",
    }
    work = {
        "id": "1",
        "composer": "Domenico Scarlatti",
        "title": "Sonata K. 433 in G major",
        "catalogue": "K. 433",
    }
    assert recording_names.match_recording_name(row, [work]) == "1"
    assert (
        recording_names.match_recording_name(row, [work, {**work, "id": "2"}]) is None
    )
    for override in (
        {"composer": "Wolfgang Amadeus Mozart"},
        {"title": "Sonata K. 433 in C minor"},
        {"catalogue": "K. 433 No. 1"},
        {"title": "Sonata K. 433: I. Allegro"},
    ):
        assert recording_names.match_recording_name(row, [{**work, **override}]) is None
    assert (
        recording_names.match_recording_name(
            {**row, "title_ko": "건반 소나타 다단조, K. 433"}, [work]
        )
        is None
    )


def test_numbered_member_is_not_matched_to_parent_opus():
    row = {
        "composer": "Frédéric Chopin",
        "title_ko": "연습곡 1번, Op. 10/1",
        "title_en": "Etude No. 1, Op. 10/1",
    }
    work = {
        "id": "1",
        "composer": "Frédéric Chopin",
        "title": "Etudes, Op. 10",
        "catalogue": "Op. 10",
    }
    assert recording_names.match_recording_name(row, [work]) is None


def test_whole_suite_does_not_rename_one_dance_using_the_same_catalogue():
    row = {
        "composer": "Johann Sebastian Bach",
        "title_ko": "프랑스 모음곡 2번, BWV 813",
        "title_en": "French Suite No. 2, BWV 813",
    }
    work = {
        "id": "1",
        "composer": "Johann Sebastian Bach",
        "title": "Sarabande, BWV 813",
        "catalogue": "BWV 813",
    }
    assert recording_names.match_recording_name(row, [work]) is None


def test_same_catalogue_with_conflicting_korean_number_is_rejected():
    row = {
        "composer": "Domenico Scarlatti",
        "title_ko": "건반 소나타 사장조, K. 432",
        "title_en": "Keyboard Sonata in G Major, K. 433",
    }
    work = {
        "id": "1",
        "composer": "Domenico Scarlatti",
        "title": "Sonata K. 433 in G major",
        "catalogue": "K. 433",
    }
    assert recording_names.match_recording_name(row, [work]) is None


def test_variant_reference_in_note_cannot_match_the_original_work():
    row = {
        "composer": "Johann Sebastian Bach",
        "title_ko": "전주곡 다장조, BWV 924a · ‘Variant of BWV924’",
        "title_en": "Prelude in C Major, BWV 924a · ‘Variant of BWV924’",
    }
    work = {
        "id": "1",
        "composer": "Johann Sebastian Bach",
        "title": "Prelude in C major, BWV 924",
        "catalogue": "BWV 924",
    }
    assert recording_names.match_recording_name(row, [work]) is None


def test_canonical_member_title_does_not_inherit_collection_name():
    row = {
        "composer": "Franz Schubert",
        "title_ko": "4개의 즉흥곡, D 935",
        "title_en": "4 Impromptus, D 935",
    }
    work = {
        "id": "1",
        "composer": "Franz Schubert",
        "title": "Impromptu D 935 No. 2 in A-flat major",
        "catalogue": "D. 935",
    }
    assert recording_names.match_recording_name(row, [work]) is None


def test_names_exclude_editorial_notes_and_unverified_secondary_catalogues():
    assert (
        recording_names.observed_name("론도 다단조, B. 10, Op. 1 · ‘이별의 왈츠’")
        == "론도 다단조"
    )
    assert (
        recording_names.observed_name(
            "Prelude in C Major, BWV 924a · ‘Variant of BWV924’"
        )
        == "Prelude in C Major"
    )
    assert (
        recording_names.observed_name("아 하나님, 마음의 고통이 많사오니, 1, BWV 3")
        == "아 하나님, 마음의 고통이 많사오니, 1"
    )


def test_korean_and_english_work_forms_must_not_conflict():
    row = {
        "composer": "Frédéric Chopin",
        "title_ko": "왈츠 다단조, Op. 1",
        "title_en": "Rondo in C Minor, Op. 1",
    }
    work = {
        "id": "1",
        "composer": "Frédéric Chopin",
        "title": "Rondo in C minor, op. 1",
        "catalogue": "Op. 1",
    }
    assert recording_names.match_recording_name(row, [work]) is None
