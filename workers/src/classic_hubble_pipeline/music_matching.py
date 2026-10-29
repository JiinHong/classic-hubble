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

# Keep Hoboken's Roman section distinct from its Arabic work number.
HOBOKEN = re.compile(
    r"\b(?:Hob\.?\s*|H\.\s*)((?=[IVX])X{0,3}(?:IX|IV|V?I{0,3}))\s*[:/]\s*(\d+[a-z]?)\b",
    re.IGNORECASE,
)
# Additional schemes require grounded evidence, not legacy ingestion or import.
CATALOGUE = re.compile(HOBOKEN.pattern + "|" + LEGACY_CATALOGUE.pattern + r"|\b(?:WAB|WWV|FWV|CD|FP|H|G|M)\.?\s*\d+\b", re.IGNORECASE)
LIFESPAN = re.compile(r"\(?\b\d{4}\s*[-–—~]\s*\d{4}\b\)?")
COMPOSER_YEAR = r"(?:[12]\d[0-9oOlI]{2}|[Il]\d{3})"
COMPOSER_BIOGRAPHICAL_DATES = re.compile(
    rf"\(\s*(?:{COMPOSER_YEAR}\s*[-–—~]\s*{COMPOSER_YEAR}|[bB]\.\s*{COMPOSER_YEAR})\s*\)"
)
LATIN_NOTE_KEY = re.compile(
    r"(?<![a-z])(?:in\s*)?([a-g])\s*([-\u2013 ]?(?:flat|sharp)|[b#♭♯])?\s*-?\s*(major|minor|장조|단조)\b",
    re.IGNORECASE,
)
KOREAN_KEY = re.compile(r"(내림|올림)?\s*([가나다라마바사]|[A-Ga-g][b#♭♯]?)\s*(장|단)조")
KOREAN_NOTES = dict(zip("다라마바사가나", "cdefgab"))
# Observed in recital programs and confirmed against bilingual publisher titles.
GERMAN_NOTES = {"es": "eb", "cis": "c#", "fis": "f#", "b": "bb", "h": "b", "g": "g", "f": "f", "as": "ab", "e": "e", "c": "c"}
GERMAN_NOTE_KEY = re.compile(r"(?<!\w)(es|cis|fis|b|h|g|f|as|e|c)\s*-\s*(dur|moll)\b", re.IGNORECASE)
QUALIFIED_STRAUSS_NAMES = {
    "johann strauss i": 1,
    "johann strauss ii": 2,
    "johann strauss jr": 2,
    "johann strauss junior": 2,
    "johann strauss iii": 3,
}
# PF301618 prints this full Korean spelling beside Gaetano Donizetti.
FULL_NAME_TRANSLITERATIONS = {"가에타노도니제티": "gaetano donizetti"}
# Publisher/venue-backed forms; never infer omitted personal names or OCR typos.
VERIFIED_COMPOSER_NAME_FORMS = {
    # https://www.deutsche-biographie.de/sfz68986.html (GND 11861164X)
    "clara schumann": ("Clara Josephine Schumann",),
    # https://searcharchives.bl.uk/catalog/032-002018849
    "ethel smyth": ("Ethel Mary Smyth",),
    # https://s-lib019.lib.uiowa.edu/subjects/3664
    "cecile chaminade": ("Cécile Louise Stéphanie Chaminade",),
    # https://www.loc.gov/item/n82155113/fanny-mendelssohn-hensel-1805-1847/
    "fanny hensel": ("Fanny Mendelssohn-Hensel",),
    # https://guides.loc.gov/schubert
    "franz schubert": ("Franz Peter Schubert",),
    "antonin dvorak": ("안토닌 드보르작",),
    "mikhail ivanovich glinka": ("Mikhail Glinka",),
    # https://www.boosey.de/composer/Pyotr+Tchaikovsky
    # https://www.ballet.org.uk/blog/pyotr-tchaikovsky-the-man-behind-the-music/
    "pyotr ilyich tchaikovsky": ("Peter Ilyich Tchaikovsky", "Pyotr Tchaikovsky"),
    "sergei rachmaninoff": ("Sergei Rachmaninov",),
    # https://www.harmoniamundi.com/wp-content/uploads/pdf/prokofiev-piano-sonatas-2-en.pdf
    # https://repository.sungshin.ac.kr/handle/2025.oak/4229
    "sergei prokofiev": ("Sergey Prokofiev", "세르게이 프로코피에프"),
}
# Source-verified identities only; a bare opus never identifies an arbitrary member.
VERIFIED_NAMED_OPUS_MEMBERS = {
    # https://stainer.co.uk/shop/n49917/
    ("nikolai medtner", "russian round dance", "op58no1"),
}
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
    "preludes",
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
def _variants(text: str, *, composer: bool = False) -> tuple[str, ...]:
    if composer:
        # Ignore only complete year annotations, never repair the actual name.
        text = COMPOSER_BIOGRAPHICAL_DATES.sub("", text)
    text = LIFESPAN.sub("", text)
    # Keep a printed Korean generation suffix attached to the composer's name.
    korean = r"[가-힣]+(?:\s*[가-힣]+)*" + (r"(?:\s*\d+\s*세)?" if composer else "")
    parts = re.findall(korean + r"|[^가-힣]+", text)
    return tuple(
        dict.fromkeys(
            part.strip(" ()[],:;/") for part in parts if part.strip(" ()[],:;/")
        )
    )


