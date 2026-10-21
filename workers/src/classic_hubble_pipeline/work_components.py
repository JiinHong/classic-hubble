"""Evidence-bound component imports; parent works and recordings stay distinct."""

import json
import re
from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from .catalog_import import digest
from .work_catalog import QID, identity, source_id
from .worklist_names import Document


def apply_component_plan(repository, plan, *, apply=False):
    if not apply:
        return
    for table, rows, conflict in (
        ("works", plan["works"], "id"),
        ("work_aliases", plan["aliases"], "work_id,alias"),
        ("provider_records", plan["provenance"], "provider,entity_type,provider_id"),
    ):
        for offset in range(0, len(rows), 100):
            repository._request(
                "POST",
                table,
                params={"on_conflict": conflict},
                json=rows[offset : offset + 100],
                prefer="resolution=ignore-duplicates,return=minimal",
            )


def numbered_title(value):
    match = re.match(r"^(?:No\.\s*)?(\d+|[IVXLCDM]+)[.,:]\s*(.+)$", value.strip())
    if not match or re.search(
        r"\b(?:arr\.|arranged\b|version\b|remaster\b|live\b)", value, re.IGNORECASE
    ):
        return None
    number, title = match.groups()
    if number.isdigit():
        ordinal = int(number)
    else:
        values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        ordinal = sum(
            -values[c]
            if i + 1 < len(number) and values[c] < values[number[i + 1]]
            else values[c]
            for i, c in enumerate(number)
        )
        if not re.fullmatch(
            r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", number
        ):
            return None
    if (
        not 0 < ordinal < 10000
        or not any(c.isalnum() for c in title)
        or re.search(r"\b[IVX]+\.\s", title)
    ):
        return None
    return ordinal, title.strip()


def parse_album_parts(html, locale, album_id):
    scripts = [
        n
        for n in Document(html).root.descendants("script")
        if n.attrs.get("id") == "serialized-server-data"
    ]
    if len(scripts) != 1:
        raise ValueError("Missing album identity metadata")
    payload = json.loads("".join(c for c in scripts[0].children if isinstance(c, str)))
    pages = [
        p
        for p in payload["data"]
        if p.get("intent", {}).get("id") == album_id
        and p["intent"].get("storefront") == locale
    ]
    if len(pages) != 1 or pages[0]["data"].get("screenId") != album_id:
        raise ValueError("Unexpected album identity")
    rows = []
    for section in pages[0]["data"].get("sections", []):
        header = section.get("header", {})
        if header.get("kind") != "work":
            continue
        item = header["item"]
        composers, works = item.get("firstRowLinks", []), item.get("secondRowLinks", [])
        if len(composers) != 1 or len(works) != 1:
            continue
        composer = composers[0].get("segue", {}).get("destination", {})
        work = works[0].get("segue", {}).get("destination", {})
        key, artist = work.get("id"), composer.get("id")
        if (
            not key
            or not artist
            or work.get("pageType") != "work"
            or work.get("contentDescriptor", {}).get("url") != f"/{locale}/work/{key}"
            or composer.get("contentDescriptor", {}).get("url")
            != f"/{locale}/artist/{artist}"
        ):
            continue
        tracks = section.get("items", [])
        contradictory = False
        for track in tracks:
            parsed = numbered_title(track.get("title", ""))
            variation = re.search(
                r"\bVar(?:iation)?\.?\s*(\d+)", track.get("title", ""), re.IGNORECASE
            )
            if parsed and variation and parsed[0] != int(variation[1]):
                contradictory = True
        if contradictory:
            continue
        for track in tracks:
            tid = re.fullmatch(
                rf"track-lockup - {re.escape(album_id)} - (\d+)", track.get("id", "")
            )
            parsed = numbered_title(track.get("title", ""))
            if not tid or not parsed:
                continue
            ordinal, title = parsed
            rows.append(
                {
                    "track_id": tid[1],
                    "parent_key": key,
                    "composer_id": artist,
                    "composer": item["firstRowText"],
                    "parent_title": item["secondRowText"],
                    "position": ordinal,
                    "title": title,
                }
            )
    return rows


def pair_album_parts(korean, english):
    def index(rows):
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row["track_id"], row["parent_key"])].append(row)
        return {k: v[0] for k, v in grouped.items() if len(v) == 1}

    ko, en = index(korean), index(english)
    rows = []
    for key in sorted(ko.keys() & en.keys()):
        a, b = ko[key], en[key]
        if (a["position"], a["composer_id"]) != (b["position"], b["composer_id"]):
            continue
        rows.append(
            {
                **b,
                "title_en": b["title"],
                "title_ko": a["title"] if re.search("[가-힣]", a["title"]) else None,
                "parent_title_ko": a["parent_title"],
                "parent_title_en": b["parent_title"],
            }
        )
    return sorted(rows, key=lambda r: (r["parent_key"], r["position"], r["track_id"]))


