"""Split source program blocks without conflating translations and movements."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

from .music_matching import (
    LIFESPAN,
    MusicMatcher,
    _catalogues,
    _genres,
    _keys,
    _variants,
)
from .program_matching import _composer_only, _movement_line, _non_music_line
from .work_matching import CATALOGUE, WorkMatch, _normalize

VERSION = "program-split-v1"
BIRTH = re.compile(r"\(?\s*(?:b\.?\s*|\*)\d{4}\)?", re.IGNORECASE)
TEMPO = re.compile(
    r"^(?:molto\s+)?(?:allegro|allegretto|adagio|andante|andantino|largo|larghetto|"
    r"lento|presto|prestissimo|moderato|vivace|grave|mesto|giocoso|impetuoso|"
    r"interm[eè]de|finale|menuet|scherzo|rondo|ziemlich|lebhaft|intermezzo|"
    r"tr[eè]s anim[eé]|quarter\s*=|langsam|schnell|sehr schnell|non allegro)\b",
    re.IGNORECASE,
)
NUMBERED = re.compile(r"^(?:[IVX]{1,6}|\d{1,2})[.)]\s+")
ARRANGEMENT = re.compile(
    r"arr\.|arranged|arrangement|performed on|편곡|\bver\.", re.IGNORECASE
)
SCOPED = re.compile(
    r"\bfrom\b|\bexcerpt\b|\bmovement\b|악장|\s중\s|中|:.*(?:Overture|Intermezzo)",
    re.IGNORECASE,
)
INSTRUMENTS = r"pianos?|violins?|violas?|cellos?|flutes?|oboe|clarinet|horns?|saxophone|guitar|orchestra|strings|hands|solo|two|four|[248]|and|&"
COLLECTION = re.compile(
    r"\bsuite\b|\bpieces\b|\bvariations\b|\bromances\b|모음곡|소품|변주곡",
    re.IGNORECASE,
)
NAME_INITIAL = re.compile(r"^((?:[A-Z]\.\s*)+[A-ZÀ-Ž][\wÀ-ž'’\-]+)(?:\s+(.+))?$")


def _clean(text: str) -> str:
    return unicodedata.normalize("NFKC", html.unescape(text)).strip()


def _name(text: str) -> str:
    return BIRTH.sub("", LIFESPAN.sub("", text)).strip(" ,:|┃ㅣ/–—-.")


def _composer_label(text: str, matcher: MusicMatcher) -> bool:
    if _composer_only(text, matcher):
        return True
    # A translated name may be absent, but must not contain any work information.
    return (
        bool(re.search(r"[가-힣]", text))
        and not (CATALOGUE.search(text) or _genres(text))
        and len(text.split()) <= 8
        and any(
            _composer_only(p, matcher)
            for p in _variants(text)
            if not re.search(r"[가-힣]", p)
        )
    )


def _unknown_bilingual_name(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"[가-힣]+(?:\s+[가-힣]+)*\s+[A-ZÀ-Ž][a-zà-ž'’\-]+(?:\s+[A-ZÀ-Ž][a-zà-ž'’\-]+){1,3}",
            text,
        )
    ) and not (CATALOGUE.search(text) or _genres(text))


def _credit(line: str) -> bool:
    if CATALOGUE.search(line) or _genres(line):
        return False
    return bool(
        re.search(
            r",\s*(?:piano|violin|viola|cello|guitar|soprano|tenor|orchestra|play-direct)\s*$",
            line,
            re.IGNORECASE,
        )
        or re.match(
            r"^(?:1st|2nd|Piano|Flute|Solo|Gt\.|협연\s*\||소프라노|메조소프라노|오르간|앙상블)\s*[가-힣]",
            line,
        )
        or re.fullmatch(r"[가-힣]{2,5}(?:,\s*[가-힣]{2,5}){2,}", line)
    )


def _context(line: str) -> bool:
    return (
        bool(
            re.search(
                r"^(?:영국|스위스|오스트리아|이탈리아)[,\s].*(?:프롬스|페스티벌)$", line
            )
        )
        or line == "한국 민요"
        or line.startswith("NEGRO SPIRITUALS SERIES")
    )


def _prefix(line: str, matcher: MusicMatcher) -> tuple[str | None, str]:
    clean = _name(line)
    if _composer_label(clean, matcher):
        return clean, ""
    if _unknown_bilingual_name(clean):
        return clean, ""
    life = LIFESPAN.search(line) or BIRTH.search(line)
    if life and line[: life.start()].strip():
        return _name(line[: life.start()]), line[life.end() :].strip()
    # Longest recognized composer prefix; a prefix must end at a word/delimiter.
    ends = [m.start() for m in re.finditer(r"\s+|[|┃ㅣ:/,]|\.{3,}", line)]
    for end in reversed(ends[:24]):
        before = _name(line[:end])
        after = line[end:].lstrip(" .|┃ㅣ:/,–—-")
        if before and after and _composer_label(before, matcher):
            return before, after
    parts = re.split(r"\s*[|┃ㅣ/]\s*|\s+[-–—]\s+|\s*\.{3,}\s*", line, maxsplit=1)
    if len(parts) == 2 and not (CATALOGUE.search(parts[0]) or _genres(parts[0])):
        candidate = _name(parts[0])
        if re.fullmatch(r"(?:[A-Z][\w.'’\-]*\s*){1,6}", candidate):
            return candidate, parts[1]
    initial = NAME_INITIAL.fullmatch(line)
    if initial and not TEMPO.match(re.sub(r"^[IVX]+\.\s*", "", line)):
        return initial[1], initial[2] or ""
    return None, line


def _match_header(title: str, composer: str | None, matcher: MusicMatcher) -> WorkMatch:
    # Strip only explicit credits/arrangement notes, never catalogue/key evidence.
    title = re.sub(
        r"\([^()]*\)",
        lambda m: (
            ""
            if (ARRANGEMENT.search(m[0]) or "협연" in m[0])
            and not CATALOGUE.search(m[0])
            else m[0]
        ),
        title,
    ).strip()
    variants = [title]
    short = re.sub(
        rf"\s+for\s+(?:(?:{INSTRUMENTS})\s*)+$", "", title, flags=re.IGNORECASE
    )
    if short != title:
        variants.append(short)
    results = [matcher.match(t, composer, scoped=True) for t in variants]
    ids = {r.work_id for r in results if r.work_id}
    if len(ids) == 1:
        return next(r for r in results if r.work_id)
    return results[0]


def _result(lines, headers, composer, matcher, reason=None):
    text = "\n".join(lines)
    scope = (
        "arrangement"
        if ARRANGEMENT.search(text)
        else "excerpt"
        if SCOPED.search(text)
        else "unspecified"
    )
    matches = [_match_header(h, composer, matcher) for h in headers]
    if any(h.rstrip().endswith("?") for h in headers):
        reason = reason or "uncertain_source_title"
    ids = {m.work_id for m in matches if m.work_id}
    catalogues = [_catalogues(h) for h in headers if _catalogues(h)]
    keys = set().union(*(_keys(h) for h in headers)) if headers else set()
    if (
        len(ids) > 1
        or len(keys) > 1
        or (len(catalogues) > 1 and any(c != catalogues[0] for c in catalogues[1:]))
    ):
        reason = "conflicting_translations"
    work_id = next(iter(ids)) if len(ids) == 1 and not reason else None
    if not headers and any(NUMBERED.match(_clean(line)) for line in lines):
        reason = reason or "orphan_movements"
    result_reason = reason or (
        next(m.reason for m in matches if m.work_id)
        if work_id
        else matches[0].reason
        if matches
        else "not_program"
    )
    return {
        "display_title": text,
        "composer_name": composer,
        "work_id": work_id,
        "scope": scope,
        "reason": result_reason,
        "candidate_ids": list(
            dict.fromkeys(c for m in matches for c in m.candidate_ids)
        )[:3],
    }


def split_program_block(
    item: dict[str, Any], matcher: MusicMatcher
) -> list[dict[str, Any]]:
    raw = item["display_title"]
    dates = set(re.findall(r"\b(20\d{2})[.년/-]\s*(\d{1,2})(?=[.월/\s)]|$)", raw))
    if len(dates) > 1:
        return [
            _result(
                [raw], [], item.get("composer_name"), matcher, "multiple_program_dates"
            )
        ]
    composer = item.get("composer_name")
    rows, lines, headers = [], [], []

    def flush():
        nonlocal lines, headers
        if lines:
            rows.append(_result(lines, headers, composer, matcher))
        lines, headers = [], []

    for original in raw.splitlines():
        line = _clean(original).lstrip("·• ")
        line = re.sub(
            r"^(?:ES|DE|PL|IT|FR|RU|AT|CZ|US|GB|AR|NO)\s+(?=[가-힣])", "", line
        )
        if not line:
            continue
        if _context(line):
            flush()
            lines.append(original.strip())
            continue
        if (
            _credit(line)
            or _non_music_line(line)
            or re.match(r"^(?:20\d{2}[.]|[12]부$)", line)
            or re.fullmatch(r"[가-힣 ]+(?:홀|공연장)\s*\([^()]+\)", line)
        ):
            lines.append(original.strip())
            continue
        found_composer, title = _prefix(line, matcher)
        known_prefix = (
            found_composer
            and _composer_label(found_composer, matcher)
            and bool(re.search(r"[A-Za-zÀ-ž]{3,}|[가-힣]", found_composer))
        )
        if not known_prefix and (
            _movement_line(line)
            or (
                NUMBERED.match(line)
                and not CATALOGUE.search(line)
                and (not _genres(line) or TEMPO.match(NUMBERED.sub("", line)))
            )
            or (headers and TEMPO.match(line) and not CATALOGUE.search(line))
        ):
            lines.append(original.strip())
            continue
        if found_composer and not title:
            if headers:
                flush()
            composer = found_composer
            lines.append(original.strip())
            continue
        if (
            headers
            and not found_composer
            and (
                line.lower().startswith("from ")
                or (
                    COLLECTION.search(headers[0])
                    and not (CATALOGUE.search(line) or _genres(line))
                )
            )
        ):
            lines.append(original.strip())
            continue
        translation_header = (
            re.split(r"\s+(?:소프라노|메조소프라노|협연)", headers[-1])[0]
            if headers
            else ""
        )
        is_translation = bool(headers) and bool(
            re.search(r"[가-힣]", translation_header)
        ) != bool(re.search(r"[가-힣]", title))
        if found_composer and composer:
            current_identity = matcher._composers(composer)[0]
            new_identity = matcher._composers(found_composer)[0]
            same_unknown_catalogue = (
                (
                    not current_identity
                    and not new_identity
                    and bool(_catalogues(title))
                    and _catalogues(title) == _catalogues(headers[-1])
                )
                if headers
                else False
            )
            is_translation = is_translation and (
                bool(current_identity & new_identity)
                or _normalize(composer) == _normalize(found_composer)
                or same_unknown_catalogue
            )
        if headers and not is_translation:
            flush()
        if found_composer:
            composer = found_composer
        headers.append(title)
        lines.append(original.strip())
    flush()
    return rows or [_result([raw], [], composer, matcher, "empty")]