@lru_cache(maxsize=80_000)
def _keys(text: str) -> frozenset[str]:
    result = set()
    for note, mode in GERMAN_NOTE_KEY.findall(text):
        result.add(
            GERMAN_NOTES[note.lower()]
            + ":"
            + ("major" if mode.lower() == "dur" else "minor")
        )
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
        modifier = accidental.strip("- \u2013").lower()
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
    values = set()
    for match in CATALOGUE.finditer(text):
        hoboken = HOBOKEN.fullmatch(match.group())
        values.add(
            "hob" + hoboken[1].lower() + hoboken[2].lower()
            if hoboken else _catalogue_key(match.group())
        )
    # A duplicated root plus its explicit member denotes the member, not two works.
    return frozenset(
        v for v in values if not any(w.startswith(v + "no") for w in values)
    )


def _root(value: str) -> str:
    return value.split("no", 1)[0]


def _scheme(value: str) -> str:
    if value.startswith("hob"):
        return "hob"
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
    text = re.sub(r"(?<!\w)0p(?=\.?\s*\d)", "Op", text, flags=re.IGNORECASE)
    return re.sub(r"(?<!\w)op,(?=\s*\d)", "Op.", text, flags=re.IGNORECASE)


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
        # Keep the printed scoring in evidence; only scoped parent lookup may
        # remove the observed piano/hand-count suffix (PF301161).
        piano_parent = re.sub(
            r"\s+for\s+(?:1\s+piano\s+4|2\s+pianos?\s+[48])\s+hands$",
            "", clean, flags=re.IGNORECASE,
        )
        if piano_parent != clean:
            variants.update(_titles(piano_parent))
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
        "romance": r"\bromances?\b",
    }
    return frozenset(
        name
        for name, pattern in patterns.items()
        if re.search(pattern, text, re.IGNORECASE)
    )


