from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

CATALOGUE = re.compile(
    r"\b(?:op|bwv|hwv|kv|k|rv|d|s|l)\.?\s*\d+[a-z]?"
    r"(?:\s*[,/]?\s*(?:no|nr)\.?\s*\d+[a-z]?)?\b",
    re.IGNORECASE,
)
MOVEMENT = re.compile(r"^(?:[IVXLCDM]+|\d+)[.)]\s+", re.IGNORECASE)
EXCERPT = re.compile(
    r"(?:[:：]\s*[IVXLCDM]+\.|\b(?:excerpt|movement|arr\.)\b|악장|발췌|편곡)",
    re.IGNORECASE,
)
WORK_NUMBER = re.compile(r"\bno\.?\s*(\d+)\b", re.IGNORECASE)
MUSICAL_KEY = re.compile(
    r"\bin\s+([a-g](?:[- ]?(?:flat|sharp)|[#♭♯])?\s+(?:major|minor))\b", re.IGNORECASE
)


@dataclass(frozen=True)
class CanonicalWork:
    id: str
    slug: str
    titles: tuple[str, ...]
    composers: tuple[str, ...]
    catalogue: str | None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkMatch:
    work_id: str | None
    candidate_ids: tuple[str, ...]
    reason: str


def _normalize(value: str) -> str:
    # Strip Latin accents but retain composed Hangul syllables.
    value = "".join(
        c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)
    )
    value = unicodedata.normalize("NFC", value).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", value).split())


def _composer_matches(value: str, names: Sequence[str]) -> bool:
    tokens = _normalize(value).split()
    if not tokens:
        return False
    for name in names:
        expected = _normalize(name).split()
        if tokens == expected or tokens == expected[-1:]:
            return True
        if len(tokens) == len(expected) and all(
            actual == full or (len(actual) == 1 and full.startswith(actual))
            for actual, full in zip(tokens, expected)
        ):
            return True
    return False


def _catalogue_key(value: str) -> str:
    return _normalize(value).replace(" ", "")


def work_details_conflict(title: str, work: CanonicalWork) -> bool:
    """Check explicit work numbers and English keys against the canonical titles."""
    for pattern in (WORK_NUMBER, MUSICAL_KEY):
        actual = {
            _normalize(value) for value in pattern.findall(CATALOGUE.sub("", title))
        }
        expected = {
            _normalize(value) for text in work.titles for value in pattern.findall(text)
        }
        if actual and expected and not actual.issubset(expected):
            return True
    return False


def match_work(
    title: str, composer: str | None, works: Sequence[CanonicalWork]
) -> WorkMatch:
    """Link only one explicit work; uncertain text stays available for review."""
    lines = [line.strip() for line in title.splitlines() if line.strip()]
    if not lines:
        return WorkMatch(None, (), "empty")
    if (
        ";" in lines[0]
        or EXCERPT.search(lines[0])
        or any(not MOVEMENT.match(line) for line in lines[1:])
    ):
        return WorkMatch(None, (), "complex_program")

    normalized = _normalize(lines[0])
    catalogues = {
        _catalogue_key(match.group()) for match in CATALOGUE.finditer(lines[0])
    }
    candidates: list[tuple[CanonicalWork, str]] = []
    for work in works:
        expected = _catalogue_key(work.catalogue or "")
        if work_details_conflict(lines[0], work):
            continue
        exact_title = normalized in {
            _normalize(text) for text in (*work.titles, *work.aliases)
        }
        if catalogues:
            if not expected or catalogues != {expected}:
                continue
            reason = "composer_and_catalogue"
        elif exact_title:
            reason = "composer_and_alias"
        else:
            continue
        candidates.append((work, reason))

    supported = [
        (work, reason)
        for work, reason in candidates
        if composer and _composer_matches(composer, work.composers)
    ]
    composer_identities = {
        tuple(sorted(_normalize(name) for name in work.composers))
        for work in works
        if composer and _composer_matches(composer, work.composers)
    }
    if supported and len(composer_identities) > 1:
        return WorkMatch(
            None, tuple(work.id for work, _ in supported)[:3], "ambiguous_composer"
        )
    if len(supported) == 1:
        work, reason = supported[0]
        return WorkMatch(work.id, (work.id,), reason)
    if len(supported) > 1:
        return WorkMatch(None, tuple(work.id for work, _ in supported)[:3], "ambiguous")
    return WorkMatch(
        None,
        tuple(work.id for work, _ in candidates)[:3],
        "composer_unconfirmed" if candidates else "no_candidate",
    )
