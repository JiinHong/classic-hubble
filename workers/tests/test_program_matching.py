import pytest
from classic_hubble_pipeline.program_matching import match_stored_programs
from classic_hubble_pipeline.work_matching import CanonicalWork


class Repository:
    def __init__(self):
        self.writes = []

    def load_work_catalog(self):
        return [CanonicalWork("w", "rach-2", ("Concerto",), ("Rachmaninoff",), "Op.18")]

    def load_unlinked_program_items(self):
        return [
            {
                "id": "a",
                "display_title": "Concerto Op.18",
                "composer_name": "Rachmaninoff",
                "source_url": "https://tickets.interpark.com/goods/26007299",
            },
            {
                "id": "b",
                "display_title": "Concerto Op.18",
                "composer_name": "Strauss",
                "source_url": None,
            },
        ]

    def link_program_item(self, item, work_id):
        self.writes.append((item["id"], work_id))
        return True


def test_backfill_defaults_to_a_read_only_report():
    repo = Repository()
    result = match_stored_programs(repo)
    assert result["matched"] == 1
    assert result["unresolved"] == 1
    assert result["updated"] == 0
    assert repo.writes == []
    assert result["items"][0]["reason"] == "composer_and_catalogue"


def test_backfill_only_applies_unambiguous_database_ids():
    repo = Repository()
    result = match_stored_programs(repo, apply=True)
    assert result["updated"] == 1
    assert repo.writes == [("a", "w")]


def test_batch_cursor_is_stable_after_successful_rows_disappear():
    repo = Repository()
    first = match_stored_programs(repo, apply=True, batch_size=1)
    assert first["scanned"] == 1
    assert first["next_after_id"] == "a"
    assert first["has_more"] is True
    remaining = [row for row in repo.load_unlinked_program_items() if row["id"] != "a"]
    repo.load_unlinked_program_items = lambda: remaining
    second = match_stored_programs(repo, batch_size=1, after_id="a")
    assert [r["program_item_id"] for r in second["items"]] == ["b"]
    assert second["has_more"] is False


def test_changed_source_is_not_counted_as_an_applied_match():
    repo = Repository()
    repo.link_program_item = lambda item, work_id: False
    result = match_stored_programs(repo, apply=True)
    assert result["matched"] == 1
    assert result["updated"] == 0


def test_notice_followed_by_a_work_is_not_classified_as_only_a_notice():
    repo = Repository()
    repo.load_unlinked_program_items = lambda: [{
        "id": "a", "composer_name": None,
        "display_title": "- 인터미션 -\nRachmaninoff | Concerto Op.18",
    }]
    result = match_stored_programs(repo)
    assert result["items"][0]["reason"] == "complex_program"


@pytest.mark.parametrize("size", [0, -1, 201])
def test_invalid_batch_size_fails_before_reading_or_writing(size):
    with pytest.raises(ValueError, match="batch_size"):
        match_stored_programs(Repository(), batch_size=size)


class StructuredRepository(Repository):
    def load_work_catalog(self):
        return [
            CanonicalWork(
                "sonata",
                "wikidata-sonata",
                ("Violin Sonata No. 6 in A Major",),
                ("Ludwig van Beethoven",),
                "Op. 30",
                ("Op. 30 No. 1",),
                True,
            )
        ]

    def load_unlinked_program_items(self):
        return [
            {
                "id": "a",
                "composer_name": None,
                "source_url": None,
                "display_title": "Ludwig van Beethoven (1770~1827)\nSonata for Piano and Violin No. 6 in A Major, Op. 30, No. 1",
            }
        ]


def test_stored_program_uses_explicit_composer_line_and_catalogue_member():
    repo = StructuredRepository()
    result = match_stored_programs(repo, apply=True)
    assert result["updated"] == 1
    assert repo.writes == [("a", "sonata")]


@pytest.mark.parametrize(
    "text",
    [
        "Ludwig van Beethoven\nViolin Sonata No. 6 Op. 30 No. 1\nAnother piece",
        "Ludwig van Beethoven | Violin Sonata No. 6 Op. 30 No. 1 중 1악장",
        "Ludwig van Beethoven\nViolin Sonata No. 6 Op. 30 No. 2",
    ],
)
def test_complex_or_conflicting_program_blocks_are_not_flattened(text):
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {"id": "a", "composer_name": None, "display_title": text}
    ]
    assert match_stored_programs(repo, apply=True)["updated"] == 0