@lru_cache(maxsize=80_000)
def _work_instruments(text: str, *, sonata: bool = False, suite: bool = False) -> frozenset[str]:
    pattern = r"\bsuites?\b|모음곡" if suite else (r"\bsonatas?\b|소나타" if sonata else r"\bconcertos?\b|협주곡")
    genre = re.search(pattern, text, re.IGNORECASE)
    if not genre:
        return frozenset()
    phrase = text[:genre.start()]
    following = re.search(r"\bfor\s+(.+)", text[genre.end():], re.IGNORECASE)
    if following:
        phrase += " " + re.split(
            r"\b(?:and|with)\s+(?:the\s+)?(?:string\s+)?orchestra\b",
            following[1], flags=re.IGNORECASE,
        )[0]
    patterns = {
        "piano": r"\bpianos?\b|피아노",
        "violin": r"\bviolins?\b|바이올린",
        "viola": r"\bviolas?\b|비올라",
        "cello": r"\b(?:cello|celli|cellos|violoncello|violoncelli)\b|첼로",
        "flute": r"\bflutes?\b|플루트",
        "clarinet": r"\bclarinets?\b|클라리넷",
        "oboe": r"\boboes?\b|오보에",
        "bassoon": r"\bbassoons?\b|바순",
        "horn": r"\bhorns?\b|호른",
        "trumpet": r"\btrumpets?\b|트럼펫",
        "harp": r"\bharps?\b|하프",
    }
    if sonata or suite:
        patterns["saxophone"] = r"\b(?:saxophones?|sax)\b|색소폰|색서폰|삭소폰"
    instruments = frozenset(
        name for name, pattern in patterns.items()
        if re.search(pattern, phrase, re.IGNORECASE)
    )
    # Chamber titles often omit piano accompaniment; it cannot identify the soloist.
    return instruments - {"piano"} if (sonata or suite) and len(instruments) > 1 else instruments


def _concerto_instruments(text: str) -> frozenset[str]:
    return _work_instruments(text)


@lru_cache(maxsize=80_000)
def _name_matches(actual: str, names: tuple[str, ...]) -> bool:
    names = names + tuple(
        form for name in names
        for form in VERIFIED_COMPOSER_NAME_FORMS.get(_normalize(name), ())
    )
    alias = FULL_NAME_TRANSLITERATIONS.get(_normalize(actual).replace(" ", ""))
    if alias is not None and any(_normalize(name) == alias for name in names):
        return True
    # Generation is identity evidence, not an initial that may expand I to II.
    qualified = _normalize(actual)
    if re.fullmatch(r"j strauss (?:i{1,3}|jr|junior)", qualified):
        qualified = "johann " + qualified[2:]
    generation = QUALIFIED_STRAUSS_NAMES.get(qualified)
    if generation is not None:
        return any(
            QUALIFIED_STRAUSS_NAMES.get(_normalize(name)) == generation
            for name in names
        )
    if _composer_matches(actual, names):
        return True
    abbreviation = re.fullmatch(r"([A-Za-z]{2})\.\s*([A-Za-z]+)", actual.strip())
    if abbreviation:
        prefix, surname = (part.lower() for part in abbreviation.groups())
        for name in names:
            expected = _normalize(name).split()
            # Ch. Gounod is explicit abbreviation evidence; bare Ch is not.
            if len(expected) == 2 and expected[0].startswith(prefix) and surname == expected[1]:
                return True
    tokens = _normalize(actual).split()
    if len(tokens) >= 2 and all(re.fullmatch(r"[a-z]+", t) for t in tokens):
        for name in names:
            expected = _normalize(name).split()
            # C. v. Weber omits Maria; its initial must refer to Carl, not Maria.
            if (len(tokens) == 3 and len(expected) == 4
                    and expected[2] in {"de", "van", "von"}
                    and (len(tokens[0]) == 1 or tokens[0] == expected[0])):
                if _composer_matches(actual, (" ".join((expected[0], *expected[2:])),)):
                    return True
                continue
            # Observed P. Sarasate, L. Beethoven and F. Suppe omit a particle.
            if len(tokens) == 2 and len(expected) == 3 and expected[1] in {"de", "van", "von"}:
                if _composer_matches(actual, (f"{expected[0]} {expected[2]}",)):
                    return True
            if len(expected) > len(tokens) and tokens[-1] == expected[-1]:
                if _composer_matches(actual, (" ".join(expected[-len(tokens) :]),)):
                    return True
    compact = _normalize(actual).replace(" ", "")
    return bool(re.fullmatch(r"[가-힣]+(?:\d+세)?", compact)) and any(
        compact == _normalize(name).replace(" ", "") for name in names
    )


