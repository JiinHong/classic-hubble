import pytest
from classic_hubble_pipeline.music_matching import MusicMatcher
from classic_hubble_pipeline.program_split import split_program_block
from classic_hubble_pipeline.work_matching import CanonicalWork


@pytest.fixture
def matcher():
    return MusicMatcher(
        [
            CanonicalWork(
                "b4",
                "b4",
                ("Symphony No. 4", "교향곡 4번"),
                ("Ludwig van Beethoven", "베토벤"),
                "Op. 60",
            ),
            CanonicalWork(
                "b8",
                "b8",
                ("Symphony No. 8", "교향곡 8번"),
                ("Ludwig van Beethoven", "베토벤"),
                "Op. 93",
            ),
            CanonicalWork("rv", "rv", ("La Valse",), ("Maurice Ravel", "라벨"), None),
            CanonicalWork(
                "fae",
                "fae",
                ("Scherzo in C minor, F-A-E Sonata",),
                ("Johannes Brahms", "브람스"),
                "WoO 2",
            ),
            CanonicalWork(
                "song1",
                "song1",
                ("Mondnacht",),
                ("Robert Schumann", "슈만"),
                "Op. 39 No. 5",
            ),
            CanonicalWork(
                "song2",
                "song2",
                ("Wenn ich in deine Augen seh",),
                ("Robert Schumann", "슈만"),
                "Op. 48 No. 4",
            ),
        ]
    )


def split(text, matcher, composer=None):
    return split_program_block(
        {"display_title": text, "composer_name": composer}, matcher
    )


def test_separate_work_headings_keep_order_and_composer(matcher):
    rows = split(
        "베토벤 / 교향곡 제8번 F장조 Op.93\n베토벤 / 교향곡 제4번 B-flat장조 Op.60",
        matcher,
    )
    assert [r["work_id"] for r in rows] == ["b8", "b4"]
    assert all(r["composer_name"] == "베토벤" for r in rows)


def test_translations_and_movements_stay_with_one_work(matcher):
    text = "베토벤, 교향곡 제8번 Op.93\nL. van Beethoven - Symphony No. 8 Op.93\nⅠ. Allegro\nII. Menuetto"
    rows = split(text, matcher)
    assert len(rows) == 1
    assert rows[0]["work_id"] == "b8"
    assert "Menuetto" in rows[0]["display_title"]


def test_composer_scope_is_carried_to_individual_songs(matcher):
    rows = split(
        "R. Schumann\nMondnacht 달밤\nWenn ich in deine Augen seh 그대의 눈동자를 보면",
        matcher,
    )
    assert [r["work_id"] for r in rows] == ["song1", "song2"]
    assert all(r["composer_name"] == "R. Schumann" for r in rows)


def test_performer_credit_is_not_another_work(matcher):
    rows = split("M. Ravel\nLa Valse\n1st 이정은, 2nd 이진현", matcher)
    assert len(rows) == 1
    assert rows[0]["work_id"] == "rv"
    assert "이정은" in rows[0]["display_title"]


def test_explicit_new_composer_does_not_inherit_previous_identity(matcher):
    rows = split(
        "L. van Beethoven ... Symphony No. 8 Op.93\nM. Ravel ... La Valse", matcher
    )
    assert [r["work_id"] for r in rows] == ["b8", "rv"]


def test_arrangement_scope_is_retained_not_promoted_to_full_work(matcher):
    rows = split("M. Ravel\nLa Valse (arranged for two pianos)", matcher)
    assert len(rows) == 1
    assert rows[0]["work_id"] == "rv"
    assert rows[0]["scope"] == "arrangement"
    assert "arranged" in rows[0]["display_title"]


def test_different_dates_are_not_attached_to_one_performance(matcher):
    rows = split(
        "Beethoven / Symphony No.8 Op.93 (2025.3)\nBeethoven / Symphony No.4 Op.60 (2026.3)",
        matcher,
    )
    assert len(rows) == 1
    assert rows[0]["work_id"] is None
    assert rows[0]["reason"] == "multiple_program_dates"


