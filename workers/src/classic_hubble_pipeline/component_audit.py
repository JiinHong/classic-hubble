"""Source-scoped composition graph audit, with no inferred track ordering."""

import re
from collections import defaultdict

from .catalog_name_audit import match_exact_name
from .recording_names import match_recording_name, observed_name
from .work_catalog import catalogue_code, identity
from .work_matching import CATALOGUE


def values(entity, prop):
    return [
        c["mainsnak"]["datavalue"]["value"]
        for c in entity.get("claims", {}).get(prop, [])
        if c.get("rank") != "deprecated" and "datavalue" in c.get("mainsnak", {})
    ]


def ids(entity, prop):
    return {v["id"] for v in values(entity, prop) if isinstance(v, dict) and "id" in v}


def wikidata_components(catalog, observations):
    works = {w["id"]: w for w in catalog["works"]}
    links = {r["provider_id"]: r["payload"]["work_id"] for r in catalog["links"]}
    composer_qids = {
        r["payload"]["work_id"]: set(r["payload"]["record"]["composers"])
        for r in catalog["links"]
    }
    edges = defaultdict(list)
    for qid, observed in observations.items():
        for prop in ("P527", "P361"):
            for claim in observed["entity"].get("claims", {}).get(prop, []):
                value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if (
                    claim.get("rank") == "deprecated"
                    or not isinstance(value, dict)
                    or "id" not in value
                ):
                    continue
                key = (qid, value["id"]) if prop == "P527" else (value["id"], qid)
                ordinals = [
                    q.get("datavalue", {}).get("value")
                    for q in claim.get("qualifiers", {}).get("P1545", [])
                ]
                edges[key].append((qid, ordinals))
    rows, held = [], []
    for (parent_qid, child_qid), evidence in sorted(edges.items()):
        parent = works.get(links.get(parent_qid))
        child = works.get(links.get(child_qid))
        observed = observations.get(child_qid)
        reason = None
        positions = {p for _, ordinals in evidence for p in ordinals}
        if not parent or not observed:
            reason = "missing_canonical_parent_or_source"
        elif not ids(observed["entity"], "P31") or ids(observed["entity"], "P31") - {
            "Q105543609",
            "Q929848",
        }:
            reason = "noncanonical_component_type"
        elif ids(observed["entity"], "P86") != composer_qids[parent["id"]]:
            reason = "unconfirmed_component_composer"
        elif child and child["composer_id"] != parent["composer_id"]:
            reason = "canonical_composer_conflict"
        elif len(positions) > 1 or any(
            not isinstance(p, str) or not re.fullmatch(r"[1-9]\d{0,3}", p)
            for p in positions
        ):
            reason = "conflicting_or_noninteger_ordinal"
        elif not observed["entity"].get("labels", {}).get("en", {}).get("value"):
            reason = "missing_english_name"
        if reason:
            held.append(
                {"parent_qid": parent_qid, "child_qid": child_qid, "reason": reason}
            )
            continue
        entity = observed["entity"]
        sources = []
        for qid in sorted({q for q, _ in evidence} | {child_qid}):
            source = observations[qid]
            sources.append(
                {
                    "url": f"https://www.wikidata.org/wiki/{qid}",
                    "sha256": source["sha256"],
                    "revision": source["entity"].get("lastrevid"),
                    "fetched_at": source.get("fetched_at"),
                }
            )
        rows.append(
            {
                "parent_id": parent["id"],
                "expected_parent_title": parent["title"],
                "composer_id": parent["composer_id"],
                "child_qid": child_qid,
                "existing_child_id": child["id"] if child else None,
                "position": int(next(iter(positions))) if positions else None,
                "title": entity["labels"]["en"]["value"],
                "title_ko": entity.get("labels", {}).get("ko", {}).get("value"),
                "aliases": [
                    {"alias": a["value"], "locale": lang}
                    for lang in ("ko", "en")
                    for a in entity.get("aliases", {}).get(lang, [])
                ],
                "sources": sources,
            }
        )
    return rows, held


def resolve_album_parent(row, catalog):
    composers = {c["id"]: c["name"] for c in catalog["composers"]}
    works = [{**w, "composer": composers[w["composer_id"]]} for w in catalog["works"]]
    request = {
        "title_en": row["parent_title_en"],
        "title_ko": row["parent_title_ko"],
        "composer": row["composer"],
    }
    codes = {
        catalogue_code(m.group()) for m in CATALOGUE.finditer(request["title_en"])
    } - {None}
    eligible = [
        w for w in works if identity(w["composer"]) == identity(row["composer"])
    ]
    if (
        len([w for w in eligible if catalogue_code(w.get("catalogue") or "") in codes])
        > 1
    ):
        return None
    match = match_recording_name(request, works) or match_exact_name(
        request, works, catalog["work_aliases"]
    )
    if match:
        return match
    # English-only names can identify a parent, but never overrule catalogue conflicts.
    en = request["title_en"].split(" · ")[0]
    exact = [
        w
        for w in eligible
        if identity(w["title"]) in {identity(en), identity(observed_name(en))}
        and (not codes or catalogue_code(w.get("catalogue") or "") in codes)
    ]
    return exact[0]["id"] if len(exact) == 1 else None