def _one_edit(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1 or left == right:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    small, large = sorted((left, right), key=len)
    return any(large[:i] + large[i + 1 :] == small for i in range(len(large)))


def _bare_movement_label(text: str) -> bool:
    text = _normalize(LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", text)))
    return bool(re.fullmatch(
        r"(?:(?:[ivxlcdm]+|\d+)\s+)?(?:allegro con brio|finale)", text,
    ))


def _distinctive_title(text: str) -> bool:
    """Require lexical identity, not just a genre, instrument, tempo or number."""
    if _bare_movement_label(text):
        return False
    if _normalize(text) == "ensemble":
        return False
    if re.fullmatch(r"part\s+(?:[ivxlcdm]+|\d+)", _normalize(text)):
        return False
    text = LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", CATALOGUE.sub("", text)))
    text = _normalize(text)
    text = re.sub(
        r"\b(?:piano|violin|viola|cello|flute|clarinet|horn|keyboard|solo|strings|chamber|"
        r"sonata|concerto|symphony|quartet|quintet|trio|no|nr|in|for|and|the|major|minor|"
        r"variations?|waltz|preludes?|etude|nocturne|minuet|adagio|allegro|andante|"
        r"lento|largo|semplice|moderato|allegretto|grazioso|con|moto|rondo|ma|non|troppo|"
        r"romance|romances|intermezzo|scherzo|polonaises?|overture|suite|pieces?|op|orchestra|"
        r"fantasy|fantasia|fantaisie|fantasie|phantasy)\b",
        "",
        text,
    )
    text = re.sub(
        r"피아노|바이올린|비올라|첼로|플루트|협주곡|교향곡|소나타|사중주|오중주|삼중주|"
        r"변주곡|왈츠|전주곡|연습곡|야상곡|미뉴에트|폴로네즈|서곡|모음곡|작품|제|번",
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
        # Keep the observed Korean compound surname intact; titles stay literal.
        text = re.sub(
            r"[가-힣]+(?:\s*-\s*[가-힣]+)+",
            lambda match: re.sub(r"[\s-]", "", match[0]),
            text or "",
        )
        groups = [
            {names for names in self.composers if _name_matches(part, names)}
            for part in _variants(text, composer=True)
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
    def _catalogue_match(
        actual: frozenset[str], work: CanonicalWork, *,
        title: str | None = None, keys: frozenset[str] = frozenset(),
    ) -> bool:
        # A missing catalogue column must not let an alias widen a numbered
        # component's primary title into the entire collection (PF253175).
        primary = _catalogues(work.catalogue or "") or _catalogues(" ".join(work.titles))
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
        if actual and actual.issubset(known):
            return True
        if not title or len(actual) != 1 or len(primary) != 1:
            return False
        root = next(iter(actual))
        if not re.fullmatch(r"op\d+", root) or not re.fullmatch(root + r"no\d+", next(iter(primary))):
            return False
        # A publisher-verified name may supply an omitted member number, but
        # only with the same canonical composer, primary name and specific code.
        name = _title_key(CATALOGUE.sub("", title))
        if (
            not keys
            and all(_catalogues(t).issubset(primary) for t in work.titles)
            and any(
                (_normalize(composer), name, next(iter(primary))) in VERIFIED_NAMED_OPUS_MEMBERS
                for composer in work.composers
            )
            and any(name == _title_key(CATALOGUE.sub("", t)) for t in work.titles)
        ):
            return True
        # Op.120 alone is a collection. A numbered sonata needs its complete
        # primary title and explicit matching key before using that root code.
        if len(keys) != 1:
            return False
        numbers = _numbers(title)
        member = next(iter(primary))
        if numbers == frozenset({int(member.split("no")[1])}):
            # No.1, Op.37 is a member only when its complete
            # primary name and key agree, not a general catalogue rewrite.
            def member_identity(text):
                text = CATALOGUE.sub(
                    lambda m: "No " + member.split("no")[1]
                    if _catalogue_key(m[0]) == member else "", text,
                )
                return _title_key(LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", text)))

            if any(
                _catalogues(t) == primary and _keys(t) == keys
                and member_identity(t) == member_identity(title)
                for t in work.titles
            ):
                return True
        if len(numbers) != 1 or _genres(title) != frozenset({"sonata"}):
            return False

        def identity(text):
            return _title_key(LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", CATALOGUE.sub("", text))))

        return any(
            _numbers(t) == numbers and _keys(t) == keys and identity(t) == identity(title)
            for t in work.titles
        )

    def match(
        self,
        title: str,
        composer: str | None,
        *,
        catalogue: str | None = None,
        key: str | None = None,
        scoped: bool = False,
    ) -> WorkMatch:
        prefix, separator, body = title.partition(" - ")
        # Some grounded OCR titles repeat the separately supplied composer.
        if separator and body.strip() and composer and _normalize(prefix) == _normalize(composer):
            title = body.strip()
        title = _catalogue_ocr(title)
        catalogue = _catalogue_ocr(catalogue) if catalogue else None
        if not catalogue and not _catalogues(title):
            # Preserve the literal Korean number without guessing its scheme.
            trailing = re.search(r"(?<!\S)(작품\s*(?:번호\s*)?\d+)\s*$", title)
            if trailing and len(re.findall(r"작품\s*(?:번호\s*)?\d+", title)) == 1:
                catalogue = trailing[1]
        untyped = re.fullmatch(r"작품\s*(?:번호\s*)?(\d+)", (catalogue or "").strip())
        if untyped:
            # The Korean label does not imply Opus (PF284828 also uses it for K364).
            # Identify by composer/title first; the number is only a constraint.
            identities, _ = self._composers(composer)
            embedded = re.compile(r"작품\s*(?:번호\s*)?(\d+)(?![0-9A-Za-z./])")
            if len(identities) != 1 or any(int(m[1]) != int(untyped[1]) for m in embedded.finditer(title)):
                return WorkMatch(None, (), "unsupported_catalogue")
            clean = embedded.sub("", title).strip()
            named = _distinctive_title(clean) or bool(_genres(clean) and _numbers(clean))
            short_korean = re.fullmatch(r"[가-힣]{2,4}", re.sub(r"\s", "", clean))
            if _catalogues(clean) or not (named or short_korean):
                return WorkMatch(None, (), "unsupported_catalogue")
            matched = self.match(clean, composer, key=key, scoped=scoped)
            if len(matched.candidate_ids) != 1:
                return WorkMatch(None, (), "unsupported_catalogue")
            work = next(w for w in self.by_composer[next(iter(identities))] if w.id == matched.candidate_ids[0])
            # The selected work must own both the short translation and a named title.
            if not named and not (
                any(_title_key(clean) == _title_key(t) for t in work.titles)
                and any(_distinctive_title(t) for t in work.titles)
            ):
                return WorkMatch(None, (), "unsupported_catalogue")
            primary = work.catalogue or ""
            codes = _catalogues(primary)
            code = re.fullmatch(r"[a-z]+(\d+)", next(iter(codes))) if len(codes) == 1 else None
            if not CATALOGUE.fullmatch(primary.strip()) or not code or int(code[1]) != int(untyped[1]):
                return WorkMatch(None, (), "unsupported_catalogue")
            return matched
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
        if re.search(r"\bHob(?=\b|[IVX])|\bH\.\s*[IVX]", HOBOKEN.sub("", title), re.IGNORECASE):
            return WorkMatch(None, (), "unsupported_catalogue")
        if catalogue and (
            not _catalogues(catalogue) or CATALOGUE.sub("", catalogue).strip(" ,;:()")
        ):
            return WorkMatch(None, (), "unsupported_catalogue")
        if any(
            re.match(r"\s*[-–—/,]\s*\d", title[m.end() :])
            or (_scheme(_catalogue_key(m[0])) in {"wab", "fwv", "cd", "fp", "h", "g", "m"} and re.match(r"\.\s*\d", title[m.end() :]))
            or (_scheme(_catalogue_key(m[0])) == "h" and re.match(r"\s+[A-Za-z]\b", title[m.end() :]))
            or (HOBOKEN.fullmatch(m[0]) and re.match(r"\s*[.:]\s*\d", title[m.end() :]))
            for m in CATALOGUE.finditer(title)
        ):
            return WorkMatch(None, (), "complex_catalogue")
        if not actual_catalogues and _bare_movement_label(title):
            return WorkMatch(None, (), "insufficient_title")
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
            # A composer-specific catalogue can resolve a family surname (Bach
            # + BWV). Generic opus numbers cannot. All title/key guards below
            # still apply, and multiple matching works still remain ambiguous.
            named_title = re.search(r"[a-z가-힣]", _normalize(
                LATIN_NOTE_KEY.sub("", KOREAN_KEY.sub("", CATALOGUE.sub("", title)))
            ))
            specific_catalogue = named_title and actual_catalogues and all(
                _scheme(code) not in {"op", "woo"} for code in actual_catalogues
            )
            pool = tuple(
                w for names in identities for w in self.by_composer[names]
            ) if specific_catalogue else tuple(w for w in exact if w.composers in identities)
            if not pool:
                return WorkMatch(None, (), "ambiguous_composer")
            identity_reason = None if specific_catalogue else "surname_and_distinctive_title"
        else:
            names = next(iter(identities))
            pool = self.by_composer[names]
            if not actual_catalogues and (
                _normalize(title) in GENERIC_TITLES
                or all(_name_matches(part, names) for part in _variants(title))
            ):
                return WorkMatch(None, (), "insufficient_title")
        supported = []
        number_conflict = False
        title_variants = _titles(title) | (_scoped_titles(title) if scoped else set())
        actual_numbers = _numbers(title)
        actual_genres = _genres(title)
        actual_instruments = _concerto_instruments(title)
        sonata_instruments = _work_instruments(title, sonata=True) if not scoped else frozenset()
        suite_instruments = _work_instruments(title, suite=True) if not scoped else frozenset()

        def catalogue_matches(work):
            return self._catalogue_match(
                actual_catalogues, work,
                title=title if len(identities) == 1 and not scoped else None,
                keys=actual_keys,
            )

        for work in pool:
            # A catalogue match cannot change an explicitly named solo instrument.
            # Primary titles, not possibly misleading aliases, supply this guard.
            expected_instruments = frozenset().union(
                *(_concerto_instruments(t) for t in work.titles)
            )
            if (
                actual_instruments and expected_instruments
                and not actual_instruments.issubset(expected_instruments)
            ):
                continue
            expected_sonata_instruments = frozenset().union(
                *(_work_instruments(t, sonata=True) for t in work.titles)
            )
            if (
                sonata_instruments and expected_sonata_instruments
                and not sonata_instruments.issubset(expected_sonata_instruments)
            ):
                continue
            expected_suite_instruments = frozenset().union(
                *(_work_instruments(t, suite=True) for t in work.titles)
            )
            if (
                suite_instruments and expected_suite_instruments
                and not suite_instruments.issubset(expected_suite_instruments)
            ):
                continue
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
                if identities and actual_catalogues and catalogue_matches(work):
                    number_conflict = True
                continue
            expected_keys = frozenset().union(*(_keys(t) for t in work.titles))
            if (
                actual_keys
                and expected_keys
                and not actual_keys.issubset(expected_keys)
            ):
                continue
            if actual_catalogues:
                if not catalogue_matches(work):
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
                primary_named = [
                    work for work in self.by_title.get(variant, {}).values()
                    if not work.requires_review
                    and any(_title_key(t) == variant for t in work.titles)
                    and actual_catalogues.issubset(_catalogues(work.catalogue or ""))
                ]
                # Both primary title and catalogue must identify the foreign work;
                # a title alone (e.g. Requiem) cannot assert exclusive ownership.
                if identities and primary_named and not any(
                    work.composers in identities for work in primary_named
                ):
                    return WorkMatch(None, (), "title_composer_conflict")
                named = [
                    work for work in self.by_title.get(variant, {}).values()
                    if work.id in pool_ids
                ]
                if named and not any(
                    catalogue_matches(work) for work in named
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
        if not candidates and number_conflict:
            return WorkMatch(None, (), "title_number_conflict")
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
