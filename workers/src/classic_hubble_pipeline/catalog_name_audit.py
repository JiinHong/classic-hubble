"""Complete, identity-bound source observations for remaining work names."""

import hashlib
import json
import re
import time
from collections import Counter
from datetime import UTC, datetime

from .catalog_import import digest
from .recording_names import observed_name
from .work_catalog import QID, catalogue_code, identity
from .work_matching import CATALOGUE, EXCERPT
from .worklist_names import Document, _conflicts

ENDPOINT = "https://www.wikidata.org/w/api.php"


def _validate_entities(payload, ids):
    entities = payload.get("entities", {})
    if (
        "error" in payload
        or set(entities) != set(ids)
        or any(entity.get("id") != qid for qid, entity in entities.items())
    ):
        raise ValueError("Wikidata error or incomplete identity response")


def fetch_entities(client, qids, directory, *, delay=1):
    if len(set(qids)) != len(qids) or not all(QID.fullmatch(qid) for qid in qids):
        raise ValueError("Invalid or duplicate target identity")
    directory.mkdir(parents=True, exist_ok=True)
    rows = {}
    for offset in range(0, len(qids), 50):
        ids = qids[offset : offset + 50]
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": "|".join(ids),
            "props": "info|labels|aliases|claims|sitelinks",
            "languages": "ko|en",
            "sitefilter": "kowiki|enwiki",
            "maxlag": 5,
        }
        path = directory / f"{digest(params)}.json"
        if path.exists():
            observation = json.loads(path.read_text())
        else:
            response = client.get(ENDPOINT, params=params)
            response.raise_for_status()
            payload = response.json()
            _validate_entities(payload, ids)
            observation = {
                "requested_ids": ids,
                "url": str(response.url),
                "fetched_at": datetime.now(UTC).isoformat(),
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "payload": payload,
            }
            path.write_text(json.dumps(observation, ensure_ascii=False))
            time.sleep(delay)
        if observation["requested_ids"] != ids:
            raise ValueError("Cached source does not cover requested identities")
        _validate_entities(observation["payload"], ids)
        for qid, entity in observation["payload"]["entities"].items():
            rows[qid] = {
                "entity": entity,
                **{k: observation[k] for k in ("url", "fetched_at", "sha256")},
            }
    return rows


def match_exact_name(row, works, aliases):
    """Resolve a unique full name within a composer; never use fuzzy similarity."""
    en, ko = row["title_en"].split(" · ")[0], row["title_ko"].split(" · ")[0]
    if not re.search("[가-힣]", ko) or EXCERPT.search(en + " " + ko):
        return None
    series = re.search(r"\bSequenza\s+([IVX]+)\b", en)
    korean_series = re.search(r"세쿠엔차\s*(\d+)\b", ko)
    if series and korean_series:
        numerals = [
            "I",
            "II",
            "III",
            "IV",
            "V",
            "VI",
            "VII",
            "VIII",
            "IX",
            "X",
            "XI",
            "XII",
            "XIII",
            "XIV",
        ]
        if series[1] not in numerals or numerals.index(series[1]) + 1 != int(
            korean_series[1]
        ):
            return None
    names = {identity(en), identity(observed_name(en))}
    index = {
        w["id"]: w
        for w in works
        if identity(w["composer"]) == identity(row["composer"])
    }
    candidates = {w["id"] for w in index.values() if identity(w["title"]) in names}
    candidates.update(
        a["work_id"]
        for a in aliases
        if a["work_id"] in index and identity(a["alias"]) in names
    )
    if len(candidates) != 1:
        return None
    work = index[next(iter(candidates))]
    expected = catalogue_code(work["catalogue"]) if work.get("catalogue") else None
    codes = {catalogue_code(m.group()) for m in CATALOGUE.finditer(en)} - {None}
    ko_codes = {catalogue_code(m.group()) for m in CATALOGUE.finditer(ko)} - {None}
    if codes != ko_codes or (expected and codes and expected not in codes):
        return None
    title_codes = {
        catalogue_code(m.group()) for m in CATALOGUE.finditer(work["title"])
    } - {None}
    if not expected and any(
        re.search(r"\d[a-z]", code, re.IGNORECASE) for code in codes - title_codes
    ):
        return None
    # An incoming alias may describe a suite discussed on the parent work's page.
    scopes = r"\b(suite|arrangement|excerpt|selection|version)s?\b"
    if set(re.findall(scopes, en.lower())) - set(
        re.findall(scopes, work["title"].lower())
    ):
        return None
    if _conflicts(ko, work) or _conflicts(ko, {**work, "title": en}):
        return None
    return work["id"]


