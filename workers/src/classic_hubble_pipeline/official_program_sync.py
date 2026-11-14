"""Read bounded public programme sections and link them to existing KOPIS concerts."""

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import json
import re
import time
import unicodedata
from urllib.parse import parse_qs, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .supabase import SupabaseRepository, SupabaseSettings
from .work_matching import _composer_matches
from .worklist_names import Document


HOST = dict(
    sac="www.sac.or.kr",
    sejong="www.sejongpac.or.kr",
    bucheon="www.bucheonphil.or.kr",
    seoulphil="www.seoulphil.or.kr",
)
BAC = "/front/M0000012/event/"
NOTES = "/front/M0000133/article/"
SEJ = "/portal/performance/performance/performTicket.do"
SAC = "/site/main/show/show_view"
CODE = re.compile(r"\b(Op|K|BWV|FP|M)\.?\s*(\d+[a-z]?)\b", re.I)
SCOPE = re.compile(
    r"\b(from|excerpts?|selections?|movement|arranged|arr\.|suite from)\b|악장|발췌|편곡|모음곡 중| 중(?:\s|$)|[:：]\s*[IVX]+\.",
    re.I,
)
KEY = re.compile(
    r"\b([a-g])(?:[- ]?(flat|sharp)|([♭♯#]))?\s*(major|minor|장조|단조)", re.I
)


def tonalities(s):
    return {
        (
            letter.lower(),
            {"♭": "flat", "♯": "sharp", "#": "sharp"}.get(symbol, acc.lower()),
            {"장조": "major", "단조": "minor"}.get(mode, mode.lower()),
        )
        for letter, acc, symbol, mode in KEY.findall(s)
    }


def plain(node):
    return " ".join(node.text().split())


def compact(text):
    return "".join(
        c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum()
    )


@dataclass
class Event:
    title: str
    day: str
    hall: str
    clock: str
    pairs: list


def program_pairs(lines):
    out, credit, active = [], "", False
    for s in lines:
        s = s.strip()
        if re.fullmatch(r"[\[【]?\s*(프로그램|program(?:me)?)\s*[\]】]?", s, re.I):
            active = True
            continue
        if not active:
            continue
        if re.search(
            r"\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}월\s*\d{1,2}일|^\s*[IVX]+\.\s|공연\s*취소",
            s,
        ):
            return []
        if re.search(
            r"^※|^\*\s*프로그램|이력|프로필|profile|biograph|^소개$|공연해설|^출연|^\[(?!프로그램)",
            s,
            re.I,
        ):
            break
        if not s:
            continue
        person = re.fullmatch(
            r"([A-Za-zÀ-ž가-힣 .'-]+?)\s*\(\d{4}\s*[-~–]\s*\d{4}\)", s
        )
        if person:
            credit = person[1].strip()
            continue
        parts = re.fullmatch(r"([^/|]{2,55}?)\s+[/|]\s+(.+)", s)
        bracket = re.fullmatch(r"(.+?)\s*\(\s*([A-Za-zÀ-ž가-힣 .'-]+)\s*\)", s)
        if parts:
            out.append((parts[1].strip(), parts[2].strip()))
        elif bracket:
            out.append((bracket[2].strip(), bracket[1].strip()))
        elif credit:
            out.append((credit, s))
        elif comma := re.fullmatch(r"([A-Za-zÀ-ž가-힣 .'-]{2,45}),\s+(.+)", s):
            out.append((comma[1], comma[2]))
        credit = ""
    return out


def title_key(s):
    s = re.sub(r"제\s*(\d+)\s*번", r"\1번", s)
    s = re.sub(r"['‘’“”\"(].*?['‘’“”\")]", " ", s)
    s = re.sub(
        r"(?:\bin\s+)?\b[a-g](?:[- ]?(?:flat|sharp)|[♭♯#])?\s*(?:major|minor|장조|단조)",
        " ",
        s,
        flags=re.I,
    )
    return compact(CODE.sub("", s))


def catalogue(s):
    m = CODE.fullmatch(s or "")
    return (m[1].lower(), m[2].lower()) if m else None


