"""Render unambiguous formal titles, distinct from observed Korean nicknames."""

from __future__ import annotations

import re

FORMS = (
    ("Symphony", "교향곡", "Q11985"),
    ("Piano Concerto", "피아노 협주곡", "Q44261"),
    ("Violin Concerto", "바이올린 협주곡", "Q73586"),
    ("Cello Concerto", "첼로 협주곡", "Q162002"),
    ("Violin Sonata", "바이올린 소나타", "Q428956"),
    ("Piano Sonata", "피아노 소나타", "Q12008"),
    ("Cello Sonata", "첼로 소나타", "Q586125"),
    ("String Quartet", "현악 사중주", "Q163616"),
    ("String Quintet", "현악 오중주", "Q1779432"),
    ("Piano Trio", "피아노 삼중주", "Q1134792"),
    ("Piano Quartet", "피아노 사중주", "Q3132812"),
    ("Piano Quintet", "피아노 오중주", "Q210227"),
    ("Clarinet Concerto", "클라리넷 협주곡", "Q1056501"),
    ("Horn Concerto", "호른 협주곡", "Q1063431"),
    ("Bassoon Concerto", "바순 협주곡", "Q1196773"),
    ("Oboe Concerto", "오보에 협주곡", "Q675198"),
    ("Waltz", "왈츠", "Q1527943"),
    ("Polonaise", "폴로네즈", "Q1506063"),
)
TAIL = (
    r"(?: No\.?\s*(?P<number>\d+))?"
    r"(?: in (?P<note>[A-G])(?P<accidental>-flat|-sharp)? (?P<mode>major|minor))?"
    r"(?P<catalogue>(?:,?\s*\(?(?:Op\.|BWV|RV|K\.|D\.|HWV)\s*\d+[a-z]?"
    r"(?:,?\s*No\.\s*\d+)?\)?)?)"
)


def render_title(title):
    for english, korean, _ in FORMS:
        match = re.fullmatch(re.escape(english) + TAIL, title, flags=re.IGNORECASE)
        if not match or not (match["number"] or match["note"]):
            continue
        result = korean
        if match["number"]:
            result += f" {match['number']}번"
        if match["note"]:
            accidental = {"-flat": "♭", "-sharp": "♯", "": ""}[
                (match["accidental"] or "").lower()
            ]
            mode = "장조" if match["mode"].lower() == "major" else "단조"
            result += f" {match['note'].upper()}{accidental}{mode}"
        return result + match["catalogue"]
    return None


def build_manifest(works, composers, links):
    composer_index = {c["id"]: c["name"] for c in composers}
    qids = {link["payload"]["work_id"]: link["provider_id"] for link in links}
    if len(qids) != len(links) or len(set(qids.values())) != len(links):
        raise ValueError("Ambiguous canonical crosswalk")
    sources = {
        f"term-{qid}": {
            "url": f"https://www.wikidata.org/wiki/{qid}",
            "kind": "bilingual_term_example",
            "english": english,
            "korean": korean,
            "scope": "Genre term only, not evidence that every generated work title was observed.",
        }
        for english, korean, qid in FORMS
    }
    entries = []
    for work in works:
        qid = qids.get(work["id"])
        rendered = render_title(work["title"])
        if not qid or not rendered:
            continue
        term_qid = next(
            q for e, _, q in FORMS if work["title"].lower().startswith(e.lower())
        )
        source_id = f"work-{qid}"
        sources[source_id] = {
            "url": f"https://www.wikidata.org/wiki/{qid}",
            "kind": "formal_title_input",
            "input_title": work["title"],
            "method": "Translate supported genre, ordinal and key only; retain catalogue suffix. No nickname inference.",
        }
        evidence = [source_id, f"term-{term_qid}"]
        entries.append(
            {
                "qid": qid,
                "composer": composer_index[work["composer_id"]],
                "expected_title": work["title"],
                "previous_title_ko": work["title_ko"],
                "title_ko": work["title_ko"] or rendered,
                "display_title_origin": "existing"
                if work["title_ko"]
                else "formal-rendering",
                "sources": evidence,
                "aliases": [{"text": rendered, "kind": "title", "sources": evidence}],
            }
        )
    return {
        "version": "2026-10-21.forms.1",
        "origin": "formal-rendering",
        "policy": "Deterministic formal Korean rendering, not observed usage or identity verification. Preserve reviewed names; do not translate programmatic titles or infer nicknames.",
        "sources": sources,
        "works": sorted(entries, key=lambda e: int(e["qid"][1:])),
    }
