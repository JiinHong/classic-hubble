"""Conservative matching of grounded fields, without changing legacy ingestion."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from functools import lru_cache

from .work_matching import (
    CATALOGUE as LEGACY_CATALOGUE,
    CanonicalWork,
    WorkMatch,
    _catalogue_key,
    _composer_matches,
    _normalize,
)

# WAB support is limited to grounded matching, not legacy ingestion or import.
CATALOGUE = re.compile(LEGACY_CATALOGUE.pattern + r"|\bWAB\.?\s*\d+\b", re.IGNORECASE)
LIFESPAN = re.compile(r"\(?\b\d{4}\s*[-–—~]\s*\d{4}\b\)?")
LATIN_NOTE_KEY = re.compile(
    r"(?<![a-z])(?:in\s*)?([a-g])\s*([- ]?(?:flat|sharp)|[b#♭♯])?\s*(major|minor|장조|단조)\b",
    re.IGNORECASE,
)
KOREAN_KEY = re.compile(r"(내림|올림)?\s*([가나다라마바사]|[A-Ga-g][b#♭♯]?)\s*(장|단)조")
KOREAN_NOTES = dict(zip("다라마바사가나", "cdefgab"))
QUALIFIED_STRAUSS_NAMES = {
    "johann strauss i": 1,
    "johann strauss ii": 2,
    "johann strauss jr": 2,
    "johann strauss junior": 2,
    "johann strauss iii": 3,
}
# PF301618 prints this full Korean spelling beside Gaetano Donizetti.
FULL_NAME_TRANSLITERATIONS = {"가에타노도니제티": "gaetano donizetti"}
GENERIC_TITLES = {
    "waltz",
    "왈츠",
    "sonata",
    "소나타",
    "symphony",
    "교향곡",
    "concerto",
    "협주곡",
    "prelude",
    "전주곡",
    "etude",
    "연습곡",
    "nocturne",
    "야상곡",
    "minuet",
    "미뉴에트",
    "fantasy",
    "fantasia",
    "fantaisie",
    "fantasie",
    "phantasy",
}


@lru_cache(maxsize=40_000)
def _variants(text: str) -> tuple[str, ...]:
    text = LIFESPAN.sub("", text)
    parts = re.findall(r"[가-힣]+(?:\s*[가-힣]+)*|[^가-힣]+", text)
    return tuple(
        dict.fromkeys(
            part.strip(" ()[],:;/") for part in parts if part.strip(" ()[],:;/")
        )
    )


@lru_cache(maxsize=80_000)
def _keys(text: str) -> frozenset[str]:
    result = set()
    for accidental, note, mode in KOREAN_KEY.findall(text):
        modifier = "b" if accidental == "내림" else "#" if accidental else ""
        result.add(
            KOREAN_NOTES.get(note, note.lower()).replace("♭", "b").replace("♯", "#")
            + modifier
            + ":"
            + ("major" if mode == "장" else "minor")
        )
    # Consume Korean accidentals first so "내림B장조" is not also read as B natural.
    for note, accidental, mode in LATIN_NOTE_KEY.findall(KOREAN_KEY.sub(" ", text)):
        modifier = accidental.strip("- ").lower()
        modifier = "b" if modifier in {"flat", "b", "♭"} else "#" if modifier else ""
        mode = {"장조": "major", "단조": "minor"}.get(mode, mode.lower())
        result.add(note.lower() + modifier + ":" + mode)
    return frozenset(result)


@lru_cache(maxsize=80_000)
def _catalogues(text: str) -> frozenset[str]:
    # Koechel editions use alternate numbers, unlike Op.102/2 (a collection member).
    text = re.sub(
        r"\b(KV?)\.?\s*(\d+[a-z]?)\s*(?:/\s*(\d+[a-z]?)|\(\s*(\d+[a-z]?)\s*\))",
        lambda m: f"{m[1]}. {m[2]}; {m[1]}. {m[3] or m[4]}",
        text,
        flags=re.IGNORECASE,
    )
    values = {_catalogue_key(m.group()) for m in CATALOGUE.finditer(text)}
    # A duplicated root plus its explicit member denotes the member, not two works.
    return frozenset(
        v for v in values if not any(w.startswith(v + "no") for w in values)
    )


def _root(value: str) -> str:
    return value.split("no", 1)[0]


def _scheme(value: str) -> str:
    return re.match(r"[a-z]+", value).group()


def _title_key(text: str) -> str:
    text = re.sub(
        r"\bno\.?\s*0*(\d+)\b", lambda m: f"No {int(m[1])}", text, flags=re.IGNORECASE
    )
    text = re.sub(r"(?:제\s*)?(\d+)\s*번", lambda m: f"No {int(m[1])}", text)
    value = _normalize(text)
    return value.replace(" ", "") if re.search(r"[가-힣]", value) else value


def _catalogue_ocr(text: str) -> str:
    # Only the known Op. prefix is repaired; catalogue digits remain evidence.
    return re.sub(r"(?<!\w)0p(?=\.?\s*\d)", "Op", text, flags=re.IGNORECASE)


def _scoped_titles(text: str) -> frozenset[str]:
    parts = [text]
    korean, latin = re.search(r"[가-힣]", text), re.search(r"[A-Za-z]", text)
    if korean and latin:
        split = max(korean.start(), latin.start())
        parts.extend([text[:split], text[split:]])
    variants = set()
    for part in parts:
        clean = re.sub(r"^\s*from\s+", "", part, flags=re.IGNORECASE)
        clean = re.sub(r"[»〉》>\]}’'\"]\s*중\s*$", "", clean)
        clean = clean.strip(" {}[]<>«»〈〉《》‘’\"'.,")
        variants.update(_titles(clean))
        # Only scoped references may use a delimited parent title. All constraints
        # (numbers, keys, catalogues, genres) still come from the entire input.
        prefix, *suffix = re.split(r"[:：'‘“\"]", clean, maxsplit=1)
        if suffix and not re.search(r"\bfrom\b", suffix[0], re.IGNORECASE):
            variants.update(_titles(prefix))
    return frozenset(variants)


@lru_cache(maxsize=80_000)
def _titles(text: str) -> frozenset[str]:
    parts = [text, *re.findall(r'"([^"\n]+)"|“([^”\n]+)”', text)]
    parts.extend(re.findall(r"(?:^|\s)'([^'\n]+)'|‘([^’'\n]+)[’']", text))
    # Split bilingual labels, not digits within "교향곡 5번" or "협주곡 No.10".
    korean, latin = re.search(r"[가-힣]", text), re.search(r"[A-Za-z]", text)
    if korean and latin:
        split = max(korean.start(), latin.start())
        left, right = text[:split], text[split:]
        english = left if latin.start() < korean.start() else right
        meaningful = re.sub(
            r"\b(?:no|nr|op|bwv|hwv|kv|k|rv|in|major|minor)\b",
            "",
            english,
            flags=re.IGNORECASE,
        )
        if re.search(r"[A-Za-z]{2,}", meaningful):
            parts.extend([left, right])
    flattened = [
        value
        for part in parts
        for value in (part if isinstance(part, tuple) else (part,))
        if value
    ]
    result = set()
    for value in flattened:
        result.add(_title_key(value))
        stripped = CATALOGUE.sub("", value)
        stripped = KOREAN_KEY.sub("", stripped)
        stripped = LATIN_NOTE_KEY.sub("", stripped)
        if stripped.strip(" ,;:()"):
            result.add(_title_key(stripped))
    # Split numbered ballades retain their printed plural. Add this equivalent
    # only to composer-scoped comparisons, never the composerless title index.
    result.update(
        re.sub(r"^ballades (no \d+)$", r"ballade \1", value)
        for value in tuple(result)
    )
    return frozenset(result - {""})


@lru_cache(maxsize=80_000)
def _numbers(text: str) -> frozenset[int]:
    text = CATALOGUE.sub("", text)
    return frozenset(
        int(english or korean)
        for english, korean in re.findall(
            r"\bno\.?\s*(\d+)\b|(?:제\s*)?(\d+)\s*번",
            text,
            flags=re.IGNORECASE,
        )
    )


@lru_cache(maxsize=80_000)
def _genres(text: str) -> frozenset[str]:
    patterns = {
        "sonata": r"\bsonatas?\b|소나타",
        "concerto": r"\bconcertos?\b|협주곡",
        "symphony": r"\bsymphon(?:y|ies)\b|교향곡",
        "quartet": r"\bquartets?\b|사중주",
        "quintet": r"\bquintets?\b|오중주|(?<!\d)5\s*중주",
        "trio": r"\btrios?\b|삼중주",
        "canzone": r"\bcanzone\b",
    }
    return frozenset(
        name
        for name, pattern in patterns.items()
        if re.search(pattern, text, re.IGNORECASE)
    )


@lru_cache(maxsize=80_000)
def _name_matches(actual: str, names: tuple[str, ...]) -> bool:
    alias = FULL_NAME_TRANSLITERATIONS.get(_normalize(actual).replace(" ", ""))
    if alias is not None and any(_normalize(name) == alias for name in names):
        return True
    # Generation is identity evidence, not an initial that may expand I to II.
    generation = QUALIFIED_STRAUSS_NAMES.get(_normalize(actual))
    if generation is not None:
        return any(
            QUALIFIED_STRAUSS_NAMES.get(_normalize(name)) == generation
            for name in names
        )
    if _composer_matches(actual, names):
        return True
    tokens = _normalize(actual).split()
    if len(tokens) >= 2 and all(re.fullmatch(r"[a-z]+", t) for t in tokens):
        for name in names:
            expected = _normalize(name).split()
            if len(expected) > len(tokens) and tokens[-1] == expected[-1]:
                if _composer_matches(actual, (" ".join(expected[-len(tokens) :]),)):
                    return True
    compact = _normalize(actual).replace(" ", "")
    return bool(re.fullmatch(r"[가-힣]+", compact)) and any(
        compact == _normalize(name).replace(" ", "") for name in names
    )


def _one_edit(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1 or left == right:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    small, large = sorted((left, right), key=len)
    return any(large[:i] + large[i + 1 :] == small for i in range(len(large)))


def _distinctive_title(text: str) -> bool:
    """Require lexical identity, not just a genre, instrument, tempo or number."""
    text = LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", CATALOGUE.sub("", text)))
    text = _normalize(text)
    text = re.sub(
        r"\b(?:piano|violin|viola|cello|flute|clarinet|horn|keyboard|solo|strings|"
        r"sonata|concerto|symphony|quartet|quintet|trio|no|nr|in|for|and|the|major|minor|"
        r"variations?|waltz|prelude|etude|nocturne|minuet|adagio|allegro|andante|"
        r"romance|romances|intermezzo|scherzo|overture|suite|pieces?|op|orchestra|"
        r"fantasy|fantasia|fantaisie|fantasie|phantasy)\b",
        "",
        text,
    )
    text = re.sub(
        r"피아노|바이올린|비올라|첼로|플루트|협주곡|교향곡|소나타|사중주|오중주|삼중주|"
        r"변주곡|왈츠|전주곡|연습곡|야상곡|미뉴에트|서곡|모음곡|작품|제|번",
        "",
        text,
    )
    return len(re.sub(r"[^a-z가-힣]", "", text)) >= 5


class MusicMatcher:
    def __init__(self, works: Sequence[CanonicalWork]):
        self.works = tuple(works)
        self.composers = tuple(dict.fromkeys(work.composers for work in works))
        self.by_composer = {
            names: tuple(work for work in works if work.composers == names)
            for names in self.composers
        }
        self.by_title = defaultdict(dict)
        for work in works:
            for title in (*work.titles, *work.aliases):
                if _distinctive_title(title) and not _name_matches(
                    title, work.composers
                ):
                    self.by_title[_title_key(title)][work.id] = work

    def _composers(self, text: str | None):
        groups = [
            {names for names in self.composers if _name_matches(part, names)}
            for part in _variants(text or "")
        ]
        recognized = [group for group in groups if group]
        if recognized:
            common = set.intersection(*recognized)
            return common, "conflicting_composers" if not common else ""
        return set(), "composer_unconfirmed"

    def _spelling_candidates(self, text: str | None, catalogues: frozenset[str]):
        if not text or not catalogues:
            return ()
        names = set()
        for part in _variants(text):
            tokens = _normalize(part).split()
            if not tokens or not re.fullmatch(r"[a-z]{7,}", tokens[-1]):
                continue
            for identity in self.composers:
                for name in identity:
                    expected = _normalize(name).split()
                    if (
                        expected
                        and _one_edit(tokens[-1], expected[-1])
                        and (len(tokens) == 1 or tokens[0][0] == expected[0][0])
                    ):
                        names.add(identity)
        if len(names) != 1:
            return ()
        return tuple(
            w.id
            for w in self.by_composer[next(iter(names))]
            if self._catalogue_match(catalogues, w)
        )[:3]

    @staticmethod
    def _catalogue_match(actual: frozenset[str], work: CanonicalWork) -> bool:
        primary = _catalogues(work.catalogue or "")
        known = set(primary)
        roots = {_root(value) for value in primary}
        schemes = {_scheme(value) for value in primary}
        for text in (*work.titles, *work.aliases):
            for value in _catalogues(text):
                specific = {
                    code
                    for code in primary
                    if _root(code) == _root(value) and "no" in code
                }
                if specific and value not in specific:
                    continue
                if not roots or _root(value) in roots or _scheme(value) not in schemes:
                    known.add(value)
        return bool(actual) and actual.issubset(known)

    def match(
        self,
        title: str,
        composer: str | None,
        *,
        catalogue: str | None = None,
        key: str | None = None,
        scoped: bool = False,
    ) -> WorkMatch:
        title = _catalogue_ocr(title)
        catalogue = _catalogue_ocr(catalogue) if catalogue else None
        if catalogue:
            # A generic translated number confirms an explicit code, never its scheme.
            numbers = {re.sub(r"^[a-z]+", "", c) for c in _catalogues(catalogue)}
            catalogue = re.sub(
                r"(?<!\w)작품\s*번호\s*(\d+[a-z]?)(?!\w)",
                lambda m: "" if m[1].lower() in numbers else m[0],
                catalogue,
                flags=re.IGNORECASE,
            )
        actual_catalogues = _catalogues(title + " " + (catalogue or ""))
        if catalogue and (
            not _catalogues(catalogue) or CATALOGUE.sub("", catalogue).strip(" ,;:()")
        ):
            return WorkMatch(None, (), "unsupported_catalogue")
        if any(
            re.match(r"\s*[-–—/,]\s*\d", title[m.end() :])
            or (m[0].lower().startswith("wab") and re.match(r"\.\s*\d", title[m.end() :]))
            for m in CATALOGUE.finditer(title)
        ):
            return WorkMatch(None, (), "complex_catalogue")
        actual_keys = _keys(title) | _keys(key or "")
        if key and not _keys(key):
            return WorkMatch(None, (), "key_requires_review")
        if len(actual_keys) > 1:
            return WorkMatch(None, (), "conflicting_keys")
        identities, reason = self._composers(composer)
        exact = tuple(self.by_title.get(_title_key(title), {}).values())
        identity_reason = None
        if not identities:
            if not (composer or "").strip() and exact:
                pool = exact
                identity_reason = "unique_distinctive_title"
            else:
                candidates = self._spelling_candidates(composer, actual_catalogues)
                return WorkMatch(
                    None,
                    candidates or tuple(w.id for w in exact)[:3],
                    "composer_spelling_candidate" if candidates else reason,
                )
        elif len(identities) > 1:
            pool = tuple(w for w in exact if w.composers in identities)
            if not pool:
                return WorkMatch(None, (), "ambiguous_composer")
            identity_reason = "surname_and_distinctive_title"
        else:
            names = next(iter(identities))
            pool = self.by_composer[names]
            if not actual_catalogues and (
                _normalize(title) in GENERIC_TITLES
                or all(_name_matches(part, names) for part in _variants(title))
            ):
                return WorkMatch(None, (), "insufficient_title")
        supported = []
        title_variants = _titles(title) | (_scoped_titles(title) if scoped else set())
        actual_numbers = _numbers(title)
        actual_genres = _genres(title)
        for work in pool:
            expected_genres = frozenset().union(*(_genres(t) for t in work.titles))
            # PF301008 exposed quintet aliases on the namesake song. An alias
            # or catalogue number cannot supply missing primary quintet identity.
            if "quintet" in actual_genres and "quintet" not in expected_genres:
                continue
            if (
                actual_genres
                and expected_genres
                and not actual_genres.issubset(expected_genres)
            ):
                continue
            expected_numbers = frozenset().union(*(_numbers(t) for t in work.titles))
            if (
                actual_numbers
                and expected_numbers
                and not actual_numbers.issubset(expected_numbers)
            ):
                continue
            expected_keys = frozenset().union(*(_keys(t) for t in work.titles))
            if (
                actual_keys
                and expected_keys
                and not actual_keys.issubset(expected_keys)
            ):
                continue
            if actual_catalogues:
                if not self._catalogue_match(actual_catalogues, work):
                    continue
                # An opera-wide catalogue may also occur on an aria row. A shared
                # catalogue alone must not turn another excerpt into that aria.
                if (
                    re.search(r"\boverture\b|서곡", title, re.IGNORECASE)
                    and not any(
                        re.search(r"\boverture\b|서곡", t, re.IGNORECASE)
                        for t in (*work.titles, *work.aliases)
                    )
                    and not any(
                        title_variants & _titles(t)
                        for t in (*work.titles, *work.aliases)
                    )
                ):
                    continue
                match_reason = "composer_and_catalogue"
            elif any(
                title_variants & _titles(text) for text in (*work.titles, *work.aliases)
            ):
                match_reason = "composer_and_alias"
            else:
                continue
            supported.append((work, identity_reason or match_reason))
        if actual_catalogues and supported:
            pool_ids = {work.id for work in pool}
            # A known name and a different work's number are conflicting evidence.
            # Literal language segments retain counts such as "3 Fantasiestucke".
            # Do not infer scoped parent names for this contradiction check.
            literal_titles = {_title_key(title)}.union(
                *(_titles(part) for part in _variants(title))
            )
            for variant in literal_titles:
                named = [
                    work for work in self.by_title.get(variant, {}).values()
                    if work.id in pool_ids
                ]
                if named and not any(
                    self._catalogue_match(actual_catalogues, work) for work in named
                ):
                    return WorkMatch(None, (), "title_catalogue_conflict")
        if actual_catalogues and len(supported) > 1:
            # Components can carry their parent's catalogue in an alias. Only a
            # unique exact distinctive title may break that catalogue tie.
            exact_ids = {work.id for work in exact}
            named = [(work, reason) for work, reason in supported if work.id in exact_ids]
            if len(named) == 1:
                supported = named
        candidates = tuple(work.id for work, _ in supported)
        if len(candidates) == 1:
            work, reason = supported[0]
            return WorkMatch(
                None if work.requires_review else work.id,
                candidates,
                "catalog_review_required" if work.requires_review else reason,
            )
        return WorkMatch(
            None, candidates[:3], "ambiguous" if candidates else "no_candidate"
        )

    def match_listed_work(self, title: str, composer: str | None) -> WorkMatch:
        """Recognize an explicitly numbered work inside a model movement list."""
        if (
            not _catalogues(_catalogue_ocr(title))
            or not _genres(title)
            or re.match(r"^\s*(?:[IVXLCDM]+|\d+)[.)]\s", title, re.IGNORECASE)
        ):
            return WorkMatch(None, (), "not_explicit_listed_work")
        return self.match(title, composer)
