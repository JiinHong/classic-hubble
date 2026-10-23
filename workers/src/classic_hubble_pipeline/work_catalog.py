"""Conservative reference-catalog imports, independent of concert publication."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .work_matching import CanonicalWork, work_details_conflict

WORK_CONCEPT = "Q105543609"
QID = re.compile(r"Q[1-9]\d*")
NUMBER = re.compile(
    r"(\d+[a-z]?)(?:\s*(?:/|,?\s*(?:no|nr)\.?)\s*(\d+[a-z]?))?", re.IGNORECASE
)
CODE = re.compile(r"(op|bwv|hwv|kv|k|rv|d|s|l|woo)\.?\s*(.+)", re.IGNORECASE)
KEY = re.compile(r"[A-G](?:[- ](?:flat|sharp)|[#♭♯])? (?:major|minor)", re.IGNORECASE)
PREFIXES = {
    "op": "Op.",
    "k": "K.",
    "kv": "K.",
    "d": "D.",
    "s": "S.",
    "l": "L.",
    "woo": "WoO",
}
SCHEMES = {
    "Köchel catalogue": "k",
    "Bach-Werke-Verzeichnis": "bwv",
    "Deutsch catalogue": "d",
    "Händel-Werke-Verzeichnis": "hwv",
    "Ryom-Verzeichnis": "rv",
    "Kirkpatrick catalogue": "k",
}


def identity(value: str) -> str:
    plain = "".join(
        c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)
    )
    return " ".join(
        re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFC", plain).casefold()).split()
    )


def source_id(qid: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"https://www.wikidata.org/wiki/{qid}"))


def catalogue_code(value: str, prefix: str = "", ordinal: str = "") -> str | None:
    if not prefix:
        match = CODE.fullmatch(value.strip())
        if not match:
            return None
        prefix, value = match.groups()
    match = NUMBER.fullmatch(value.strip())
    if not match:
        return None
    number, part = match.groups()
    if ordinal:
        if not re.fullmatch(r"\d+[a-z]?", ordinal, re.IGNORECASE) or (
            part and part != ordinal
        ):
            return None
        part = ordinal
    label = PREFIXES.get(prefix.lower(), prefix.upper())
    return f"{label} {number}" + (f" No. {part}" if part else "")


def normalize_record(
    record: dict[str, Any], registry: dict[str, Any]
) -> dict[str, Any]:
    qid = record["qid"]
    if not QID.fullmatch(qid):
        raise ValueError("invalid_identity")
    composers = record["composers"]
    if len(composers) != 1 or composers[0] not in registry:
        raise ValueError("ambiguous_composer")
    if set(record["types"]) != {WORK_CONCEPT}:
        raise ValueError("noncanonical_type")
    title = record["title"].strip()
    if not title:
        raise ValueError("missing_english_title")
    opus = {
        catalogue_code(v["value"], "op", v.get("ordinal", "")) for v in record["opus"]
    }
    opus.discard(None)
    codes = set()
    for code in record["catalogues"]:
        explicit = CODE.fullmatch(code["value"].strip())
        prefix = (
            explicit.group(1) if explicit else SCHEMES.get(code.get("scheme"), "")
        )
        value = explicit.group(2) if explicit else code["value"]
        # K can name different catalogues; a slash may denote another edition.
        # Do not import an ambiguous source code as a numbered member.
        if prefix.lower() in {"k", "kv"} and "/" in value:
            continue
        parsed = catalogue_code(value, prefix, code.get("ordinal", ""))
        if parsed:
            codes.add(parsed)
    candidates = opus or codes
    catalogue = next(iter(candidates)) if len(candidates) == 1 else None
    source_title = title
    keys = record["keys"]
    if (
        len(keys) == 1
        and KEY.fullmatch(keys[0])
        and not re.search(r"\bin\s+" + KEY.pattern, title, re.IGNORECASE)
    ):
        title += f" in {keys[0]}"
    aliases = {(source_title, "en"), (title, "en")}
    title_ko = record.get("title_ko") or None
    if title_ko:
        aliases.add((title_ko, "ko"))
    for locale in ("en", "ko"):
        aliases.update(
            (a.strip(), locale)
            for a in record.get("aliases", {}).get(locale, [])
            if a.strip()
        )
    return {
        "id": source_id(qid),
        "slug": f"wikidata-{qid.lower()}",
        "source_id": qid,
        "source_url": f"https://www.wikidata.org/wiki/{qid}",
        "composer_qid": composers[0],
        "title": title,
        "title_ko": title_ko,
        "catalogue": catalogue,
        "aliases": [{"alias": a, "locale": lang} for a, lang in sorted(aliases)],
    }


def _title_identity(value: str) -> str:
    return identity(
        re.sub(r"\s+in\s+" + KEY.pattern + r"$", "", value, flags=re.IGNORECASE)
    )


def build_import_plan(records, registry, existing_composers, existing_works):
    """Plan inserts only; no upstream refresh overwrites local curator decisions."""
    if len({r["qid"] for r in records}) != len(records):
        raise ValueError("Duplicate source identity")
    plan = {"composers": [], "works": [], "aliases": [], "links": [], "skipped": []}
    normalized = []
    for record in records:
        try:
            normalized.append(normalize_record(record, registry))
        except ValueError as error:
            plan["skipped"].append({"qid": record["qid"], "reason": str(error)})
    counts = Counter((w["composer_qid"], w["catalogue"]) for w in normalized)
    composers = {}
    for qid, entry in registry.items():
        matches = [
            c
            for c in existing_composers
            if identity(c["name"]) == identity(entry["name"])
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous existing composer identity")
        composers[qid] = matches[0] if matches else {"id": source_id(qid), **entry}
    existing_ids = {w["id"]: w for w in existing_works}
    new_composer_ids = set()
    alias_keys = set()
    for item in normalized:
        composer = composers[item["composer_qid"]]
        work_id = item["id"]
        if work_id in existing_ids:
            if existing_ids[work_id]["composer_id"] != composer["id"]:
                plan["skipped"].append(
                    {"qid": item["source_id"], "reason": "composer_changed"}
                )
                continue
        else:
            matches = [
                w
                for w in existing_works
                if w["composer_id"] == composer["id"]
                and item["catalogue"]
                and identity(w.get("catalogue") or "") == identity(item["catalogue"])
            ]
            if matches:
                match = matches[0]
                expected = CanonicalWork(
                    match["id"],
                    "",
                    (match["title"],),
                    (composer["name"],),
                    match.get("catalogue"),
                )
                if (
                    len(matches) != 1
                    or counts[item["composer_qid"], item["catalogue"]] != 1
                    or _title_identity(item["title"]) != _title_identity(match["title"])
                    or work_details_conflict(item["title"], expected)
                ):
                    plan["skipped"].append(
                        {
                            "qid": item["source_id"],
                            "reason": "existing_catalogue_conflict",
                        }
                    )
                    continue
                work_id = match["id"]
            else:
                plan["works"].append(
                    {
                        "id": work_id,
                        "composer_id": composer["id"],
                        "slug": item["slug"],
                        "title": item["title"],
                        "title_ko": item["title_ko"],
                        "catalogue": item["catalogue"],
                        "instrumentation": None,
                        "popularity_rank": None,
                    }
                )
                if (
                    composer["id"] not in {c["id"] for c in existing_composers}
                    and composer["id"] not in new_composer_ids
                ):
                    plan["composers"].append(composer)
                    new_composer_ids.add(composer["id"])
        # A full-title source marker also keeps unreviewed imports out of auto-linking.
        for alias in item["aliases"]:
            key = (work_id, alias["alias"])
            if key not in alias_keys:
                plan["aliases"].append(
                    {
                        "work_id": work_id,
                        **alias,
                        "source": f"wikidata:{item['source_id']}",
                    }
                )
                alias_keys.add(key)
        plan["links"].append(
            {
                "source_id": item["source_id"],
                "work_id": work_id,
                "source_url": item["source_url"],
            }
        )
    return plan