def parse_apple_names(html, locale, artist_id):
    """Read names embedded in public artist HTML, not private query endpoints."""
    scripts = [
        n
        for n in Document(html).root.descendants("script")
        if n.attrs.get("id") == "serialized-server-data"
    ]
    if len(scripts) != 1:
        raise ValueError("Missing public artist metadata")
    payload = json.loads("".join(c for c in scripts[0].children if isinstance(c, str)))
    pages = [
        p
        for p in payload["data"]
        if p.get("intent", {}).get("id") == artist_id
        and p["intent"].get("storefront") == locale
    ]
    if len(pages) != 1 or pages[0]["data"]["header"].get("id") != artist_id:
        raise ValueError("Unexpected public artist identity")
    rows = {}
    for section in pages[0]["data"].get("sections", []):
        for item in section.get("items", []):
            if item.get("type") != "work":
                continue
            url = item.get("url", "")
            if not re.fullmatch(rf"/{locale}/work/[a-z0-9-]+", url):
                continue
            header = item.get("action", {}).get("header", {})
            composer_url = header.get("composerAction", {}).get("url")
            if (
                header.get("type") != "work"
                or composer_url != f"/query/view/{locale}/artist/{artist_id}"
            ):
                continue
            title = header.get("title", "").strip()
            subtitle = (header.get("subtitle") or "").split(" · ")[0].strip()
            if not title or not header.get("composerName"):
                continue
            key = url.rsplit("/", 1)[1]
            row = {
                "title": title + (f", {subtitle}" if subtitle else ""),
                "composer": header["composerName"],
                "composer_id": artist_id,
            }
            if key in rows and rows[key] != row:
                raise ValueError("Conflicting work metadata in artist page")
            rows[key] = row
    return rows


def pair_apple_names(korean, english):
    return [
        {
            "work_key": key,
            "title_ko": korean[key]["title"],
            "title_en": english[key]["title"],
            "composer": english[key]["composer"],
            "composer_ko": korean[key]["composer"],
            "composer_id": korean[key]["composer_id"],
        }
        for key in sorted(korean.keys() & english.keys())
        if korean[key]["composer_id"] == english[key]["composer_id"]
        and re.search("[가-힣]", korean[key]["title"])
    ]


def build_audit(targets, decisions, sources, version):
    if (
        not version
        or not targets
        or len(set(targets)) != len(targets)
        or not all(QID.fullmatch(q) for q in targets)
    ):
        raise ValueError("Invalid audit targets or version")
    ids = [row["qid"] for row in decisions]
    if len(ids) != len(set(ids)) or set(ids) != set(targets):
        raise ValueError("Audit must account for every target exactly once")
    statuses = {
        "named",
        "no_korean_evidence",
        "identity_conflict",
        "source_unavailable",
    }
    for source in sources.values():
        if not source.get("url", "").startswith("https://") or not source.get("kind"):
            raise ValueError("Invalid audit source")
    for row in decisions:
        if row.get("status") not in statuses or not all(
            row.get(k) for k in ("composer", "expected_title", "reason", "sources")
        ):
            raise ValueError("Missing audit outcome or evidence")
        if not set(row["sources"]) <= sources.keys():
            raise ValueError("Unknown audit source")
        if row["status"] == "named" and (
            not row.get("title_ko")
            or not re.fullmatch(r"[a-f0-9]{64}", row.get("dictionary_sha256", ""))
        ):
            raise ValueError("Named outcome needs a guarded naming dictionary")
    audit = {
        "version": version,
        "target_sha256": digest(sorted(targets)),
        "scope": "Every target checked against listed sources. Absence is not proof of absence elsewhere; observed names are not popularity rankings.",
        "summary": {
            "total": len(targets),
            **dict(sorted(Counter(row["status"] for row in decisions).items())),
        },
        "sources": sources,
        "works": sorted(decisions, key=lambda row: int(row["qid"][1:])),
    }
    audit["sha256"] = digest(audit)
    return audit


def plan_audit(audit, works, composers, links):
    fingerprint = audit["sha256"]
    if digest({k: v for k, v in audit.items() if k != "sha256"}) != fingerprint:
        raise ValueError("Audit integrity mismatch")
    validated = build_audit(
        [row["qid"] for row in audit["works"]],
        audit["works"],
        audit["sources"],
        audit["version"],
    )
    if validated != audit:
        raise ValueError("Invalid audit summary or target set")
    work_index = {w["id"]: w for w in works}
    composer_index = {c["id"]: c["name"] for c in composers}
    link_index = {link["provider_id"]: link["payload"]["work_id"] for link in links}
    if len(link_index) != len(links) or len(set(link_index.values())) != len(links):
        raise ValueError("Ambiguous audit identity crosswalk")
    records = []
    for row in audit["works"]:
        work = work_index.get(link_index.get(row["qid"]))
        if (
            not work
            or work["title"] != row["expected_title"]
            or composer_index.get(work["composer_id"]) != row["composer"]
        ):
            raise ValueError("Audit canonical identity conflict")
        records.append(
            {
                "provider": "classic_hubble",
                "entity_type": "work_name_audit",
                "provider_id": f"{row['qid']}:{fingerprint}",
                "payload": {
                    "work_id": work["id"],
                    "audit_sha256": fingerprint,
                    "version": audit["version"],
                    "decision": row,
                    "sources": {key: audit["sources"][key] for key in row["sources"]},
                },
            }
        )
    return records
