"""Bind a numbered song to the venue's programme, never to a performer's biography."""
import hashlib
import re
from datetime import date

from .worklist_names import Document


STYLE = "sejong_numbered_liszt_songs"
URL = r"https://www\.sejongpac\.or\.kr/portal/performance/performance/performTicket\.do\?menuNo=200320&performIdx=[1-9][0-9]{0,7}"
_VOICE = r"(?:Ten|Sop|Bar)\. [가-힣]{2,6}"
_HEAD = r"(?:<\s*[12]부>|Intermiss(?:i)?on|(?:이탈리아|프랑스|독일) 시인 [“”가-힣, ]+(?:\s*[-–]\s*Acc\. [가-힣, ]+)?|Acc\. [가-힣, ]+)"
_TITLE = r"([A-Za-zÀ-ÖØ-öø-ÿ'’!, .-]{2,120})"
_ALL = re.compile(r"[1-9][0-9]?\. "+_TITLE+r", S\. ([1-9][0-9]{1,3})(-[12]|, No\. *[1-9])?(?: \([A-Za-zÀ-ÖØ-öø-ÿ. ]+\))?\s*[-–]\s*"+_VOICE)


def _one(items):
    one, = items
    return one


def _numbered(lines):
    positions=[]
    for line in lines:
        line=line.strip().replace("\u200b","")
        if not line or re.fullmatch(_HEAD,line):
            continue
        if not _ALL.fullmatch(line):
            raise ValueError("Unknown vocal programme row")
        positions.append(line)
    if not 1<=len(positions)<=60 or len(set(positions))!=len(positions):
        raise ValueError("Absent or duplicate programme rows")
    return positions


def venue_lines(raw):
    if len(raw)>2_000_000:raise ValueError("Venue page too large")
    doc=Document(raw.decode("utf-8-sig")).root
    text=lambda n:" ".join(n.text().split())
    top=_one(n for n in doc.descendants("div") if "show_sub_top" in n.attrs.get("class","").split())
    heading=text(_one(n for n in top.descendants("p") if n.attrs.get("class")=="tit"))
    cells=[text(n) for n in doc.descendants("td")]
    fields=[_one(s for s in cells if s.startswith(prefix)) for prefix in ("기간 ","장소 ","시간 ")]
    notices=[n for n in doc.descendants("li") if n.attrs.get("id")=="tabMove1"]
    if any(re.search(r"(공연|출연진|곡목|프로그램)\s*(?:이 |이?가 |의 )?(?:변경|취소|연기)",text(n)) for n in notices):
        raise ValueError("Venue posted a change notice")
    tab=_one(n for n in doc.descendants("li") if n.attrs.get("id")=="tabMove2")
    section=_one(n for n in tab.descendants("div") if n.attrs.get("class")=="editer")
    lines=[text(n) for n in section.descendants("p") if text(n)]
    if not lines or lines[0]!="[PROGRAM]":raise ValueError("Unbound programme section")
    return [heading,*fields,*_numbered(lines[1:])]


def verified_songs(reading,p):
    try:
        if [reading.get(k) for k in ("coverage","status","extraction_status","items")]!=["complete","text_extracted","no_program_identified",[]]:return []
        cover=[n["text"] for n in reading["lines"] if n["page_index"]==0]
        if len(cover)!=5 or len(reading["lines"])!=5:return []
        s=p["session"];day=date.fromisoformat(p["day"]);wk="월화수목금토일"[day.weekday()]
        if (set(p["sources"])!={"venue"} or not re.fullmatch(URL,p["sources"]["venue"]["url"])
                or not re.fullmatch("[a-f0-9]{64}",p["sources"]["venue"]["sha"])
                or hashlib.sha256("\n".join(s).encode()).hexdigest()!=p["session_sha"]):return []
        clock=re.fullmatch(wk+r"요일\((([01][0-9]|2[0-3]):[0-5][0-9])\)",p["schedule"])
        if not clock:return []
        hh,mm=map(int,clock[1].split(":"));en=("MON","TUE","WED","THU","FRI","SAT","SUN")[day.weekday()]
        if (cover[2]!=p["title"] or cover[4]!="세종체임버홀" or p["venue"]!="세종문화회관 ("+cover[4]+")"
                or not re.fullmatch(r"리스트 (?:서거|탄생) [1-9][0-9]{0,2}년 기념음악회",cover[0])
                or cover[1]!="리스트가 사랑한 시인들" or cover[3]!=f"{day.year}. {day.month}. {day.day}. {en}. {hh%12 or 12}:{mm:02} {'AM' if hh<12 else 'PM'}"
                or s[:4]!=[cover[2]+" <"+cover[0]+" "+cover[1]+">",f"기간 {day:%Y.%m.%d}({wk})","장소 "+cover[4]+" 위치보기","시간 "+clock[1]]):return []
        ls=p["sty"].splitlines()
        if not ls or ls[0]!="[PROGRAM]" or len(ls)>200 or _numbered(ls[1:])!=s[4:]:return []
        result=[];seen=set();positions=set();last=-1
        for r in p["rows"]:
            i=r["position"]
            if type(i) is not int or not last<i<len(s)-4 or r["work_id"] in seen:return []
            m=_ALL.fullmatch(s[4+i]);title,num,qual=m.groups()
            if (qual or r["catalogue"]!="S. "+num or r["title"]!=title.replace("’","'") or r["composer"]!="Franz Liszt"
                    or r["slug"]!="liszt-vocal-s"+num):return []
            result.append(dict(position=i,work_id=r["work_id"],composer_name=r["composer"],display_title=title,performed_scope="unknown",scope_details=[]))
            seen.add(r["work_id"]);positions.add(str(i));last=i
        if set(p["held"])!={str(i) for i in range(len(s)-4)}-positions:return []
        return result
    except (IndexError,ValueError,TypeError,KeyError,AttributeError):
        return []
