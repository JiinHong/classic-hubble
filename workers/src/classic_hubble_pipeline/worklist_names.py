"""Extract source-observed list titles for conservative, reviewable catalog matching."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .korean_title_forms import FORMS
from .wikipedia_work_names import LICENSE
from .work_catalog import catalogue_code
from .work_matching import CATALOGUE, EXCERPT, CanonicalWork, work_details_conflict


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def text(self):
        if self.tag in {"sup", "style", "script", "ul", "ol", "table"}:
            return ""
        if self.tag == "br":
            return " "
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def descendants(self, tag):
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    yield child
                yield from child.descendants(tag)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"br", "img", "hr", "input", "link", "meta", "wbr", "source"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _plain(node):
    return " ".join(node.text().split()).strip()


def _catalogue_text(text):
    text = re.sub(
        r"작품번호\s*(\d+[a-z]?)(?:의\s*(\d+[a-z]?))?(?![\w])",
        lambda m: f"Op. {m[1]}" + (f" No. {m[2]}" if m[2] else ""),
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"(\bOp\.?\s*\d+[a-z]?)\s*,\s*(\d+)번(?![\w])",
        r"\1 No. \2",
        text,
        flags=re.IGNORECASE,
    )


def _list_items(node, context=""):
    if node.tag == "li":
        yield node, context
        heading = re.sub(r"\s*\(\d+곡\)$", "", _plain(node))
        genres = {ko for _, ko, _ in FORMS} | {"녹턴", "야상곡", "뱃노래", "바르카롤"}
        context = _plain(node) if heading in genres else ""
    for child in node.children:
        if isinstance(child, Node):
            yield from _list_items(child, context)


def _text_row(raw, context=""):
    text = _catalogue_text(raw)
    matches = list(CATALOGUE.finditer(text))
    if len(matches) != 1:
        return None
    match = matches[0]
    # A slash in a Koechel list is often a revised catalogue number, not a part.
    if re.match(r"\s*[-–—/,]\s*\d", text[match.end() :]) or (
        match.group().lower().startswith(("k.", "kv")) and "/" in match.group()
    ):
        return None
    before, after = text[: match.start()].strip(" ,"), text[match.end() :].strip(" ,")
    if not before:
        title = re.sub(r"\s*\(\d{4}[^)]*\)\s*$", "", after).strip()
    elif not after or re.fullmatch(r"\(\d{4}[^)]*\)", after):
        title = before
    else:
        return None
    evidence = [raw]
    if context and re.match(r"(?:제\s*)?\d+번", title):
        title = re.sub(r"\s*\(\d+곡\)$", "", context) + " " + title
        evidence.insert(0, context)
    code = catalogue_code(match.group())
    if code and re.search("[가-힣]", title) and len(title) < 140:
        return {"code": code, "title": title, "evidence": evidence}
    return None


def extract_rows(html):
    root = Document(html).root
    rows = []
    for table in root.descendants("table"):
        if "wikitable" not in table.attrs.get("class", "").split():
            continue
        header = None
        for tr in table.descendants("tr"):
            cells = [
                c for c in tr.children if isinstance(c, Node) and c.tag in {"th", "td"}
            ]
            values = [_plain(c) for c in cells]
            if cells and all(c.tag == "th" for c in cells):
                header = values
                continue
            if not header or len(values) != len(header):
                continue
            if any(
                c.attrs.get("rowspan", "1") != "1" or c.attrs.get("colspan", "1") != "1"
                for c in cells
            ):
                continue
            if header in (["곡명", "조성"], ["곡명", "조성", "곡명", "조성"]):
                for index in range(0, len(values), 2):
                    row = _text_row(values[index])
                    if row:
                        rows.append(
                            {
                                **row,
                                "title": values[index],
                                "evidence": values[index : index + 2],
                            }
                        )
                continue
            if header[:2] == ["번호", "제목, 조성"]:
                code, title = catalogue_code(values[0]), values[1]
            elif header[:2] == ["HWV", "제목"]:
                code, title = catalogue_code(values[0], "hwv"), values[1]
            elif header[:4] == ["K1", "K6", "작품", "작품(한글명)"]:
                code, title = catalogue_code(values[0], "k"), values[3]
            else:
                continue
            if code and re.search("[가-힣]", title):
                rows.append({"code": code, "title": title, "evidence": values[:4]})
    for li, context in _list_items(root):
        row = _text_row(_plain(li), context)
        if row:
            rows.append(row)
    return rows


def _conflicts(title, work):
    if (
        EXCERPT.search(title)
        or EXCERPT.search(work["title"])
        or re.match(r"(?:제\s*)?\d+번", title)
        or re.fullmatch(
            r"\s*(?:내림|올림)?\s*[가나다라마바사]\s*(?:장조|단조)\s*", title
        )
        or title.count("(") != title.count(")")
    ):
        return True
    # Compare explicit ordinals and keys across the two languages, without translating names.
    comparable = re.sub(r"(?:제\s*)?(\d+)번", r"No. \1", _catalogue_text(title))
    comparable = re.sub(
        r"([A-Ga-g](?:[- ]?(?:flat|sharp)|[#♭♯])?)\s*(장조|단조)",
        lambda m: "in " + m[1] + (" major" if m[2] == "장조" else " minor"),
        comparable,
    )
    comparable = (
        comparable.replace("♭", "-flat").replace("♯", "-sharp").replace("#", "-sharp")
    )
    notes = dict(zip("가나다라마바사", "ABCDEFG", strict=True))
    comparable = re.sub(
        r"(?<![가-힣])(?:(내림|올림)\s*)?([가나다라마바사])\s*(장조|단조)",
        lambda m: (
            "in "
            + notes[m[2]]
            + {None: "", "내림": "-flat", "올림": "-sharp"}[m[1]]
            + (" major" if m[3] == "장조" else " minor")
        ),
        comparable,
    )
    expected = CanonicalWork(
        work["id"], "", (CATALOGUE.sub("", work["title"]),), (), work.get("catalogue")
    )
    if work_details_conflict(comparable, expected):
        return True
    for english, korean in (
        ("trio", "삼중주"),
        ("quartet", "사중주"),
        ("quintet", "오중주"),
        ("sextet", "육중주"),
    ):
        if korean in title and any(
            other in work["title"].lower()
            for other in ("trio", "quartet", "quintet", "sextet")
            if other != english
        ):
            return True
    counts = (
        ("two", "두"),
        ("three", "세"),
        ("four", "네"),
        ("five", "다섯"),
        ("six", "여섯"),
        ("seven", "일곱"),
    )
    actual_count = next(
        (n for n, (_, ko) in enumerate(counts, 2) if re.match(ko + r"\s", title)), None
    )
    expected_count = next(
        (
            n
            for n, (en, _) in enumerate(counts, 2)
            if work["title"].lower().startswith(en + " ")
        ),
        None,
    )
    if actual_count and expected_count and actual_count != expected_count:
        return True
    forms = [(en.lower(), ko) for en, ko, _ in FORMS]
    normalize = lambda s: (
        s.replace("3중주", "삼중주")
        .replace("4중주", "사중주")
        .replace("5중주", "오중주")
    )
    actual_forms = {en for en, ko in forms if ko in normalize(title)}
    expected_forms = {en for en, _ in forms if en in work["title"].lower()}
    return bool(actual_forms and expected_forms and actual_forms != expected_forms)


def match_rows(rows, composer_id, works):
    index = defaultdict(list)
    for work in works:
        if work["composer_id"] == composer_id and work.get("catalogue"):
            code = catalogue_code(work["catalogue"])
            if code:
                index[code].append(work)
    titles = defaultdict(set)
    for row in rows:
        titles[row["code"]].add(row["title"])
    accepted, rejected = [], []
    for row in rows:
        matches = index[row["code"]]
        reason = None
        if len(titles[row["code"]]) != 1:
            reason = "conflicting_source_rows"
        elif len(matches) != 1:
            reason = "missing_or_ambiguous_catalogue"
        elif any(
            code.split()[0] == row["code"].split()[0] and code != row["code"]
            for match in CATALOGUE.finditer(matches[0]["title"])
            if (code := catalogue_code(match.group()))
        ):
            reason = "canonical_title_catalogue_conflict"
        elif _conflicts(row["title"], matches[0]):
            reason = "scope_number_or_key_conflict"
        if reason:
            rejected.append({**row, "reason": reason})
        else:
            accepted.append({**row, "work_id": matches[0]["id"]})
    return accepted, rejected


def build_manifest(documents, works, composers, links):
    qids = {link["payload"]["work_id"]: link["provider_id"] for link in links}
    if len(qids) != len(links) or len(set(qids.values())) != len(links):
        raise ValueError("Ambiguous canonical crosswalk")
    work_index = {w["id"]: w for w in works}
    entries, sources, audit = {}, {}, []
    for document in documents:
        matches = [c for c in composers if c["name"] == document["composer"]]
        if len(matches) != 1:
            raise ValueError("Ambiguous composer")
        page = document["parse"]
        source_id = f"kowiki-list-{page['pageid']}"
        rows = extract_rows(page["text"]["*"])
        accepted, rejected = match_rows(rows, matches[0]["id"], works)
        audit.extend({**row, "source": source_id} for row in rejected)
        sources[source_id] = {
            "url": f"https://ko.wikipedia.org/w/index.php?oldid={page['revid']}",
            "kind": "encyclopedia_worklist_names",
            "publisher": "한국어 위키백과 기여자",
            "license": LICENSE,
            "page_id": page["pageid"],
            "revision_id": page["revid"],
            "article_title": page["title"],
            "composer": document["composer"],
        }
        for row in accepted:
            reason = document.get("exclude", {}).get(row["code"])
            if reason:
                audit.append({**row, "source": source_id, "reason": reason})
                continue
            title = document.get("titles", {}).get(row["code"], row["title"])
            if title not in row["title"]:
                raise ValueError("Reviewed title must be an observed substring")
            work = work_index[row["work_id"]]
            qid = qids.get(work["id"])
            if not qid:
                raise ValueError("Missing canonical crosswalk")
            entry = entries.setdefault(
                qid,
                {
                    "qid": qid,
                    "composer": document["composer"],
                    "expected_title": work["title"],
                    "previous_title_ko": work["title_ko"],
                    "title_ko": work["title_ko"] or title,
                    "display_title_origin": "existing"
                    if work["title_ko"]
                    else source_id,
                    "sources": [],
                    "aliases": [],
                    "evidence": [],
                },
            )
            if source_id not in entry["sources"]:
                entry["sources"].append(source_id)
            alias = {
                "text": title,
                "locale": "ko",
                "kind": "title",
                "sources": [source_id],
            }
            if alias not in entry["aliases"]:
                entry["aliases"].append(alias)
            evidence = {
                "code": row["code"],
                "text": row["evidence"],
                "source": source_id,
            }
            if evidence not in entry["evidence"]:
                entry["evidence"].append(evidence)
    return {
        "version": "2026-10-21.worklists.1",
        "origin": "worklist-names",
        "language": "ko",
        "policy": "Observed list names, matched by unique composer and complete catalogue code, with conflicts excluded and a per-row review. Existing display titles are preserved. Source presence is not measured popularity; imported identities remain review-only.",
        "sources": sources,
        "works": sorted(entries.values(), key=lambda e: int(e["qid"][1:])),
    }, audit