def test_explicit_composer_prefix_on_single_line_can_match():
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {
            "id": "a",
            "composer_name": None,
            "display_title": "Ludwig van Beethoven, Violin Sonata No. 6 Op. 30 No. 1",
        }
    ]
    assert match_stored_programs(repo, apply=True)["updated"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "베토벤 / 교향곡 제8번 F장조 Op.93,\n베토벤 / 바이올린 소나타 6번 Op.30 No.1",
        "Beethoven\nViolin Sonata No. 6 Op. 30 No. 1 arranged for piano",
        "Beethoven\nViolin Sonata No. 6 Op. 30 No. 1 (arranged by Somebody)",
    ],
)
def test_never_drops_a_work_line_as_if_it_were_only_a_composer(text):
    repo = StructuredRepository()
    repo.load_work_catalog = lambda: [
        CanonicalWork(
            "w", "w", ("Violin Sonata No. 6",), ("Beethoven", "베토벤"), "Op.30 No.1"
        )
    ]
    repo.load_unlinked_program_items = lambda: [
        {"id": "a", "composer_name": None, "display_title": text}
    ]
    assert match_stored_programs(repo, apply=True)["updated"] == 0


def test_bilingual_work_lines_must_both_identify_the_same_work():
    repo = StructuredRepository()
    repo.load_work_catalog = lambda: [
        CanonicalWork(
            "w",
            "w",
            ("Violin Sonata No. 6", "바이올린 소나타 6번"),
            ("Ludwig van Beethoven", "베토벤"),
            "Op.30 No.1",
        )
    ]
    repo.load_unlinked_program_items = lambda: [
        {
            "id": "a",
            "composer_name": None,
            "display_title": "베토벤 | 바이올린 소나타 6번 Op.30 No.1\nLudwig van Beethoven - Violin Sonata No. 6 Op.30 No.1\nI. Allegro",
        }
    ]
    assert match_stored_programs(repo, apply=True)["updated"] == 1


@pytest.mark.parametrize(
    "second",
    [
        "L. van Beethoven - Violin Sonata No. 7 Op.30 No.2",
        "II. Violin Sonata No. 7 Op.30 No.2",
        "C. Debussy - Violin Sonata",
    ],
)
def test_composer_initial_or_numbered_work_is_not_a_movement(second):
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {
            "id": "a",
            "composer_name": "Beethoven",
            "display_title": "Violin Sonata No. 6 Op.30 No.1\n" + second,
        }
    ]
    assert match_stored_programs(repo, apply=True)["updated"] == 0


@pytest.mark.parametrize(
    "text",
    [
        "I N T E R M I S S I O N",
        "- 인터미션 -",
        "※ 본 공연 내용은 주최 측 사정에 의해 변경될 수 있습니다.\nThe program can be subject to change.",
    ],
)
def test_non_music_labels_are_not_reported_as_missing_catalogue(text):
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {"id": "a", "composer_name": None, "display_title": text}
    ]
    result = match_stored_programs(repo)
    assert result["items"][0]["reason"] == "not_program"
    assert result["matched"] == 0


@pytest.mark.parametrize(
    "movement",
    [
        "I. Nicht schnell",
        "II. Einfach, innig",
        "I. Fantasie (Ruhig)",
        "II. Thema mit Variationen",
        "I. Molto moderato",
        "II. Introduzione. Adagio molto",
        "II. Improvisation: Andante cantabile",
        "2. Intermezzo",
        "II. Hastig",
        "IV. Innig",
        "V. Sehr lebhaft",
        "VI. Mit einigem Pomp",
        "VII. Zum Beschluss",
        "2. Tema con variazioni: Andante con moto",
        "3. Scherzo: Allegro - Trio",
    ],
)
def test_conventional_movement_labels_do_not_hide_a_single_work(movement):
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {
            "id": "a",
            "composer_name": "Beethoven",
            "display_title": "Violin Sonata No. 6 Op.30 No.1\n" + movement,
        }
    ]
    assert match_stored_programs(repo)["matched"] == 1


def test_conflicting_inline_and_stored_composers_are_not_overwritten():
    repo = StructuredRepository()
    repo.load_unlinked_program_items = lambda: [
        {
            "id": "a",
            "composer_name": "Mozart",
            "display_title": "Beethoven, Violin Sonata No. 6 Op.30 No.1",
        }
    ]
    result = match_stored_programs(repo, apply=True)
    assert result["updated"] == 0
    assert result["items"][0]["reason"] == "conflicting_composers"
