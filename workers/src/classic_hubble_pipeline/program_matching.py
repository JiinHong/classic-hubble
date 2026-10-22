from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from typing import Any, Protocol

from .music_matching import (
    LIFESPAN,
    MusicMatcher,
    _genres,
    _name_matches,
    _numbers,
    _variants,
)
from .work_matching import CATALOGUE, EXCERPT, CanonicalWork, WorkMatch


class MatchingRepository(Protocol):
    def load_work_catalog(self) -> list[CanonicalWork]: ...
    def load_unlinked_program_items(self) -> list[dict[str, Any]]: ...
    def link_program_item(self, item: dict[str, Any], work_id: str) -> bool: ...


def _composer_only(text: str, matcher: MusicMatcher) -> bool:
    identities, _ = matcher._composers(text)
    return bool(identities) and all(
        any(_name_matches(part, names) for names in identities)
        for part in _variants(text)
    )


def _non_music_line(text: str) -> bool:
    compact = re.sub(r"[\s\-–—_*]", "", text).casefold()
    return compact in {"intermission", "인터미션"} or text in {
        "※ 본 공연 내용은 주최 측 사정에 의해 변경될 수 있습니다.",
        "The program can be subject to change.",
    }


def _movement_line(text: str) -> bool:
    # Composer initials (L., C.) and numbered works are not movement headings.
    return (
        bool(
            re.match(
                r"^(?:[IVX]{1,5}|\d{1,2})[.)]\s+(?:molto\s+)?(?:allegro|allegretto|adagio|andante|"
                r"andantino|largo|larghetto|lento|presto|prestissimo|moderato|vivace|"
                r"grave|scherzo|rondo|minuet|menuetto|finale|tempo|intermezzo|introduzione|"
                r"improvisation|fantasie|thema mit variationen|tema con variazioni|"
                r"nicht schnell|einfach|hastig|innig|sehr lebhaft|mit einigem pomp|zum beschluss)\b",
                text,
                re.IGNORECASE,
            )
        )
        and not CATALOGUE.search(text)
        and not _numbers(text)
        and not (_genres(text) - {"trio"})
    )


def match_program_text(item: dict[str, Any], matcher: MusicMatcher) -> WorkMatch:
    lines = [
        line.strip() for line in item["display_title"].splitlines() if line.strip()
    ]
    if not lines:
        return WorkMatch(None, (), "empty")
    if all(_non_music_line(line) for line in lines):
        return WorkMatch(None, (), "not_program")
    composer = item["composer_name"]
    first = LIFESPAN.sub("", lines[0]).strip()
    if _composer_only(first, matcher) and len(lines) > 1:
        if composer and not (
            matcher._composers(composer)[0] & matcher._composers(first)[0]
        ):
            return WorkMatch(None, (), "conflicting_composers")
        composer, lines = first, lines[1:]
    if any(
        ";" in line
        or EXCERPT.search(line)
        or re.search(
            r"[>〉》’'\"]\s*중|[中]|\bfrom\b|performed on|\bver\.|\barrang(?:ed|ement)\b",
            line,
            re.IGNORECASE,
        )
        for line in lines
    ):
        return WorkMatch(None, (), "complex_program")
    headers = [lines[0], *(line for line in lines[1:] if not _movement_line(line))]
    if len(headers) > 2:
        return WorkMatch(None, (), "complex_program")
    matches = []
    for header in headers:
        local_composer = composer
        prefix, *rest = re.split(r"\s*[|┃ㅣ:/,]\s*|\s+[-–—]\s+", header, maxsplit=1)
        prefix = LIFESPAN.sub("", prefix).strip()
        if rest and _composer_only(prefix, matcher):
            if composer and not (
                matcher._composers(composer)[0] & matcher._composers(prefix)[0]
            ):
                return WorkMatch(None, (), "conflicting_composers")
            local_composer, header = prefix, rest[0]
        matches.append(matcher.match(header, local_composer))
    if len(matches) == 1:
        return matches[0]
    if matches[0].work_id and matches[0].work_id == matches[1].work_id:
        return WorkMatch(
            matches[0].work_id, matches[0].candidate_ids, "consistent_bilingual_headers"
        )
    return WorkMatch(None, (), "complex_program")


def match_stored_programs(
    repository: MatchingRepository,
    *,
    apply: bool = False,
    batch_size: int = 50,
    after_id: str | None = None,
) -> dict[str, Any]:
    if not 1 <= batch_size <= 200:
        raise ValueError("batch_size must be between 1 and 200")
    works = repository.load_work_catalog()
    matcher = MusicMatcher([replace(w, requires_review=False) for w in works])
    remaining = sorted(
        (
            i
            for i in repository.load_unlinked_program_items()
            if not after_id or i["id"] > after_id
        ),
        key=lambda item: item["id"],
    )
    items = remaining[:batch_size]
    results = []
    matched = updated = 0
    for item in items:
        result = match_program_text(item, matcher)
        if result.work_id:
            matched += 1
            if apply and repository.link_program_item(item, result.work_id):
                updated += 1
        results.append(
            {
                "program_item_id": item["id"],
                "title": item["display_title"],
                "composer": item["composer_name"],
                "source_url": item.get("source_url"),
                "work_id": result.work_id,
                "candidate_ids": result.candidate_ids,
                "reason": result.reason,
            }
        )
    return {
        "mode": "apply" if apply else "dry_run",
        "batch_size": batch_size,
        "after_id": after_id,
        "next_after_id": items[-1]["id"] if items else after_id,
        "has_more": len(remaining) > len(items),
        "catalogue_size": len(works),
        "scanned": len(items),
        "matched": matched,
        "updated": updated,
        "unresolved": len(items) - matched,
        "unresolved_reasons": dict(
            Counter(i["reason"] for i in results if not i["work_id"])
        ),
        "items": results,
    }