def identify(credit, title, works):
    codes = list(CODE.finditer(title))
    if (
        len(codes) != 1
        or len(title) > 180
        or SCOPE.search(title)
        or re.search(r"[()]|피아노판", title)
        or re.match(
            r"\s*(?:[/~–-]\s*\d|,?\s*(?:No|Nr)\.?\s*\d)", title[codes[0].end() :], re.I
        )
    ):
        return None
    key = title_key(title)
    code = catalogue(codes[0][0])
    hits = []
    for w in works:
        c = w["composers"]
        if (
            not _composer_matches(credit, [s for s in (c["name"], c["name_ko"]) if s])
            or catalogue(w["catalogue"]) != code
        ):
            continue
        names = [w["title"], w["title_ko"], *(a["alias"] for a in w["work_aliases"])]
        keys = set().union(*(tonalities(n) for n in names if n))
        if tonalities(title) and keys and tonalities(title) != keys:
            continue
        if key and any(title_key(n) == key for n in names if n):
            hits.append(w)
    return hits[0] if len(hits) == 1 else None


def sejong_id(url):
    u = urlsplit(url)
    q = parse_qs(u.query)
    ids = q.get("performIdx", [])
    if (
        u.scheme in ("https", "http")
        and u.netloc == HOST["sejong"]
        and u.path == SEJ
        and len(ids) == 1
        and re.fullmatch(r"[0-9]+", ids[0])
    ):
        return ids[0]


def serial(s):
    m = re.search(r"제\s*(\d+)회\s*(?:부천필하모닉오케스트라\s*)?정기연주회", s)
    return m[1] if m else None


def same_event(p, e, provider):
    if not e.day or p["starts_on"] != e.day or p["ends_on"] != e.day:
        return False
    hall = compact((p.get("venue_halls") or {}).get("name", ""))
    venue = compact((p.get("venues") or {}).get("name", "").replace(" [서울]", ""))
    clocks = re.findall(r"\b\d{1,2}:\d\d\b", p.get("schedule_text") or "")
    if not hall or compact(e.hall) not in (hall, venue + hall) or clocks != [e.clock]:
        return False
    a, b = map(compact, (p["title"], e.title))
    if provider == "bucheon":
        return bool(
            serial(e.title)
            and serial(e.title) == serial(p["title"])
            and "부천필" in a
            and "부천필" in b
        )
    if provider == "sejong":
        # Discovery already bound the exact official product ID to this KOPIS record.
        return a == b or (len(b) >= 7 and b in a) or (len(a) >= 7 and a in b)
    return a == b


def section(doc, tag, attr, value):
    return next(
        (n for n in doc.descendants(tag) if value in n.attrs.get(attr, "").split()),
        None,
    )


def sac_event(doc):
    meta = {
        n.attrs.get("property"): n.attrs.get("content", "")
        for n in doc.descendants("meta")
    }
    m = re.fullmatch(
        r"(\d{4}-\d\d-\d\d)\([월화수목금토일]\) ~ \1\([월화수목금토일]\) (\d\d:\d\d) (.+)",
        meta.get("og:description", ""),
    )
    blocks = [
        n
        for n in doc.descendants("div")
        if "cwa-text" in n.attrs.get("class", "").split()
        and any(plain(h) == "공연·전시 상세 정보" for h in n.descendants("h2"))
    ]
    if m and blocks:
        return Event(
            meta.get("og:title", ""),
            m[1],
            m[3],
            m[2],
            program_pairs([plain(p) for p in blocks[-1].descendants("p")]),
        )


def sejong_event(doc):
    title = section(doc, "p", "class", "tit")
    intro = section(doc, "li", "id", "tabMove2")
    for tr in doc.descendants("tr"):
        cells = [plain(c) for c in tr.descendants("td")]
        if len(cells) != 3 or not title or not intro:
            continue
        d = re.fullmatch(r"기간 (\d{4}\.\d\d\.\d\d)\([월화수목금토일]\)", cells[0])
        t = re.fullmatch(r"시간 (\d\d:\d\d)", cells[2])
        if d and t:
            return Event(
                plain(title),
                d[1].replace(".", "-"),
                cells[1].removeprefix("장소 ").removesuffix(" 위치보기"),
                t[1],
                program_pairs([plain(p) for p in intro.descendants("p")]),
            )


