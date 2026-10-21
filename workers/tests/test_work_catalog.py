from dataclasses import replace

import pytest
from classic_hubble_pipeline import work_catalog as catalog

REGISTRY = {
    "Q255": {"name": "Ludwig van Beethoven", "name_ko": "베토벤", "period": "Classical"}
}


def record(**overrides):
    return {
        "qid": "Q188709",
        "composers": ["Q255"],
        "types": ["Q105543609"],
        "title": "Symphony No. 5",
        "title_ko": "교향곡 5번",
        "aliases": {"en": ["Fate Symphony"], "ko": ["운명"]},
        "opus": [{"value": "67", "ordinal": ""}],
        "catalogues": [],
        "keys": ["C minor"],
        **overrides,
    }


def test_source_work_uses_stable_id_and_real_bilingual_aliases():
    item = catalog.normalize_record(record(), REGISTRY)
    assert item["source_id"] == "Q188709"
    assert item["source_url"] == "https://www.wikidata.org/wiki/Q188709"
    assert item["catalogue"] == "Op. 67"
    assert item["title"] == "Symphony No. 5 in C minor"
    assert item["title_ko"] == "교향곡 5번"
    assert {a["alias"] for a in item["aliases"]} >= {
        "운명",
        "Symphony No. 5",
        "Fate Symphony",
    }
    assert (
        catalog.normalize_record(record(title="Corrected title"), REGISTRY)["id"]
        == item["id"]
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"composers": ["Q255", "Q254"]},
        {"composers": ["Q999"]},
        {"types": ["Q11424"]},
        {"types": ["Q105543609", "Q123"]},
        {"title": ""},
        {"qid": "not-an-id"},
    ],
)
def test_unsupported_source_records_are_not_imported(changes):
    with pytest.raises(ValueError):
        catalog.normalize_record(record(**changes), REGISTRY)


def test_catalogue_scheme_is_required_for_bare_numbers():
    item = catalog.normalize_record(
        record(
            opus=[],
            catalogues=[{"value": "22", "scheme": "Köchel catalogue", "ordinal": ""}],
        ),
        REGISTRY,
    )
    assert item["catalogue"] == "K. 22"
    item = catalog.normalize_record(
        record(
            opus=[], catalogues=[{"value": "22", "scheme": "unknown", "ordinal": ""}]
        ),
        REGISTRY,
    )
    assert item["catalogue"] is None


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("Bach-Werke-Verzeichnis", "BWV 22"),
        ("Deutsch catalogue", "D. 22"),
        ("Händel-Werke-Verzeichnis", "HWV 22"),
        ("Ryom-Verzeichnis", "RV 22"),
        ("Kirkpatrick catalogue", "K. 22"),
    ],
)
def test_known_source_schemes_retain_their_identifiers(scheme, expected):
    item = catalog.normalize_record(
        record(opus=[], catalogues=[{"value": "22", "scheme": scheme, "ordinal": ""}]),
        REGISTRY,
    )
    assert item["catalogue"] == expected


def test_subnumber_is_never_collapsed_to_parent_opus():
    item = catalog.normalize_record(
        record(opus=[{"value": "27", "ordinal": "2"}]), REGISTRY
    )
    assert item["catalogue"] == "Op. 27 No. 2"
    item = catalog.normalize_record(
        record(opus=[{"value": "27/2", "ordinal": ""}]), REGISTRY
    )
    assert item["catalogue"] == "Op. 27 No. 2"
    item = catalog.normalize_record(
        record(opus=[{"value": "27–29", "ordinal": ""}]), REGISTRY
    )
    assert item["catalogue"] is None


def test_existing_curated_ids_titles_and_aliases_are_not_rewritten():
    existing_composers = [
        {
            "id": "composer-old",
            "name": "Ludwig van Beethoven",
            "name_ko": "루트비히 판 베토벤",
        }
    ]
    existing = [
        {
            "id": "work-old",
            "composer_id": "composer-old",
            "slug": "beethoven-symphony-5",
            "catalogue": "Op. 67",
            "title": "Symphony No. 5 in C minor",
            "title_ko": "교향곡 5번",
        }
    ]
    plan = catalog.build_import_plan([record()], REGISTRY, existing_composers, existing)
    assert plan["composers"] == []
    assert plan["works"] == []
    assert plan["links"][0]["work_id"] == "work-old"
    assert all(a["work_id"] == "work-old" for a in plan["aliases"])
    assert all(a["source"].startswith("wikidata:") for a in plan["aliases"])


def test_same_catalogue_in_different_composers_is_not_merged():
    existing = [
        {
            "id": "other",
            "composer_id": "other-composer",
            "catalogue": "Op. 67",
            "title": "Other work",
        }
    ]
    plan = catalog.build_import_plan([record()], REGISTRY, [], existing)
    assert len(plan["works"]) == 1
    assert plan["links"][0]["work_id"] != "other"


def test_ambiguous_same_composer_catalogue_is_not_merged_into_curated_work():
    composers = [{"id": "c", "name": "Ludwig van Beethoven"}]
    existing = [
        {
            "id": "old",
            "composer_id": "c",
            "catalogue": "Op. 67",
            "title": "Symphony No. 5 in C minor",
        }
    ]
    plan = catalog.build_import_plan(
        [record(), record(qid="Q999", title="Another work")],
        REGISTRY,
        composers,
        existing,
    )
    assert plan["works"] == []
    assert len(plan["skipped"]) == 2


