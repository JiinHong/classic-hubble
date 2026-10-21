"""Build a reproducible, read-only component inventory from source snapshots."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .catalog_import import digest
from .component_audit import resolve_album_parent, wikidata_components
from .work_catalog import identity
from .work_components import (
    build_component_plan,
    numbered_title,
    pair_album_parts,
    parse_album_parts,
)


def name_key(title):
    parsed = numbered_title(title)
    return identity(parsed[1] if parsed else title)


def collect_albums(directories):
    rows, outcomes = [], []
    seen = set()
    for directory in directories:
        for en in sorted(directory.glob("us-*.html")):
            album_id = en.stem[3:]
            if album_id in seen:
                continue
            seen.add(album_id)
            ko = directory / f"kr-{album_id}.html"
            if not ko.exists():
                outcomes.append({"album_id": album_id, "status": "missing_locale"})
                continue
            try:
                sources = []
                for file in (ko, en):
                    source = json.loads(file.with_suffix(".json").read_text())
                    if (
                        hashlib.sha256(file.read_bytes()).hexdigest()
                        != source["sha256"]
                    ):
                        raise ValueError("Source integrity mismatch")
                    sources.append(source)
                parts = pair_album_parts(
                    parse_album_parts(ko.read_text(), "kr", album_id),
                    parse_album_parts(en.read_text(), "us", album_id),
                )
                rows.extend({**row, "sources": sources} for row in parts)
                outcomes.append(
                    {
                        "album_id": album_id,
                        "status": "checked",
                        "numbered_parts": len(parts),
                    }
                )
            except (ValueError, KeyError, OSError) as error:
                outcomes.append(
                    {
                        "album_id": album_id,
                        "status": "source_unavailable",
                        "reason": type(error).__name__,
                    }
                )
    return rows, outcomes


def inventory(catalog, entities, album_rows, manual):
    rows, held = wikidata_components(catalog, entities)
    wi = {w["id"]: w for w in catalog["works"]}
    composers = {c["id"]: c["name"] for c in catalog["composers"]}
    parent = next(w for w in catalog["works"] if w["slug"] == manual["parent_slug"])
    if (
        parent["title"] != manual["expected_parent_title"]
        or composers[parent["composer_id"]] != manual["expected_composer"]
    ):
        raise ValueError("Reviewed source parent changed")
    for part in manual["parts"]:
        rows.append(
            {
                **part,
                "parent_id": parent["id"],
                "expected_parent_title": parent["title"],
                "composer_id": parent["composer_id"],
                "sources": [manual["source"]],
            }
        )
    parents = {}
    conflicting_album_positions = set()
    existing_names = defaultdict(set)
    for work in catalog["works"]:
        existing_names[(work["composer_id"], name_key(work["title"]))].add(work["id"])
    for alias in catalog["work_aliases"]:
        work = wi[alias["work_id"]]
        existing_names[(work["composer_id"], name_key(alias["alias"]))].add(work["id"])
    for item in album_rows:
        key = (
            item["parent_key"],
            item["parent_title_en"],
            item["parent_title_ko"],
            item["composer"],
        )
        if key not in parents:
            parents[key] = resolve_album_parent(item, catalog)
        parent_id = parents[key]
        if not parent_id:
            held.append({"album_part": item, "reason": "unresolved_album_parent"})
            continue
        parent = wi[parent_id]
        siblings = [r for r in rows if r["parent_id"] == parent_id]
        matches = [
            r
            for r in siblings
            if name_key(r["title"]) == name_key(item["title_en"])
            and r.get("position") in (None, item["position"])
        ]
        if len(matches) == 1:
            row = matches[0]
            row["position"] = item["position"]
            row.setdefault("aliases", []).extend(
                {"alias": title, "locale": lang}
                for title, lang in ((item["title_en"], "en"), (item["title_ko"], "ko"))
                if title
            )
            row["sources"].extend(s for s in item["sources"] if s not in row["sources"])
            # A verified public program takes precedence over recording metadata.
            if not row.get("title_ko"):
                row["title_ko"] = item["title_ko"]
            continue
        if matches or any(r.get("position") == item["position"] for r in siblings):
            if any(
                r.get("discovery") == "album" and r.get("position") == item["position"]
                for r in siblings
            ):
                conflicting_album_positions.add((parent_id, item["position"]))
            held.append(
                {"album_part": item, "reason": "component_name_or_number_conflict"}
            )
            continue
        if existing_names[(parent["composer_id"], name_key(item["title_en"]))]:
            held.append(
                {
                    "album_part": item,
                    "reason": "potential_existing_component_needs_identity_review",
                }
            )
            continue
        rows.append(
            {
                "parent_id": parent_id,
                "expected_parent_title": parent["title"],
                "composer_id": parent["composer_id"],
                "position": item["position"],
                "title": item["title_en"],
                "title_ko": item["title_ko"],
                "sources": list(item["sources"]),
                "discovery": "album",
            }
        )
    excluded = [
        row
        for row in rows
        if row.get("discovery") == "album"
        and (row["parent_id"], row["position"]) in conflicting_album_positions
    ]
    held.extend(
        {"observation": row, "reason": "conflicting_album_component_names"}
        for row in excluded
    )
    rows = [row for row in rows if row not in excluded]
    accepted = []
    for row in rows:
        if row.get("discovery") == "album":
            albums = {
                m[1]
                for source in row["sources"]
                if (
                    m := re.fullmatch(
                        r"https://classical\.music\.apple\.com/(?:us|kr)/album/(\d+)",
                        source["url"],
                    )
                )
            }
            if len(albums) < 2:
                held.append(
                    {
                        "observation": row,
                        "reason": "single_recording_relationship_needs_corroboration",
                    }
                )
                continue
            # A numbered recording of a single waltz/etude is not a movement of it.
            if re.search(
                r"\b(?:waltz|mazurka|polonaise|nocturne|etude|prelude)\s+(?:No\.?\s*\d|in\s)",
                row["expected_parent_title"],
                re.IGNORECASE,
            ):
                held.append(
                    {"observation": row, "reason": "single_piece_parent_needs_review"}
                )
                continue
        accepted.append(row)
    rows = accepted
    plan = build_component_plan(rows, catalog["works"], catalog["work_aliases"], [])
    held.extend(plan["held"])
    relations = plan["relations"]
    touched = {r[k] for r in relations for k in ("parent_id", "child_id")}
    decisions = [
        {
            "work_id": w["id"],
            "slug": w["slug"],
            "status": "relationship_found"
            if w["id"] in touched
            else "no_verified_relationship",
        }
        for w in catalog["works"]
    ]
    audit = {
        "version": "2026-10-21-components-v1",
        "scope": "All existing catalog works, explicit Wikidata P527/P361 relationships, cached public bilingual album pages, and the cited reviewed recital program. No evidence does not mean no components exist.",
        "target_sha256": digest(sorted(w["id"] for w in catalog["works"])),
        "summary": {
            "existing_works_checked": len(decisions),
            "new_works": len(plan["works"]),
            "relations": len(relations),
            "aliases": len(plan["aliases"]),
            "held_observations": len(held),
            "outcomes": dict(Counter(d["status"] for d in decisions)),
            "hold_reasons": dict(Counter(h["reason"] for h in held)),
        },
        "works": decisions,
        "relations": relations,
        "evidence": plan["provenance"],
        "held": held,
    }
    audit["sha256"] = digest(audit)
    return {"observations": rows, "plan": plan, "audit": audit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--albums", type=Path, nargs="+", required=True)
    parser.add_argument("--manual", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    entities = json.loads(args.entities.read_text())
    rows, albums = collect_albums(args.albums)
    result = inventory(catalog, entities, rows, json.loads(args.manual.read_text()))
    result["albums"] = albums
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {
                **result["audit"]["summary"],
                "albums_checked": len(albums),
                "album_parts": len(rows),
            }
        )
    )


if __name__ == "__main__":
    main()
