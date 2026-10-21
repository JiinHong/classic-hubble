"""Apply sourced work names without changing canonical identities or programs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import dotenv_values

from .catalog_import import digest
from .supabase import SupabaseRepository, SupabaseSettings
from .work_catalog import QID


def validate_manifest(manifest):
    if not manifest.get("version") or not manifest.get("works"):
        raise ValueError("Missing dictionary version or works")
    language = manifest.get("language", "ko")
    if language not in {"ko", "en"}:
        raise ValueError("Invalid naming language")
    if manifest.get("origin", "reviewed-usage") not in {
        "reviewed-usage",
        "wikipedia-names",
        "worklist-names",
        "formal-rendering",
    }:
        raise ValueError("Unknown naming origin")
    sources = manifest["sources"]
    for source in sources.values():
        if not source["url"].startswith("https://") or not source.get("kind"):
            raise ValueError("Invalid source")
    seen = set()
    for entry in manifest["works"]:
        if not QID.fullmatch(entry["qid"]) or entry["qid"] in seen:
            raise ValueError("Invalid or duplicate work identity")
        seen.add(entry["qid"])
        if not all(entry.get(k) for k in ("composer", "expected_title")):
            raise ValueError("Missing identity or display title")
        if "title_ko" not in entry or (language == "ko" and not entry["title_ko"]):
            raise ValueError("Missing display title")
        if "previous_title_ko" not in entry:
            raise ValueError("Missing old-title guard")
        if language == "en" and entry["title_ko"] != entry["previous_title_ko"]:
            raise ValueError("English names cannot change the Korean display title")
        for term in [entry, *entry["aliases"]]:
            if not term.get("sources") or not set(term["sources"]) <= sources.keys():
                raise ValueError("Unknown or missing usage source")
        if any(
            not alias.get("text", "").strip()
            or alias.get("kind") not in {"nickname", "shorthand", "spelling", "title"}
            for alias in entry["aliases"]
        ):
            raise ValueError("Invalid alias")
        if any(a.get("locale", "ko") not in {"ko", "en"} for a in entry["aliases"]):
            raise ValueError("Invalid alias locale")


def build_plan(manifest, works, composers, links, aliases):
    validate_manifest(manifest)
    work_index = {w["id"]: w for w in works}
    composer_index = {c["id"]: c["name"] for c in composers}
    link_index = {}
    for link in links:
        qid = link["provider_id"]
        if qid in link_index:
            raise ValueError("Duplicate source crosswalk")
        link_index[qid] = link["payload"]["work_id"]
    existing = {(a["work_id"], a["alias"]) for a in aliases}
    fingerprint = digest(manifest)
    origin = manifest.get("origin", "reviewed-usage")
    alias_only = manifest.get("language") == "en"
    prefix = {
        "reviewed-usage": "usage",
        "wikipedia-names": "wikipedia",
        "worklist-names": "worklist",
        "formal-rendering": "form",
    }[origin]
    plan = {"titles": [], "aliases": [], "provenance": []}
    seen_work_ids = set()
    for entry in manifest["works"]:
        work = work_index.get(link_index.get(entry["qid"]))
        if (
            not work
            or work["id"] in seen_work_ids
            or composer_index.get(work["composer_id"]) != entry["composer"]
            or work["title"] != entry["expected_title"]
        ):
            raise ValueError(f"Work identity conflict: {entry['qid']}")
        seen_work_ids.add(work["id"])
        if not alias_only and work["title_ko"] not in (
            entry["previous_title_ko"],
            entry["title_ko"],
        ):
            raise ValueError(f"Korean title conflict: {entry['qid']}")
        if not alias_only and work["title_ko"] != entry["title_ko"]:
            plan["titles"].append(
                {
                    "id": work["id"],
                    "composer_id": work["composer_id"],
                    "title": work["title"],
                    "old": work["title_ko"],
                    "new": entry["title_ko"],
                }
            )
        names = [(a["text"], a.get("locale", "ko")) for a in entry["aliases"]]
        if not alias_only:
            names.extend(
                [(entry["title_ko"], "ko"), (entry["previous_title_ko"], "ko")]
            )
        for name, locale in names:
            if not name or (work["id"], name) in existing:
                continue
            plan["aliases"].append(
                {
                    "work_id": work["id"],
                    "alias": name,
                    "locale": locale,
                    "source": f"{locale}-{prefix}:{fingerprint}",
                }
            )
            existing.add((work["id"], name))
        source_ids = set(entry["sources"]).union(
            *(a["sources"] for a in entry["aliases"])
        )
        plan["provenance"].append(
            {
                "provider": "classic_hubble",
                "entity_type": "work_korean_names",
                "provider_id": f"{entry['qid']}:{fingerprint}",
                "payload": {
                    "work_id": work["id"],
                    "dictionary_sha256": fingerprint,
                    "version": manifest["version"],
                    "verification": "formal_rendering_only"
                    if origin == "formal-rendering"
                    else "source_names_only"
                    if manifest.get("language") == "en" or origin == "worklist-names"
                    else "korean_names_only",
                    "origin": origin,
                    "entry": entry,
                    "sources": {s: manifest["sources"][s] for s in sorted(source_ids)},
                },
            }
        )
    return plan


def apply_plan(repository, plan, *, apply=False):
    if not apply:
        return
    # Save evidence and aliases first; a partial run can resume without losing old names.
    for table, rows, conflict in (
        ("provider_records", plan["provenance"], "provider,entity_type,provider_id"),
        ("work_aliases", plan["aliases"], "work_id,alias"),
    ):
        for offset in range(0, len(rows), 100):
            repository._request(
                "POST",
                table,
                params={"on_conflict": conflict},
                json=rows[offset : offset + 100],
                prefer="resolution=ignore-duplicates,return=minimal",
            )
    for change in plan["titles"]:
        response = repository._request(
            "PATCH",
            "works",
            params={
                "id": f"eq.{change['id']}",
                "composer_id": f"eq.{change['composer_id']}",
                "title": f"eq.{change['title']}",
                "title_ko": "is.null"
                if change["old"] is None
                else f"eq.{change['old']}",
            },
            json={"title_ko": change["new"]},
            prefer="return=representation",
        )
        if [row["id"] for row in response.json()] != [change["id"]]:
            raise ValueError(
                f"Possible concurrent edit: {change['id']}; stop and review"
            )


def read_selected(repository, table, column, ids, params):
    rows = []
    for offset in range(0, len(ids), 100):
        rows.extend(
            repository._read_pages(
                table,
                {**params, column: f"in.({','.join(ids[offset : offset + 100])})"},
                page_size=1000,
            )
        )
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(args.dictionary.read_text())
    validate_manifest(manifest)
    settings = SupabaseSettings.from_env({**dotenv_values(args.env_file), **os.environ})
    if settings.url != "https://klnfamtwxwrelrjeguqb.supabase.co":
        raise ValueError("This reviewed dictionary targets Classic Hubble only")
    with SupabaseRepository(settings) as repository:
        qids = [e["qid"] for e in manifest["works"]]
        links = read_selected(
            repository,
            "provider_records",
            "provider_id",
            qids,
            {
                "select": "provider_id,payload",
                "provider": "eq.wikidata",
                "entity_type": "eq.canonical_work",
            },
        )
        ids = [link["payload"]["work_id"] for link in links]
        if not ids:
            raise ValueError("No source crosswalks found")
        works = read_selected(repository, "works", "id", ids, {"select": "*"})
        composers = repository._read_pages(
            "composers", {"select": "id,name"}, page_size=1000
        )
        aliases = read_selected(
            repository, "work_aliases", "work_id", ids, {"select": "*"}
        )
        plan = build_plan(manifest, works, composers, links, aliases)
        report = {
            "target": settings.url,
            "dictionary_sha256": digest(manifest),
            "apply": args.apply,
            "status": "planned",
            "before": {"works": works, "aliases": aliases},
            "counts": {k: len(v) for k, v in plan.items()},
            "plan": plan,
        }
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        apply_plan(repository, plan, apply=args.apply)
        if args.apply:
            report["status"] = "applied"
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(
            json.dumps(
                {
                    "target": settings.url,
                    "status": report["status"],
                    "counts": report["counts"],
                }
            )
        )


if __name__ == "__main__":
    main()
