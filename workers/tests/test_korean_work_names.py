import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from classic_hubble_pipeline.korean_work_names import apply_plan, build_plan


def fixture():
    manifest = {
        "version": "2026-10-21",
        "sources": {
            "sac": {"url": "https://www.sac.or.kr/example", "kind": "official"}
        },
        "works": [
            {
                "qid": "Q12008",
                "composer": "Ludwig van Beethoven",
                "expected_title": "Piano Sonata No. 14 in C-sharp minor",
                "previous_title_ko": "피아노 소나타 14번",
                "title_ko": "피아노 소나타 14번 '월광'",
                "sources": ["sac"],
                "aliases": [
                    {"text": "월광 소나타", "kind": "nickname", "sources": ["sac"]}
                ],
            }
        ],
    }
    work = {
        "id": "w",
        "composer_id": "c",
        "slug": "wikidata-q12008",
        "title": manifest["works"][0]["expected_title"],
        "title_ko": "피아노 소나타 14번",
        "catalogue": "Op. 27 No. 2",
    }
    composers = [{"id": "c", "name": "Ludwig van Beethoven"}]
    links = [{"provider_id": "Q12008", "payload": {"work_id": "w"}}]
    return manifest, [work], composers, links, []


def test_plan_only_changes_korean_title_preserves_old_name_and_records_sources():
    args = fixture()
    before = deepcopy(args)
    plan = build_plan(*args)
    assert args == before
    assert plan["titles"] == [
        {
            "id": "w",
            "composer_id": "c",
            "title": args[1][0]["title"],
            "old": "피아노 소나타 14번",
            "new": "피아노 소나타 14번 '월광'",
        }
    ]
    assert {a["alias"] for a in plan["aliases"]} == {
        "월광 소나타",
        "피아노 소나타 14번",
        "피아노 소나타 14번 '월광'",
    }
    assert all(a["source"].startswith("ko-usage:") for a in plan["aliases"])
    assert plan["provenance"][0]["payload"]["verification"] == "korean_names_only"


def test_rerun_does_not_change_titles_or_insert_duplicate_aliases():
    args = fixture()
    plan = build_plan(*args)
    args[1][0]["title_ko"] = plan["titles"][0]["new"]
    again = build_plan(*args[:4], plan["aliases"])
    assert again["titles"] == []
    assert again["aliases"] == []


@pytest.mark.parametrize(
    "failure", ["composer", "title", "old_name", "missing_link", "source", "duplicate"]
)
def test_identity_or_provenance_conflicts_abort_entire_plan(failure):
    args = fixture()
    if failure == "composer":
        args[2][0]["name"] = "Franz Schubert"
    elif failure == "title":
        args[1][0]["title"] = "Another work"
    elif failure == "old_name":
        args[1][0]["title_ko"] = "Someone else's curated name"
    elif failure == "missing_link":
        args[3].clear()
    elif failure == "source":
        args[0]["works"][0]["aliases"][0]["sources"] = ["missing"]
    else:
        args[0]["works"].append(deepcopy(args[0]["works"][0]))
    with pytest.raises(ValueError):
        build_plan(*args)


def test_same_nickname_can_belong_to_multiple_distinct_works():
    args = fixture()
    second = deepcopy(args[0]["works"][0])
    second["qid"] = "Q146113"
    args[0]["works"].append(second)
    args[1].append({**args[1][0], "id": "w2"})
    args[3].append({"provider_id": "Q146113", "payload": {"work_id": "w2"}})
    plan = build_plan(*args)
    assert len([a for a in plan["aliases"] if a["alias"] == "월광 소나타"]) == 2


def test_derived_names_are_not_claimed_as_observed_community_usage():
    args = fixture()
    args[0]["origin"] = "formal-rendering"
    plan = build_plan(*args)
    assert all(a["source"].startswith("ko-form:") for a in plan["aliases"])
    assert plan["provenance"][0]["payload"]["verification"] == "formal_rendering_only"


def test_english_names_do_not_require_or_change_a_korean_display_title():
    args = fixture()
    manifest, works, *_ = args
    manifest["origin"] = "wikipedia-names"
    manifest["language"] = "en"
    entry = manifest["works"][0]
    entry["previous_title_ko"] = entry["title_ko"] = None
    works[0]["title_ko"] = None
    entry["aliases"] = [
        {
            "text": "Moonlight Sonata",
            "locale": "en",
            "kind": "title",
            "sources": entry["sources"],
        }
    ]
    plan = build_plan(*args)
    assert plan["titles"] == []
    assert len(plan["aliases"]) == 1
    assert plan["aliases"][0]["locale"] == "en"
    assert plan["aliases"][0]["source"].startswith("en-wikipedia:")
    assert plan["provenance"][0]["payload"]["verification"] == "source_names_only"