def test_rerun_preserves_existing_imported_rows_and_is_insert_free():
    first = catalog.build_import_plan([record()], REGISTRY, [], [])
    second = catalog.build_import_plan(
        [record(title="Upstream title changed")],
        REGISTRY,
        first["composers"],
        first["works"],
    )
    assert second["works"] == []
    assert second["composers"] == []
    assert second["links"][0]["work_id"] == first["works"][0]["id"]


def test_duplicate_qid_is_rejected_before_any_import_plan_is_built():
    with pytest.raises(ValueError, match="Duplicate"):
        catalog.build_import_plan([record(), record()], REGISTRY, [], [])


def test_imported_works_are_candidates_not_auto_links():
    from classic_hubble_pipeline.work_matching import CanonicalWork, match_work

    work = CanonicalWork("new", "new", ("Symphony No. 5",), ("Beethoven",), "Op. 67")
    result = match_work(
        "Symphony No. 5 Op. 67", "Beethoven", [replace(work, requires_review=True)]
    )
    assert result.work_id is None
    assert result.candidate_ids == ("new",)
    assert result.reason == "catalog_review_required"


def test_partial_catalogue_number_cannot_match_a_parent_work():
    from classic_hubble_pipeline.work_matching import CanonicalWork, match_work

    work = CanonicalWork("parent", "parent", ("Sonatas",), ("Beethoven",), "Op. 27")
    assert match_work("Op. 27/2", "Beethoven", [work]).work_id is None


@pytest.mark.parametrize("text", ["Op. 27-29", "Op. 27/2/3", "Op. 27, 28"])
def test_catalogue_ranges_or_deeper_parts_cannot_be_truncated(text):
    from classic_hubble_pipeline.work_matching import CanonicalWork, match_work

    works = [
        CanonicalWork("parent", "parent", ("Sonatas",), ("Beethoven",), "Op. 27"),
        CanonicalWork("child", "child", ("Sonata",), ("Beethoven",), "Op. 27 No. 2"),
    ]
    assert match_work(text, "Beethoven", works).work_id is None


def test_k_and_kv_are_equivalent_but_the_number_must_match():
    from classic_hubble_pipeline.work_matching import CanonicalWork, match_work

    work = CanonicalWork("mozart", "mozart", ("Symphony No. 5",), ("Mozart",), "K. 22")
    assert match_work("KV 22", "Mozart", [work]).work_id == "mozart"
    assert match_work("KV 220", "Mozart", [work]).work_id is None


def test_sparql_rows_preserve_multicomposer_and_raw_catalogue_evidence():
    from classic_hubble_pipeline.catalog_import import parse_bindings

    def row(field, value, **extra):
        return {
            "work": {"value": "http://www.wikidata.org/entity/Q188709"},
            "field": {"value": field},
            "value": {"value": value, **extra},
        }

    rows = [
        row("composers", "http://www.wikidata.org/entity/Q255"),
        row("composers", "http://www.wikidata.org/entity/Q254"),
        row("title", "Symphony No. 5", **{"xml:lang": "en"}),
        row("types", "http://www.wikidata.org/entity/Q105543609"),
        row("opus", "67"),
        row("keys", "C minor"),
    ]
    result = parse_bindings(rows)
    assert result[0]["composers"] == ["Q254", "Q255"]
    assert result[0]["opus"] == [{"value": "67", "ordinal": ""}]


def test_apply_is_explicit_and_writes_only_catalog_and_private_provenance():
    from classic_hubble_pipeline.catalog_import import apply_plan

    calls = []

    class Repository:
        def _request(self, method, table, **kwargs):
            calls.append((method, table, kwargs))

    plan = catalog.build_import_plan([record()], REGISTRY, [], [])
    apply_plan(
        Repository(), plan, {"sha256": "a" * 64, "records": [record()]}, apply=False
    )
    assert calls == []
    apply_plan(
        Repository(), plan, {"sha256": "a" * 64, "records": [record()]}, apply=True
    )
    assert {table for _, table, _ in calls} == {
        "composers",
        "works",
        "work_aliases",
        "provider_records",
    }
    assert all("ignore-duplicates" in kwargs["prefer"] for _, _, kwargs in calls)


def test_snapshot_integrity_error_precedes_any_database_writes():
    from classic_hubble_pipeline.catalog_import import validate_snapshot

    with pytest.raises(ValueError, match="snapshot"):
        validate_snapshot(
            {
                "provider": "wikidata",
                "registry": REGISTRY,
                "records": [record()],
                "sha256": "0" * 64,
            }
        )


def test_snapshot_is_validated_before_storage_and_archive_is_read_back():
    from classic_hubble_pipeline.catalog_import import (
        ENDPOINT,
        LICENSE,
        archive_snapshot,
        digest,
    )

    class Store:
        bucket = "private-sources"
        saved = None

        def archive_catalog_snapshot(self, value):
            from types import SimpleNamespace

            self.saved = value
            return SimpleNamespace(key="catalogs/test", sha256="b" * 64)

        def read(self, key):
            import json

            assert key == "catalogs/test"
            return json.dumps(self.saved).encode()

    store = Store()
    with pytest.raises(ValueError, match="snapshot"):
        archive_snapshot(store, {"sha256": "invalid"})
    assert store.saved is None
    snapshot = {
        "provider": "wikidata",
        "endpoint": ENDPOINT,
        "license": LICENSE,
        "records": [record()],
        "registry": REGISTRY,
    }
    snapshot["sha256"] = digest(snapshot)
    result = archive_snapshot(store, snapshot)
    assert result == {
        "bucket": "private-sources",
        "key": "catalogs/test",
        "object_sha256": "b" * 64,
    }
