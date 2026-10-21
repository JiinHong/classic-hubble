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