def build_component_plan(observations, works, aliases, relations):
    wi = {w["id"]: w for w in works}
    slugs = {w["slug"]: w for w in works}
    alias_keys = {(a["work_id"], a["alias"]) for a in aliases}
    existing = {(r["parent_slug"], r["child_slug"]): r for r in relations}
    adjacency = defaultdict(set)
    for a, b in existing:
        adjacency[a].add(b)
    groups = defaultdict(list)
    for row in observations:
        groups[
            (
                row["parent_id"],
                row.get("position"),
                (row.get("existing_child_id") or row.get("child_qid"))
                if row.get("position") is None
                else None,
            )
        ].append(row)
    plan = {"works": [], "aliases": [], "relations": [], "held": [], "provenance": []}

    def reachable(start, target):
        pending, visited = [start], set()
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node not in visited:
                visited.add(node)
                pending.extend(adjacency[node])
        return False

    for rows in groups.values():
        if (
            len({identity(r["title"]) for r in rows}) != 1
            or len({r["existing_child_id"] for r in rows if r.get("existing_child_id")})
            > 1
            or len({r["child_qid"] for r in rows if r.get("child_qid")}) > 1
        ):
            plan["held"].extend(
                {"observation": r, "reason": "conflicting_component_titles"}
                for r in rows
            )
            continue
        for row in rows:
            parent = wi.get(row["parent_id"])
            position = row.get("position")
            reason = None
            if (
                not parent
                or parent["title"] != row["expected_parent_title"]
                or parent["composer_id"] != row["composer_id"]
            ):
                reason = "parent_identity_conflict"
            elif position is not None and (
                type(position) is not int or not 0 < position < 10000
            ):
                reason = "invalid_component_number"
            elif not row.get("sources") or any(
                not s.get("url", "").startswith("https://")
                or not re.fullmatch(r"[a-f0-9]{64}", s.get("sha256", ""))
                for s in row["sources"]
            ):
                reason = "missing_source_evidence"
            elif not row["title"].strip():
                reason = "missing_component_name"
            elif row.get("child_qid") and not QID.fullmatch(row["child_qid"]):
                reason = "invalid_source_identity"
            if reason:
                plan["held"].append({"observation": row, "reason": reason})
                continue
            qid = row.get("child_qid")
            slug = (
                f"wikidata-{qid.lower()}"
                if qid
                else f"component-{parent['slug']}-{position}"
            )
            child_id = row.get("existing_child_id") or (
                source_id(qid)
                if qid
                else str(
                    uuid5(
                        NAMESPACE_URL, f"https://classic-hubble.vercel.app/works/{slug}"
                    )
                )
            )
            child = wi.get(child_id)
            if row.get("existing_child_id") and not child:
                reason = "missing_existing_child"
            elif not child and position is None and not qid:
                reason = "missing_component_number"
            elif child and (
                child["composer_id"] != parent["composer_id"]
                or child_id == parent["id"]
            ):
                reason = "child_identity_conflict"
            elif (
                child
                and not row.get("existing_child_id")
                and child["title"] != row["title"]
            ):
                reason = "existing_number_conflict"
            elif not child and slug in slugs:
                reason = "existing_slug_conflict"
            child_slug = child["slug"] if child else slug
            key = (parent["slug"], child_slug)
            if reachable(child_slug, parent["slug"]):
                reason = "component_cycle"
            if key in existing and existing[key].get("position") != position:
                reason = "existing_position_conflict"
            if reason:
                plan["held"].append({"observation": row, "reason": reason})
                continue
            if not child:
                child = {
                    "id": child_id,
                    "slug": slug,
                    "composer_id": parent["composer_id"],
                    "title": row["title"],
                    "title_ko": row.get("title_ko"),
                    "catalogue": row.get("catalogue"),
                    "instrumentation": parent.get("instrumentation"),
                    "popularity_rank": None,
                }
                plan["works"].append(child)
                wi[child_id] = child
                slugs[slug] = child
            fingerprint = digest(row)
            names = [(row["title"], "en"), (row.get("title_ko"), "ko")]
            names += [(a["alias"], a["locale"]) for a in row.get("aliases", [])]
            for name, locale in names:
                if name and (child_id, name) not in alias_keys:
                    plan["aliases"].append(
                        {
                            "work_id": child_id,
                            "alias": name,
                            "locale": locale,
                            "source": f"component-source:{fingerprint}",
                        }
                    )
                    alias_keys.add((child_id, name))
            relation = {
                "parent_slug": parent["slug"],
                "child_slug": child_slug,
                "parent_id": parent["id"],
                "child_id": child_id,
                "position": position,
            }
            if key not in existing:
                plan["relations"].append(relation)
                existing[key] = relation
                adjacency[key[0]].add(key[1])
            plan["provenance"].append(
                {
                    "provider": "classic_hubble",
                    "entity_type": "work_component",
                    "provider_id": fingerprint,
                    "payload": {
                        "relation": relation,
                        "observation": row,
                        "verification": "source_imported",
                        "requires_review": True,
                    },
                }
            )
    return plan