def bucheon_event(doc):
    header = section(doc, "div", "class", "txtWrap")
    if not header:
        return None
    title = next(header.descendants("h4"), None)
    fields = [plain(li) for li in header.descendants("li")]
    day = next(
        (
            re.fullmatch(
                r"일자\s*(\d{4})년\s*(\d+)월\s*(\d+)일\s*\([월화수목금토일]\)\s*(\d\d:\d\d)",
                s,
            )
            for s in fields
            if s.startswith("일자")
        ),
        None,
    )
    place = next(
        (s.removeprefix("장소").strip() for s in fields if s.startswith("장소")), ""
    )
    if title and day and place:
        return Event(
            plain(title),
            date(*map(int, day.groups()[:3])).isoformat(),
            place,
            day[4],
            [],
        )


def note_pairs(doc, number):
    heading = section(doc, "h4", "class", "tit")
    body = section(doc, "div", "class", "viewContent")
    if (
        not heading
        or not body
        or "[부천필]" not in plain(heading)
        or serial(plain(heading)) != number
    ):
        return []
    if not re.search(
        r"부천필하모닉오케스트라\s*제" + number + r"회\s*정기연주회", plain(body)
    ):
        return []
    pairs = []
    for n in body.descendants("strong"):
        credit, sep, title = plain(n).partition(", ")
        if sep and re.fullmatch(r"[가-힣· ]{2,30}", credit):
            pairs.append((credit, title))
    return pairs


class PublicPages:
    """Only fetch known official hosts; no redirects, gated pages, downloads or retries."""

    def __init__(self, client):
        self.client = client
        self.rules = {}
        self.last = {}

    def fetch(self, url):
        host = urlsplit(url).netloc
        if host not in HOST.values() or not url.startswith("https://"):
            raise ValueError("Not an official host")
        if host not in self.rules:
            r = self.client.get("https://" + host + "/robots.txt")
            if r.status_code != 404:
                r.raise_for_status()
            rp = RobotFileParser()
            rp.parse(r.text.splitlines() if r.status_code != 404 else [])
            self.rules[host] = rp
        rp = self.rules[host]
        if not all(
            rp.can_fetch(agent, url) for agent in ("ClassicHubble", "ChatGPT-User")
        ):
            raise PermissionError("robots_disallowed:" + host)
        delay = max(0.4, rp.crawl_delay("ClassicHubble") or 0)
        time.sleep(max(0, self.last.get(host, 0) + delay - time.monotonic()))
        self.last[host] = time.monotonic()
        with self.client.stream("GET", url) as r:
            r.raise_for_status()
            raw = bytearray()
            for chunk in r.iter_bytes():
                raw.extend(chunk)
                if len(raw) > 4_000_000:
                    raise ValueError("Official page exceeds size cap")
        return Document(raw.decode("utf-8-sig")).root


def sac_index(doc):
    for tr in doc.descendants("tr"):
        a = next(tr.descendants("a"), None)
        d = section(tr, "div", "class", "mobile-place")
        title = section(tr, "span", "class", "pc-program-subject")
        if (
            a
            and title
            and d
            and re.fullmatch(
                r"/site/main/show/show_view\?SN=\d+", a.attrs.get("href", "")
            )
        ):
            yield plain(d).replace(".", "-"), compact(plain(title)), a.attrs["href"]


def article_links(doc, key, pattern):
    for a in doc.descendants("a"):
        m = re.fullmatch(
            r"view\.do\?" + key + "=(" + pattern + r")(?:&[^#]*)?",
            a.attrs.get("href", ""),
        )
        if m:
            yield m[1], plain(a)


