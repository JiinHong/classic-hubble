"""Collect identity-bound article names; never infer work IDs from titles."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

import httpx
from dotenv import dotenv_values

from .catalog_import import digest
from .korean_title_forms import build_manifest as build_formal_manifest
from .supabase import SupabaseRepository, SupabaseSettings

LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"


def fetch_pages(client, titles, directory, *, delay=1, language="ko"):
    if language not in {"ko", "en"}:
        raise ValueError("Unsupported language")
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    directory.mkdir(parents=True, exist_ok=True)
    merged = {}
    titles = sorted(set(titles))
    for offset in range(0, len(titles), 50):
        continuation = {}
        while True:
            params = {
                "action": "query",
                "format": "json",
                "maxlag": 5,
                "prop": "pageprops|redirects|revisions",
                "titles": "|".join(titles[offset : offset + 50]),
                "rdlimit": "max",
                "rdnamespace": 0,
                "rdprop": "title|fragment|pageid",
                "rvprop": "ids",
                **continuation,
            }
            cache = (
                directory / f"{digest({'endpoint': endpoint, 'params': params})}.json"
            )
            if cache.exists():
                payload = json.loads(cache.read_text())
            else:
                response = client.get(endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
                if "error" in payload:
                    raise ValueError(f"Wikipedia API error: {payload['error']['code']}")
                cache.write_text(json.dumps(payload, ensure_ascii=False))
                time.sleep(delay)
            for page in payload["query"]["pages"].values():
                key = page.get("pageid", page["title"])
                previous = merged.get(key, {})
                merged[key] = {
                    **previous,
                    **page,
                    "redirects": previous.get("redirects", [])
                    + page.get("redirects", []),
                }
            continuation = payload.get("continue")
            if not continuation:
                break
    return list(merged.values())


def build_manifest(pages, works, composers, links, *, language="ko"):
    if language not in {"ko", "en"}:
        raise ValueError("Unsupported language")
    name_pattern = "[가-힣]" if language == "ko" else "[A-Za-z]"
    work_index = {w["id"]: w for w in works}
    composer_index = {c["id"]: c for c in composers}
    link_index = {link["provider_id"]: link["payload"]["work_id"] for link in links}
    if len(link_index) != len(links) or len(set(link_index.values())) != len(links):
        raise ValueError("Ambiguous canonical crosswalk")
    sources, entries, seen = {}, [], set()
    for page in pages:
        props = page.get("pageprops", {})
        qid = props.get("wikibase_item")
        work = work_index.get(link_index.get(qid))
        if (
            not work
            or page.get("ns") != 0
            or "missing" in page
            or "disambiguation" in props
            or not page.get("revisions")
            or not re.search(name_pattern, page["title"])
        ):
            continue
        if qid in seen:
            raise ValueError(f"Multiple articles for {qid}")
        seen.add(qid)
        composer = composer_index[work["composer_id"]]
        composer_name = composer["name_ko" if language == "ko" else "name"]
        suffixes = {composer_name, composer_name.split()[-1]}

        def clean_title(value, suffixes=suffixes):
            value = unicodedata.normalize("NFC", value)
            for suffix in suffixes:
                value = value.removesuffix(f" ({suffix})")
            return value

        names = {page["title"], clean_title(page["title"])}
        for redirect in page.get("redirects", []):
            if (
                redirect.get("ns") == 0
                and "fragment" not in redirect
                and re.search(name_pattern, redirect["title"])
            ):
                names.update({redirect["title"], clean_title(redirect["title"])})
        source_id = f"{language}wiki-{page['pageid']}"
        sources[source_id] = {
            "url": f"https://{language}.wikipedia.org/w/index.php?oldid={page['revisions'][0]['revid']}",
            "kind": "encyclopedia_names",
            "publisher": "한국어 위키백과 기여자"
            if language == "ko"
            else "English Wikipedia contributors",
            "license": LICENSE,
            "qid": qid,
            "page_id": page["pageid"],
            "revision_id": page["revisions"][0]["revid"],
            "article_title": page["title"],
            "redirects": page.get("redirects", []),
            "redirect_evidence": "Incoming redirects observed at collection time; not historical revision claims.",
        }
        entries.append(
            {
                "qid": qid,
                "composer": composer["name"],
                "expected_title": work["title"],
                "previous_title_ko": work["title_ko"],
                "title_ko": work["title_ko"]
                or (clean_title(page["title"]) if language == "ko" else None),
                "display_title_origin": "existing"
                if work["title_ko"]
                else source_id
                if language == "ko"
                else "unavailable",
                "sources": [source_id],
                "aliases": [
                    {
                        "text": name,
                        "kind": "title",
                        "locale": language,
                        "sources": [source_id],
                    }
                    for name in sorted(names)
                ],
            }
        )
    return {
        "version": f"2026-10-21.wikipedia.{language}.2",
        "language": language,
        "origin": "wikipedia-names",
        "checked_at": datetime.now(UTC).isoformat(),
        "policy": "Exact Wikidata identity only. Preserve existing display names. Exclude section redirects. Names are observed, not popularity-ranked or curator-verified.",
        "sources": sources,
        "works": sorted(entries, key=lambda e: int(e["qid"][1:])),
    }


def public_evidence(manifests):
    return {
        "attribution": "한국어·영어 위키백과 기여자 (CC BY-SA 4.0), Wikidata (CC0). Names only; no article prose. Formal renderings are editorial transformations, not observed nicknames.",
        "datasets": [
            {
                "version": manifest["version"],
                "origin": manifest["origin"],
                "language": manifest.get("language", "ko"),
                "sources": manifest["sources"],
                "works": [
                    {
                        key: entry[key]
                        for key in (
                            "qid",
                            "composer",
                            "title_ko",
                            "display_title_origin",
                            "sources",
                            "aliases",
                        )
                    }
                    for entry in manifest["works"]
                ],
            }
            for manifest in manifests
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sitelinks", type=Path, required=True)
    parser.add_argument("--language", choices=("ko", "en"), default="ko")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--formal-output", type=Path)
    parser.add_argument("--public-output", type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args(argv)
    if args.formal_output and args.language != "ko":
        parser.error("Formal renderings are supported only for Korean")
    settings = SupabaseSettings.from_env({**dotenv_values(args.env_file), **os.environ})
    if settings.url != "https://klnfamtwxwrelrjeguqb.supabase.co":
        raise ValueError("Classic Hubble project required")
    with SupabaseRepository(settings) as repository:
        works = repository._read_pages(
            "works", {"select": "id,title,title_ko,composer_id"}, page_size=1000
        )
        composers = repository._read_pages(
            "composers", {"select": "id,name,name_ko"}, page_size=1000
        )
        links = repository._read_pages(
            "provider_records",
            {
                "select": "provider_id,payload",
                "provider": "eq.wikidata",
                "entity_type": "eq.canonical_work",
            },
            page_size=1000,
        )
    qids = {link["provider_id"] for link in links}
    bindings = json.loads(args.sitelinks.read_text())["results"]["bindings"]
    titles = {
        unquote(row["article"]["value"].split("/wiki/", 1)[1]).replace("_", " ")
        for row in bindings
        if row["work"]["value"].rsplit("/", 1)[-1] in qids
        and row["article"]["value"].startswith(
            f"https://{args.language}.wikipedia.org/wiki/"
        )
    }
    with httpx.Client(
        timeout=75,
        headers={
            "User-Agent": "ClassicHubble/0.1 (https://classic-hubble.vercel.app; work names)"
        },
    ) as client:
        pages = fetch_pages(client, titles, args.cache, language=args.language)
    manifest = build_manifest(pages, works, composers, links, language=args.language)
    manifests = [manifest]
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if args.formal_output:
        formal = build_formal_manifest(works, composers, links)
        manifests.append(formal)
        args.formal_output.write_text(
            json.dumps(formal, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "formal_titles": len(formal["works"]),
                    "empty_titles_filled": sum(
                        not e["previous_title_ko"] for e in formal["works"]
                    ),
                }
            )
        )
    if args.public_output:
        args.public_output.parent.mkdir(parents=True, exist_ok=True)
        args.public_output.write_text(
            json.dumps(
                public_evidence(manifests), ensure_ascii=False, separators=(",", ":")
            )
            + "\n"
        )
    print(
        json.dumps(
            {
                "articles": len(pages),
                "works": len(manifest["works"]),
                "names": sum(len(e["aliases"]) for e in manifest["works"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