def test_conflicting_translation_is_not_silently_ignored(matcher):
    rows = split("베토벤 | 교향곡 8번 Op.93\nBeethoven | Symphony No.4 Op.60", matcher)
    assert len(rows) == 1
    assert rows[0]["work_id"] is None
    assert rows[0]["reason"] == "conflicting_translations"


def test_unknown_composer_is_kept_separate_and_not_relabelled(matcher):
    rows = split(
        "Beethoven / Symphony No.8 Op.93\nA. Unknown / Symphony No.4 Op.60", matcher
    )
    assert len(rows) == 2
    assert rows[1]["work_id"] is None
    assert rows[1]["composer_name"] == "A. Unknown"


def test_named_movements_and_notice_do_not_create_spurious_work_matches(matcher):
    rows = split(
        "Beethoven / Symphony No.8 Op.93\nI. A named movement\nII. Another named movement\n- 인터미션 -\nM. Ravel / La Valse",
        matcher,
    )
    assert [r["work_id"] for r in rows] == ["b8", "rv"]


def test_unidentified_fragments_are_preserved_not_dropped(matcher):
    rows = split("Unknown piece\nBeethoven / Symphony No.8 Op.93", matcher)
    assert len(rows) == 2
    assert rows[0]["work_id"] is None
    assert "Unknown piece" in rows[0]["display_title"]


def test_metadata_only_block_is_not_a_missing_work(matcher):
    rows = split("스베틀린 루세브, play-direct\n고잉홈프로젝트, orchestra", matcher)
    assert rows[0]["reason"] == "not_program"
    assert rows[0]["work_id"] is None


def test_roman_movement_is_not_composer_because_of_a_dictionary_prefix(matcher):
    m = MusicMatcher(
        [
            *matcher.works,
            CanonicalWork(
                "song", "song", ("Chansons de Ronsard",), ("Darius Milhaud",), "Op.223"
            ),
        ]
    )
    rows = split("D. Milhaud ... Chansons de Ronsard Op.223\nⅠ. À une Fontaine", m)
    assert len(rows) == 1
    assert rows[0]["composer_name"] == "D. Milhaud"


def test_bilingual_unknown_composer_heading_is_not_a_work(matcher):
    rows = split(
        "피에르 막스 뒤부아 Pierre Max Dubois\nPièces Caractéristiques en Forme de Suite Op.77\nÀ la russe",
        matcher,
    )
    assert len(rows) == 1
    assert rows[0]["composer_name"] == "피에르 막스 뒤부아 Pierre Max Dubois"
    assert not rows[0]["work_id"]


def test_country_labels_do_not_obscure_composer_identity(matcher):
    rows = split("DE 베토벤 – 교향곡 8번 Op.93\nFR 라벨 – La Valse", matcher)
    assert [r["work_id"] for r in rows] == ["b8", "rv"]
    assert rows[0]["display_title"].startswith("DE")


def test_inline_performer_credit_does_not_merge_two_spirituals(matcher):
    rows = split(
        "NEGRO SPIRITUALS SERIES - 흑인영가 듀엣\nDeep River 소프라노 양귀비, 메조소프라노 김미영\nGo, tell it on the mountain",
        matcher,
    )
    assert len(rows) == 2
    assert "Go, tell" not in rows[0]["display_title"]


def test_question_mark_is_not_silently_removed_from_uncertain_title(matcher):
    assert split("M. Ravel / La Valse?", matcher)[0]["work_id"] is None


def test_roman_initial_in_known_composer_is_not_a_movement(matcher):
    xenakis = CanonicalWork("x", "x", ("Dhipli Zyia",), ("Iannis Xenakis",), None)
    m = MusicMatcher([*matcher.works, xenakis])
    rows = split("M. Ravel La Valse\nI. Xenakis Dhipli Zyia", m)
    assert [r["work_id"] for r in rows] == ["rv", "x"]