def source_jobs(provider, targets, pages):
    base = "https://" + HOST[provider]
    if provider == "sejong":
        for p in targets:
            ids = {
                n
                for l in (p["booking_links"] or [])
                if (n := sejong_id(l.get("url", "")))
            }
            if len(ids) == 1:
                yield (
                    p,
                    base + SEJ + "?performIdx=" + ids.pop() + "&menuNo=200320",
                    sejong_event,
                    None,
                )
    elif provider == "sac":
        for year in sorted({p["starts_on"][:4] for p in targets}):
            index = list(
                sac_index(
                    pages.fetch(
                        base
                        + "/site/main/program/schedule_year_ajax?searchYear="
                        + year
                        + "&CATEGORY_PRIMARY="
                    )
                )
            )
            if not index:
                raise ValueError("Empty SAC calendar")
            for p in targets:
                links = {
                    url
                    for day, title, url in index
                    if day == p["starts_on"] and title == compact(p["title"])
                }
                if len(links) == 1:
                    yield p, base + links.pop(), sac_event, None
    elif provider == "bucheon":
        if not targets:
            return
        notes = list(
            article_links(pages.fetch(base + NOTES + "list.do"), "atcId", r"AT\d+")
        )
        shows = list(
            article_links(
                pages.fetch(base + BAC + "list.do?pageIndex=1"), "eventId", r"EV\d+"
            )
        )
        if not shows or not notes:
            raise ValueError("Empty Bucheon schedule or notes listing")
        for p in targets:
            n = serial(p["title"])
            if not n:
                continue
            ns = {i for i, t in notes if serial(t) == n and "[부천필]" in t}
            es = {i for i, t in shows if serial(t) == n and "부천필" in t}
            if len(ns) == len(es) == 1:
                yield (
                    p,
                    base + BAC + "view.do?eventId=" + es.pop(),
                    bucheon_event,
                    base + NOTES + "view.do?atcId=" + ns.pop(),
                )
    elif provider == "seoulphil" and targets:
        home = pages.fetch(base + "/")
        links = {}
        for a in home.descendants("a"):
            u = urlsplit(a.attrs.get("href", ""))
            ids = parse_qs(u.query).get("perfNo", [])
            if (
                u.netloc in ("", HOST[provider])
                and u.path == "/perf/view"
                and len(ids) == 1
                and ids[0].isdigit()
            ):
                links.setdefault(compact(plain(a)), set()).add(ids[0])
        for p in targets:
            matches = {
                i
                for title, ids in links.items()
                if compact(p["title"]) in title
                for i in ids
            }
            if len(matches) == 1:
                yield (
                    p,
                    base + "/perf/view?perfNo=" + matches.pop(),
                    seoulphil_event,
                    None,
                )


def seoulphil_event(doc):
    meta = {
        n.attrs.get("property"): n.attrs.get("content", "")
        for n in doc.descendants("meta")
    }
    title = meta.get("og:title", "").split("|")[0].strip()
    lines = [plain(n) for n in doc.descendants("p")]
    days = [
        m
        for s in lines
        if (
            m := re.fullmatch(
                r"(\d{4})\s*년\s*(\d+)\s*월\s*(\d+)\s*일\s*\([월화수목금토일]\)\s*(오전|오후)\s*(\d+)\s*시\s*(?:(\d+)\s*분)?\s+(.+)",
                s,
            )
        )
    ]
    if len(days) != 1 or not title:
        return None
    d = days[0]
    pairs = []
    active = False
    for s in lines:
        if s.strip() == "프로그램":
            active = True
        elif active and (s.startswith("※") or len(s) > 180):
            break
        elif active and ", " in s:
            composer, work = s.split(", ", 1)
            if re.fullmatch(r"[가-힣A-Za-zÀ-ž .'-]{2,40}", composer):
                pairs.append((composer, work))
    return Event(
        title,
        date(*map(int, d.groups()[:3])).isoformat(),
        d[7],
        f"{int(d[5]) % 12 + 12 * (d[4] == '오후'):02}:{int(d[6] or 0):02}",
        pairs,
    )


FIELDS = "id,title,starts_on,ends_on,kopis_performance_id,venue_id,venue_hall_id,schedule_text,booking_links,venues!inner(name),venue_halls(name)"


def targets_for(repo, provider, start, end, limit, ids):
    params = {
        "select": FIELDS,
        "and": f"(starts_on.gte.{start},starts_on.lte.{end})",
        "kopis_performance_id": "not.is.null",
        "order": "starts_on.asc,id.asc",
        "limit": str(limit),
    }
    if provider in ("sac", "sejong"):
        params["venues.name"] = (
            "eq." + {"sac": "예술의전당 [서울]", "sejong": "세종문화회관"}[provider]
        )
    elif provider == "bucheon":
        params["title"] = "ilike.*부천필*"
    else:
        params["or"] = "(title.ilike.*서울시향*,title.ilike.*서울시립교향악단*)"
    if ids:
        params["kopis_performance_id"] = "in.(" + ",".join(ids) + ")"
    return repo._request("GET", "performances", params=params, prefer="").json()


