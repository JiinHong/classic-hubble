"""Bind one bilingual KOPIS programme to its own dated organizer section."""
import hashlib
import re
from datetime import date

from .worklist_names import Document


STYLE = "iscm_bilingual_session"
WEEK = "Mon Tue Wed Thu Fri Sat Sun".split()
_FOOTER = (
    "이 행사는 한국문화예술위원회 중장기지원사업 일환으로 진행됩니다.",
    "This seminar is held with support of the Art Council Korea(ARKO).",
    "ISCM 한국지부 및 PAN Music Festival 준비위원회", "ISCM Korea",
    "https://iscm-korea.com", "www.facebook.com/panmusicfestival",
)


def _compact(s):
    return " ".join(s.split())


def session_lines(raw, sty):
    if not raw or len(raw)>2_000_000:
        raise ValueError("Organizer page size")
    hdr=sty.splitlines()[:3]
    if len(hdr)!=3 or hdr[0]!="[PROGRAM]" or not all(hdr[1:]):
        raise ValueError("Missing bilingual programme heading")
    hits=[]
    for b in Document(raw.decode("utf-8-sig")).root.descendants("div"):
        if b.attrs.get("data-selector")!="div.text":
            continue
        ls=[_compact(n.text()) for n in b.descendants("div") if not any(n.descendants("div")) and n.text().strip()]
        if ls[3:5]!=hdr[1:]:continue
        if ls.count("일시 Date")!=1 or ls.count("장소 Venue")!=1:
            raise ValueError("Ambiguous organizer session")
        i=ls.index("일시 Date")
        if i+1>=len(ls) or tuple(ls[i+2:]) not in ((),_FOOTER):
            raise ValueError("Missing date or unrecognized organizer notice")
        hits.append(ls[:i+2])
    if len(hits)!=1:raise ValueError("Session not unique")
    return hits[0]


def session_url(proof):
    year=date.fromisoformat(proof["day"]).year
    if set(proof["sources"])!={"session"} or proof["sources"]["session"]["url"]!=f"https://www.iscm-korea.com/{year}-PMF":
        raise ValueError("Not the official festival year")
    return proof["sources"]["session"]["url"]


def _date(y,m,d,w):
    v=date(int(y),int(m),int(d))
    if WEEK[v.weekday()]!=w:raise ValueError("Wrong cover weekday")
    return v


def cover_day(r,p):
    lines=r["lines"];day=date.fromisoformat(p["day"])
    if (r["status"],r["coverage"],r["extraction_status"],r["items"])!=("text_extracted","complete","no_program_identified",[]):return False
    if len(lines)!=5 or any(l["page_index"]!=0 for l in lines):return False
    festival,start,end,en,note=[l["text"] for l in lines]
    heading=re.fullmatch(r"(제([1-9][0-9]?)회 범음악제), 콘서트 [1-9][0-9]?\. (.+)",p["title"])
    first=re.fullmatch(r"(\d{4})\. (\d{1,2})\. (\d{1,2}) ([A-Z][a-z]{2})\.",start)
    last=re.fullmatch(r"- (\d{1,2})\. (\d{1,2}) ([A-Z][a-z]{2})\.",end)
    if not heading or not first or not last:return False
    n=int(heading[2]);suffix="th" if 11<=n%100<=13 else {1:"st",2:"nd",3:"rd"}.get(n%10,"th")
    return (festival==heading[1] and en==f"The {n}{suffix} PAN Music Festival" and
            note=="※ 상세 일정은 범음악제 홈페이지(QR) 참조 바랍니다." and
            _date(*first.groups())<=day<=_date(first[1],*last.groups()) and p["session"][1].endswith(" - "+heading[3]))


def verified_session(r,p):
    try:
        day=date.fromisoformat(p["day"]);session_url(p);s=p["session"];rows=p["rows"]
        if not cover_day(r,p) or not 1<=len(rows)<=30 or len(s)!=10+2*len(rows):return []
        if (s[0]!=f"{day.year} PAN Music Festival" or not s[1].startswith("PAN Music Festival ") or not s[2].startswith("PMF Ensemble - ")
                or s[-5]!="장소 Venue" or s[-2]!="일시 Date" or p["venue"]!=s[-4]+" ("+s[-4]+")"
                or hashlib.sha256("\n".join(s).encode()).hexdigest()!=p["session_sha"]):return []
        clock=re.fullmatch("월화수목금토일"[day.weekday()]+r"요일\(((?:[01]\d|2[0-3]):[0-5]\d)\)",p["schedule"])
        if not clock or s[-1]!=f"{day.year}년 {day.month}월 {day.day}일 ({WEEK[day.weekday()]}) {clock[1]}":return []
        typed=[_compact(x) for x in p["sty"].splitlines() if x.strip()]
        if len(typed)!=3+2*len(rows) or typed[:3]!=["[PROGRAM]",*s[3:5]]:return []
        result=[];ids=set()
        for i,row in enumerate(rows):
            ko,en=typed[3+2*i:5+2*i]
            k=re.fullmatch(r"([가-힣]{2,6}) - ([^<>]+) <([^<>]+)>(?: \(([0-9]{4})\))?",ko)
            e=re.fullmatch(r"([A-Za-z][A-Za-z .'-]+) <([^<>]+)> ((?:for|on|für) [^<>]+)",en)
            yr=row["year"];wid=row["work_id"]
            if not k or not e or wid in ids or not re.fullmatch(r"[0-9]{4}",yr) or (k[4] and k[4]!=yr):return []
            if re.search(r"편곡|발췌|모음곡 중|\b(?:arranged|excerpt)\b",ko+" "+en,re.I):return []
            if (s[5+2*i]!=f"{k[1]} {k[2]} < {k[3]} > ({yr})" or s[6+2*i]!=f"{e[1]} < {e[2]} > {e[3]}"
                    or (row["credit_ko"],row["composer"],row["title_ko"],row["title"])!=(k[1],e[1],k[2]+" "+k[3],e[2]+" "+e[3])):return []
            result.append(dict(position=i,work_id=wid,display_title=row["title_ko"],composer_name=e[1],performed_scope="unknown",scope_details=[]));ids.add(wid)
        return result
    except (KeyError,IndexError,ValueError,TypeError,AttributeError):
        return []
