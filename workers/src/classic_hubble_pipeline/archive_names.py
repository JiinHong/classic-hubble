"""Read public bilingual KBS archive labels without requesting video media."""

import re
from urllib.parse import urljoin, urlsplit

from .work_matching import CATALOGUE, EXCERPT, WORK_NUMBER
from .worklist_names import Document, _conflicts

ARCHIVE_URL = "https://digitalkhall.kbssymphony.org/renew/concert/digital_view.html?cno=405&mode=PLAY"


def archive_name_conflict(row, work):
    ko, en = row["title_ko"], row["title_en"]
    if EXCERPT.search(ko + " " + en) or re.search(
        r"\b(?:from|mov|arranged|excerpts?|version)\b|중\s*제?\d|버전|[-–—‘'\"]\s*[IVXLCDM]+\.",
        ko + " " + en,
        re.IGNORECASE,
    ):
        return True
    for word in ("sarabande", "allemande", "courante", "gigue", "overture", "suite"):
        if re.search(r"\b" + word + r"\b", en, re.IGNORECASE) and not re.search(
            r"\b" + word + r"\b", work["title"], re.IGNORECASE
        ):
            return True
    if WORK_NUMBER.search(CATALOGUE.sub("", en)) and not WORK_NUMBER.search(
        CATALOGUE.sub("", work["title"])
    ):
        return True
    codes = list(CATALOGUE.finditer(en))
    numbers = re.findall(r"작품(?:번호)?\s*(\d+[a-z]?)", ko, re.IGNORECASE)
    if numbers and len(codes) == 1:
        number = re.search(r"\d+[a-z]?", codes[0].group(), re.IGNORECASE)[0]
        if any(n.lower() != number.lower() for n in numbers):
            return True
    if "협주곡" in ko and "concerto" in en.lower():
        instruments = (
            ("바이올린", "violin"),
            ("첼로", "cello"),
            ("피아노", "piano"),
            ("플루트", "flute"),
            ("오보에", "oboe"),
            ("호른", "horn"),
            ("클라리넷", "clarinet"),
        )
        actual = {english for korean, english in instruments if korean in ko}
        expected = {
            english
            for _, english in instruments
            if re.search(r"\b" + english + r"\b", en, re.IGNORECASE)
        }
        if actual and expected and actual != expected:
            return True
    return _conflicts(ko, work)


def extract_archive_names(html):
    rows = []
    for anchor in Document(html).root.descendants("a"):
        url = urljoin(ARCHIVE_URL, anchor.attrs.get("href", ""))
        parsed = urlsplit(url)
        if (
            parsed.hostname != "digitalkhall.kbssymphony.org"
            or not parsed.path.endswith("/video_detail.html")
        ):
            continue
        subjects = [
            p
            for p in anchor.descendants("p")
            if "subject" in p.attrs.get("class", "").split()
        ]
        if len(subjects) != 1:
            continue
        subject = subjects[0]
        translations = [
            s
            for s in subject.descendants("span")
            if "subject2" in s.attrs.get("class", "").split()
        ]
        if len(translations) != 1:
            continue
        translation = translations[0]
        ko = " ".join(
            "".join(
                c if isinstance(c, str) else c.text()
                for c in subject.children
                if c is not translation
            ).split()
        )
        en = " ".join(translation.text().split())
        if "/" not in ko or "/" not in en:
            continue
        composer_ko, title_ko = (s.strip() for s in ko.split("/", 1))
        composer_en, title_en = (s.strip() for s in en.split("/", 1))
        if not all((composer_ko, title_ko, composer_en, title_en)):
            continue
        dates = [
            p
            for p in anchor.descendants("p")
            if "date" in p.attrs.get("class", "").split()
        ]
        rows.append(
            {
                "url": url,
                "composer_ko": composer_ko,
                "composer_en": composer_en,
                "title_ko": title_ko,
                "title_en": title_en,
                "date": " ".join(dates[0].text().split()) if dates else None,
            }
        )
    return rows