def test_named_movements_of_a_suite_cannot_match_an_unrelated_piece(matcher):
    m = MusicMatcher(
        [
            *matcher.works,
            CanonicalWork(
                "dolly", "dolly", ("Dolly Suite",), ("Gabriel Faure",), "Op.56"
            ),
            CanonicalWork("other", "other", ("Berceuse",), ("Gabriel Faure",), "Op.16"),
        ]
    )
    rows = split(
        "Gabriel Faure\nDolly Suite Op.56\nBerceuse\nMi-a-ou\nLe jardin de Dolly", m
    )
    assert len(rows) == 1
    assert rows[0]["work_id"] == "dolly"


def test_unrecognized_composer_initial_header_still_scopes_the_songs(matcher):
    rows = split(
        "C. Schumann\nDer mond kommt still gegangen\nDie stille lotosblume", matcher
    )
    assert len(rows) == 2
    assert all(r["composer_name"] == "C. Schumann" and not r["work_id"] for r in rows)


def test_unknown_composer_prefix_cannot_inherit_ravel(matcher):
    rows = split("M. Ravel La Valse\nP. Vasks String Quartet No. 6", matcher)
    assert rows[-1]["composer_name"] == "P. Vasks"
    assert rows[-1]["work_id"] is None


def test_menuet_trio_is_not_an_unknown_composer(matcher):
    rows = split("Beethoven / Symphony No.8 Op.93\nII. Menuet - Trio", matcher)
    assert len(rows) == 1
    assert rows[0]["work_id"] == "b8"


def test_festival_context_does_not_leak_into_previous_work(matcher):
    rows = split(
        "Beethoven / Symphony No.8 Op.93\n영국 BBC 프롬스\nM. Ravel / La Valse", matcher
    )
    assert "프롬스" not in rows[0]["display_title"]
    assert "프롬스" in rows[1]["display_title"]


def test_composer_lifespan_followed_by_title_does_not_swallow_title(matcher):
    rows = split("Blaise Déjardin (b. 1984)Varaitions on A NEW WORLD", matcher)
    assert rows[0]["composer_name"] == "Blaise Déjardin"
    assert "Varaitions" in rows[0]["display_title"]


def test_scoped_parent_line_does_not_create_a_separate_program_item(matcher):
    rows = split(
        "Rondo espressivo\nfrom Sonata in B minor, H. 245\n김진세, guitar",
        matcher,
        "Carl Philipp Emanuel Bach",
    )
    assert len(rows) == 1
    assert "Rondo espressivo" in rows[0]["display_title"]


def test_bilingual_composer_header_can_use_only_the_known_latin_identity(matcher):
    rows = split(
        "루트비히 판 베토벤 Ludwig van Beethoven\nSymphony No.8 Op.93", matcher
    )
    assert len(rows) == 1
    assert rows[0]["work_id"] == "b8"


def test_missing_title_movement_fragment_does_not_claim_a_work(matcher):
    rows = split(
        "Ⅱ. Andante con moto\nⅢ. Lento Assai - Allegro\n1st 문지혜, 2nd 김병희", matcher
    )
    assert len(rows) == 1
    assert rows[0]["reason"] == "orphan_movements"


def test_unknown_bilingual_work_is_one_unlinked_item_not_two(matcher):
    rows = split(
        "칼리보다(1801-1866) 6개의 녹턴, Op.186\nJ. W. Kalliwoda Six Nocturnes for Viola and Piano, Op.186",
        matcher,
    )
    assert len(rows) == 1
    assert rows[0]["work_id"] is None


def test_numbered_titled_movement_cannot_be_two_initial_composer(matcher):
    m = MusicMatcher(
        [
            *matcher.works,
            CanonicalWork("a", "a", ("Unrelated",), ("Isaac Albeniz",), None),
        ]
    )
    rows = split("M. Ravel / La Valse\nⅠ. À une Fontaine", m)
    assert len(rows) == 1
    assert rows[0]["composer_name"] == "M. Ravel"


def test_replaying_unknown_bilingual_composer_context_is_idempotent(matcher):
    text = "장 미셸 드파이ㅣ호른과 피아노를 위한 알파\nJean-Michel Defaye - Alpha for Horn and Piano"
    first = split(text, matcher)
    assert len(first) == 1
    assert split_program_block(first[0], matcher) == first
