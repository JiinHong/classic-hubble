"""Source-backed album work names, separate from recording/track titles."""

import re
from collections import defaultdict

from .work_catalog import catalogue_code, identity
from .work_matching import CATALOGUE, EXCERPT, CanonicalWork, work_details_conflict
from .worklist_names import Document, _conflicts


def observed_name(title):
    """Keep the observed name, not editorial nicknames or secondary catalogue IDs."""
    primary = title.split(" · ")[0]
    return re.split(r",\s*(?=[A-Z][A-Za-z. ]{0,12}\s*\d)", primary, maxsplit=1)[
        0
    ].strip()


def _headers(html, locale):
    rows = defaultdict(set)
    for node in Document(html).root.descendants("div"):
        if node.attrs.get("data-testid") != "work-header":
            continue
        links = list(node.descendants("a"))
        works = [
            a
            for a in links
            if re.fullmatch(rf"/{locale}/work/[a-z0-9-]+", a.attrs.get("href", ""))
        ]
        artists = [
            a
            for a in links
            if re.fullmatch(rf"/{locale}/artist/\d+", a.attrs.get("href", ""))
        ]
        if len(works) != 1 or len(artists) != 1:
            continue
        work, artist = works[0], artists[0]
        rows[work.attrs["href"].rsplit("/", 1)[1]].add(
            (
                " ".join(work.text().split()),
                " ".join(artist.text().split()),
                artist.attrs["href"].rsplit("/", 1)[1],
            )
        )
    return {key: next(iter(values)) for key, values in rows.items() if len(values) == 1}


def pair_album_names(korean_html, english_html):
    korean, english = _headers(korean_html, "kr"), _headers(english_html, "us")
    rows = []
    for key in sorted(korean.keys() & english.keys()):
        ko, composer_ko, artist_ko = korean[key]
        en, composer, artist_en = english[key]
        if artist_ko != artist_en or not re.search("[가-힣]", ko):
            continue
        rows.append(
            {
                "work_key": key,
                "title_ko": ko,
                "title_en": en,
                "composer": composer,
                "composer_ko": composer_ko,
            }
        )
    return rows


def match_recording_name(row, works):
    ko, en = row["title_ko"].split(" · ")[0], row["title_en"].split(" · ")[0]
    if EXCERPT.search(ko + " " + en) or re.search(r"\d\s*[-–]\s*\d", en):
        return None
    codes = {catalogue_code(m.group()) for m in CATALOGUE.finditer(en)}
    codes.discard(None)
    korean_codes = {catalogue_code(m.group()) for m in CATALOGUE.finditer(ko)}
    if korean_codes != codes:
        return None
    candidates = [
        w
        for w in works
        if w.get("catalogue") in codes
        and identity(w["composer"]) == identity(row["composer"])
    ]
    # Duplicate canonical identities are a review case, even if one title looks closer.
    if len(candidates) != 1:
        return None
    work = candidates[0]
    title_codes = {catalogue_code(m.group()) for m in CATALOGUE.finditer(work["title"])}
    if title_codes and work["catalogue"] not in title_codes:
        return None
    if EXCERPT.search(work["title"]) or _conflicts(ko, work):
        return None
    if _conflicts(ko, {**work, "title": en}):
        return None
    expected = CanonicalWork(
        work["id"], "", (CATALOGUE.sub("", work["title"]),), (), work["catalogue"]
    )
    if work_details_conflict(en, expected):
        return None
    # A shared parent catalogue number does not identify a movement or arrangement.
    forms = r"\b(sonata|suite|sarabande|allemande|courante|gigue|prelude|fugue|concerto|symphony|quartet|quintet|trio|sextet|mass|cantata|variation|etude|minuet)s?\b"
    actual_forms = set(re.findall(forms, identity(en.split(" · ")[0])))
    expected_forms = set(re.findall(forms, identity(work["title"])))
    if actual_forms and expected_forms and actual_forms != expected_forms:
        return None
    for korean, english in (
        ("소나타", "sonata"),
        ("협주곡", "concerto"),
        ("교향곡", "symphony"),
        ("모음곡", "suite"),
        ("왈츠", "waltz"),
        ("론도", "rondo"),
        ("야상곡", "nocturne"),
        ("마주르카", "mazurka"),
    ):
        if korean in ko and not re.search(
            r"\b" + english + r"(?:s|es)?\b", identity(en)
        ):
            return None
    return work["id"]