def run(repo, pages, args):
    @lru_cache(maxsize=1024)
    def works(prefix, number):
        return repo._read_pages(
            "works",
            {
                "select": "id,slug,title,title_ko,composer_id,catalogue,composers(name,name_ko),work_aliases(alias)",
                "catalogue": "ilike." + prefix + "*" + number,
            },
            page_size=200,
        )

    failures = 0
    for provider in args.provider or list(HOST):
        stats = Counter()
        try:
            targets = targets_for(
                repo, provider, args.start, args.end, args.limit, args.kopis
            )
            stats["targets"] = len(targets)
            for p, url, parse, note in source_jobs(provider, targets, pages):
                stats["found"] += 1
                try:
                    event = parse(pages.fetch(url))
                    if not event or not same_event(p, event, provider):
                        stats["identity_held"] += 1
                        continue
                    if note:
                        event.pairs = note_pairs(pages.fetch(note), serial(p["title"]))
                    items = []
                    for ordinal, (c, t) in enumerate(event.pairs, 1):
                        m = CODE.search(t)
                        w = identify(c, t, works(*m.groups())) if m else None
                        if w and all(i["work_id"] != w["id"] for i in items):
                            items.append(
                                dict(
                                    position=ordinal,
                                    work_id=w["id"],
                                    composer_id=w["composer_id"],
                                    catalogue=w["catalogue"],
                                    credit=c,
                                    title=t,
                                )
                            )
                        else:
                            stats["unmatched_lines"] += 1
                    if not items:
                        stats["no_verified_items"] += 1
                        continue
                    evidence = dict(
                        provider=provider,
                        kopis=p["kopis_performance_id"],
                        day=event.day,
                        venue=p["venue_id"],
                        hall=p["venue_hall_id"],
                        hall_name=event.hall,
                        clock=event.clock,
                        schedule=p["schedule_text"],
                        kopis_title=p["title"],
                        official_title=event.title,
                        url=url,
                        source=note or url,
                        version="official-program-v1",
                        program=event.pairs,
                        items=items,
                    )
                    if args.apply:
                        outcome = repo._request(
                            "POST",
                            "rpc/publish_official_venue_program",
                            json={"p_id": p["id"], "doc": evidence},
                            prefer="",
                        ).json()
                    else:
                        outcome = {"status": "candidate", "items": len(items)}
                    stats[outcome["status"]] += 1
                    stats["added_items"] += (
                        outcome["items"] if outcome["status"] == "published" else 0
                    )
                    print(
                        json.dumps(
                            dict(
                                kopis=evidence["kopis"],
                                source=evidence["source"],
                                works=[i["title"] for i in items],
                                **outcome,
                            ),
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                    stats["error"] += 1
                    print(f"{provider} {p['kopis_performance_id']}: {exc}", flush=True)
                    if isinstance(
                        exc, httpx.HTTPStatusError
                    ) and exc.response.status_code in (401, 403, 429):
                        break
        except PermissionError as exc:
            stats["policy_paused"] += 1
            print(str(exc), flush=True)
        except (ValueError, httpx.HTTPError, RuntimeError) as exc:
            stats["error"] += 1
            print(f"{provider}: {exc}", flush=True)
        failures += stats["error"]
        print(provider, json.dumps(stats), flush=True)
    return int(bool(failures))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    p.add_argument("--provider", choices=HOST, action="append")
    p.add_argument("--kopis", action="append")
    p.add_argument("--limit", type=int, default=250)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if (
        not 0 < a.limit <= 500
        or not 0 <= (a.end - a.start).days <= 31
        or any(not re.fullmatch(r"PF\d+", s) for s in a.kopis or [])
    ):
        p.error(
            "Expected a bounded 0-31 day window, limit 1-500 and KOPIS performance IDs"
        )
    with (
        SupabaseRepository(SupabaseSettings.from_env()) as repo,
        httpx.Client(
            timeout=20,
            headers={"User-Agent": "ClassicHubble/1.0 (+https://classichubble.com)"},
        ) as client,
    ):
        return run(repo, PublicPages(client), a)


if __name__ == "__main__":
    raise SystemExit(main())
