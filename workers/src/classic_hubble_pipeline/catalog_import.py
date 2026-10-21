"""Fetch a resumable Wikidata snapshot; explicitly apply additive catalog inserts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

from .r2 import R2Settings, R2Store
from .supabase import SupabaseRepository, SupabaseSettings
from .work_catalog import QID, WORK_CONCEPT, build_import_plan

ENDPOINT = "https://query.wikidata.org/sparql"
LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def load_registry(root: Path):
    data = root / "apps/web/src/data"
    provenance = json.loads((data / "composer-korean-name-provenance.json").read_text())
    baseline = json.loads((data / "openopus-composers.json").read_text())
    registry = {}
    for composer in baseline:
        record = provenance[composer["name"]]
        ids = {
            s["url"].rsplit("/", 1)[-1]
            for s in record["sources"]
            if s["publisher"] == "Wikidata"
        }
        if len(ids) != 1 or not QID.fullmatch(next(iter(ids))):
            raise ValueError("Unresolved composer identity")
        qid = next(iter(ids))
        if qid in registry:
            raise ValueError("Duplicate composer identity")
        registry[qid] = {
            "name": composer["name"],
            "name_ko": record["displayName"],
            "period": composer["period"],
        }
    return registry


def make_query(qids):
    if not qids or not all(QID.fullmatch(qid) for qid in qids):
        raise ValueError("Invalid composer identity")
    values = " ".join(f"wd:{qid}" for qid in qids)
    return f"""SELECT DISTINCT ?work ?field ?value ?scheme ?ordinal WHERE {{
      VALUES ?selected {{ {values} }}
      ?work wdt:P86 ?selected; wdt:P31 wd:{WORK_CONCEPT}.
      {{ ?work wdt:P86 ?value. BIND("composers" AS ?field) }} UNION
      {{ ?work wdt:P31 ?value. BIND("types" AS ?field) }} UNION
      {{ ?work rdfs:label ?value. FILTER(LANG(?value) IN ("en", "ko")) BIND("title" AS ?field) }} UNION
      {{ ?work skos:altLabel ?value. FILTER(LANG(?value) IN ("en", "ko")) BIND("alias" AS ?field) }} UNION
      {{ ?work p:P10855 ?s. ?s a wikibase:BestRank; ps:P10855 ?value.
         OPTIONAL {{ ?s pq:P1545 ?ordinal }} BIND("opus" AS ?field) }} UNION
      {{ ?work p:P528 ?s. ?s a wikibase:BestRank; ps:P528 ?value.
         OPTIONAL {{ ?s pq:P972 ?cat. ?cat rdfs:label ?scheme. FILTER(LANG(?scheme) = "en") }}
         OPTIONAL {{ ?s pq:P1545 ?ordinal }} BIND("catalogues" AS ?field) }} UNION
      {{ ?work wdt:P826 ?key. ?key rdfs:label ?value. FILTER(LANG(?value) = "en") BIND("keys" AS ?field) }}
    }}"""


def parse_bindings(bindings):
    records = {}
    for row in bindings:
        qid = row["work"]["value"].rsplit("/", 1)[-1]
        if not QID.fullmatch(qid):
            raise ValueError("Invalid source work identity")
        record = records.setdefault(
            qid,
            {
                "qid": qid,
                "composers": [],
                "types": [],
                "title": "",
                "title_ko": None,
                "aliases": {"en": [], "ko": []},
                "opus": [],
                "catalogues": [],
                "keys": [],
            },
        )
        field, value = row["field"]["value"], row["value"]["value"]
        if field in {"composers", "types"}:
            value = value.rsplit("/", 1)[-1]
        if field in {"title", "alias"}:
            lang = row["value"].get("xml:lang")
            if lang not in {"en", "ko"}:
                raise ValueError("Unexpected source language")
            if field == "title":
                record["title" if lang == "en" else "title_ko"] = value
            elif value not in record["aliases"][lang]:
                record["aliases"][lang].append(value)
            continue
        if field in {"opus", "catalogues"}:
            value = {"value": value, "ordinal": row.get("ordinal", {}).get("value", "")}
            if field == "catalogues":
                value["scheme"] = row.get("scheme", {}).get("value", "")
        if field not in {"composers", "types", "opus", "catalogues", "keys"}:
            raise ValueError("Unexpected source field")
        if value not in record[field]:
            record[field].append(value)
    for record in records.values():
        for field in ("composers", "types", "keys"):
            record[field].sort()
    return sorted(records.values(), key=lambda r: int(r["qid"][1:]))


def fetch_snapshot(registry, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    ids = sorted(registry)
    with httpx.Client(
        timeout=75,
        follow_redirects=False,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "ClassicHubble/0.1 (https://classic-hubble.vercel.app; reference catalog)",
        },
    ) as client:
        for offset in range(0, len(ids), 10):
            query = make_query(ids[offset : offset + 10])
            cache = directory / f"{digest(query)}.json"
            if cache.exists():
                payload = json.loads(cache.read_text())
            else:
                response = client.get(ENDPOINT, params={"query": query})
                response.raise_for_status()
                payload = response.json()
                parse_bindings(payload["results"]["bindings"])
                cache.write_text(json.dumps(payload, ensure_ascii=False))
                time.sleep(1)
            rows.extend(payload["results"]["bindings"])
            print(
                json.dumps(
                    {"composers_checked": min(offset + 10, len(ids)), "rows": len(rows)}
                ),
                flush=True,
            )
    snapshot = {
        "provider": "wikidata",
        "endpoint": ENDPOINT,
        "license": LICENSE,
        "fetched_at": datetime.now(UTC).isoformat(),
        "registry": registry,
        "records": parse_bindings(rows),
        "query_sha256s": [
            digest(make_query(ids[i : i + 10])) for i in range(0, len(ids), 10)
        ],
    }
    snapshot["sha256"] = digest(snapshot)
    destination = directory / "snapshot.json"
    destination.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return destination


def validate_snapshot(snapshot):
    payload = {k: v for k, v in snapshot.items() if k != "sha256"}
    if (
        snapshot.get("provider") != "wikidata"
        or snapshot.get("license") != LICENSE
        or snapshot.get("endpoint") != ENDPOINT
        or digest(payload) != snapshot.get("sha256")
    ):
        raise ValueError("Invalid catalog snapshot integrity or source")
    if not snapshot.get("records") or not snapshot.get("registry"):
        raise ValueError("Empty catalog snapshot")


def apply_plan(repository, plan, snapshot, *, apply=False):
    if not apply:
        return
    originals = {r["qid"]: r for r in snapshot["records"]}
    links = [
        {
            "provider": "wikidata",
            "entity_type": "canonical_work",
            "provider_id": link["source_id"],
            "payload": {
                **link,
                "snapshot_sha256": snapshot["sha256"],
                "license": LICENSE,
                "verification": "source_imported",
                "record": originals[link["source_id"]],
            },
        }
        for link in plan["links"]
    ]
    for table, rows, conflict in (
        ("composers", plan["composers"], "id"),
        ("works", plan["works"], "id"),
        ("work_aliases", plan["aliases"], "work_id,alias"),
        ("provider_records", links, "provider,entity_type,provider_id"),
    ):
        for offset in range(0, len(rows), 200):
            repository._request(
                "POST",
                table,
                params={"on_conflict": conflict},
                json=rows[offset : offset + 200],
                prefer="resolution=ignore-duplicates,return=minimal",
            )


def archive_snapshot(store, snapshot):
    validate_snapshot(snapshot)
    saved = store.archive_catalog_snapshot(snapshot)
    restored = json.loads(store.read(saved.key))
    validate_snapshot(restored)
    if restored["sha256"] != snapshot["sha256"]:
        raise ValueError("Archived catalog snapshot differs from import input")
    return {
        "bucket": store.bucket,
        "key": saved.key,
        "object_sha256": saved.sha256,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--directory", type=Path, required=True)
    fetch.add_argument("--root", type=Path, default=Path.cwd())
    apply = sub.add_parser("import")
    apply.add_argument("--snapshot", type=Path, required=True)
    apply.add_argument("--env-file", type=Path, default=Path(".env"))
    apply.add_argument("--report", type=Path, required=True)
    apply.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        print(fetch_snapshot(load_registry(args.root), args.directory))
        return
    snapshot = json.loads(args.snapshot.read_text())
    validate_snapshot(snapshot)
    environment = {**dotenv_values(args.env_file), **os.environ}
    settings = SupabaseSettings.from_env(environment)
    with SupabaseRepository(settings) as repository:
        composers = repository._read_pages(
            "composers", {"select": "id,name,name_ko,period"}, page_size=1000
        )
        works = repository._read_pages(
            "works",
            {"select": "id,composer_id,slug,title,title_ko,catalogue"},
            page_size=1000,
        )
        plan = build_import_plan(
            snapshot["records"], snapshot["registry"], composers, works
        )
        report = {
            "source": ENDPOINT,
            "snapshot_sha256": snapshot["sha256"],
            "target": settings.url,
            "apply": args.apply,
            "status": "planned",
            "counts": {k: len(v) for k, v in plan.items()},
            "plan": plan,
        }
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        if args.apply:
            with R2Store(R2Settings.from_env(environment)) as store:
                report["archive"] = archive_snapshot(store, snapshot)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        apply_plan(repository, plan, snapshot, apply=args.apply)
        if args.apply:
            report["status"] = "applied"
            report["completed_at"] = datetime.now(UTC).isoformat()
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report["counts"]))


if __name__ == "__main__":
    main()