def test_alias_locale_is_validated():
    args = fixture()
    args[0]["works"][0]["aliases"][0]["locale"] = "invalid"
    with pytest.raises(ValueError, match="locale"):
        build_plan(*args)


def test_english_only_manifest_cannot_erase_existing_korean_names():
    args = fixture()
    args[0]["language"] = "en"
    args[0]["works"][0]["title_ko"] = None
    with pytest.raises(ValueError, match="cannot change"):
        build_plan(*args)


def test_english_alias_import_does_not_conflict_with_later_korean_curation():
    args = fixture()
    args[0]["language"] = "en"
    entry = args[0]["works"][0]
    entry["title_ko"] = entry["previous_title_ko"] = None
    entry["aliases"] = [
        {
            "text": "Moonlight Sonata",
            "locale": "en",
            "kind": "title",
            "sources": entry["sources"],
        }
    ]
    plan = build_plan(*args)
    assert not plan["titles"]
    assert [a["alias"] for a in plan["aliases"]] == ["Moonlight Sonata"]


def test_worklist_names_are_identified_as_source_names_not_community_verification():
    args = fixture()
    args[0]["origin"] = "worklist-names"
    plan = build_plan(*args)
    assert plan["aliases"][0]["source"].startswith("ko-worklist:")
    assert plan["provenance"][0]["payload"]["verification"] == "source_names_only"


def test_large_dictionary_reads_use_bounded_identity_batches():
    from classic_hubble_pipeline.korean_work_names import read_selected

    class Reader:
        def _read_pages(self, table, params, *, page_size):
            values = params["id"][4:-1].split(",")
            assert len(values) <= 100
            return [{"id": value} for value in values]

    ids = [f"id-{i}" for i in range(245)]
    assert read_selected(Reader(), "works", "id", ids, {"select": "id"}) == [
        {"id": value} for value in ids
    ]


class Repository:
    def __init__(self, conflict=False):
        self.calls = []
        self.conflict = conflict

    def _request(self, method, table, **kwargs):
        self.calls.append((method, table, kwargs))
        return httpx.Response(200, json=[] if self.conflict else [{"id": "w"}])


def test_apply_is_explicit_and_patch_is_compare_and_set_not_upsert():
    plan = build_plan(*fixture())
    repo = Repository()
    apply_plan(repo, plan)
    assert repo.calls == []
    apply_plan(repo, plan, apply=True)
    patches = [c for c in repo.calls if c[0] == "PATCH"]
    assert len(patches) == 1
    assert patches[0][1] == "works"
    assert patches[0][2]["json"] == {"title_ko": "피아노 소나타 14번 '월광'"}
    assert patches[0][2]["params"]["title_ko"] == "eq.피아노 소나타 14번"
    assert {c[1] for c in repo.calls} <= {"works", "work_aliases", "provider_records"}


def test_concurrent_edit_aborts_without_overwriting_it():
    with pytest.raises(ValueError, match="concurrent"):
        apply_plan(Repository(conflict=True), build_plan(*fixture()), apply=True)


def test_cli_dry_run_requires_paginated_reads_and_never_writes(tmp_path, monkeypatch):
    from classic_hubble_pipeline import korean_work_names as module

    args = fixture()
    manifest = tmp_path / "names.json"
    manifest.write_text(json.dumps(args[0]))

    class ReadOnlyRepository(Repository):
        def __init__(self, settings):
            super().__init__()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            assert self.calls == []

        def _read_pages(self, table, params, *, page_size):
            assert 0 < page_size <= 1000
            return {
                "provider_records": args[3],
                "works": args[1],
                "composers": args[2],
                "work_aliases": args[4],
            }[table]

    monkeypatch.setattr(module, "SupabaseRepository", ReadOnlyRepository)
    monkeypatch.setenv("SUPABASE_URL", "https://klnfamtwxwrelrjeguqb.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-server-key")
    report = tmp_path / "report.json"
    module.main(
        [
            "--dictionary",
            str(manifest),
            "--report",
            str(report),
            "--env-file",
            str(tmp_path / "missing.env"),
        ]
    )
    assert json.loads(report.read_text())["status"] == "planned"


def test_committed_dictionary_has_valid_evidence_and_intentional_ambiguity():
    from classic_hubble_pipeline.korean_work_names import validate_manifest

    path = Path(__file__).parents[1] / "data/korean-work-names.json"
    manifest = json.loads(path.read_text())
    validate_manifest(manifest)
    names = {e["qid"]: {a["text"] for a in e["aliases"]} for e in manifest["works"]}
    assert "비창" in names["Q146113"] & names["Q246589"]
    assert "라흐 피협 3번" in names["Q223337"]
    assert all("라흐2" not in aliases for aliases in names.values())
