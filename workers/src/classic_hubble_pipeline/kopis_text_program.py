"""Verify a dated concert cover and a separate, official KOPIS programme transcript."""
import hashlib
import json
import re
from datetime import UTC, date, datetime

from .direct_vision import _cached, _identity, _original
from .kopis_typed_recital import _DETAIL
from .music_extraction import digest, json_bytes
from .organizer_program import _archive
from .source_archive import download_source
from .worklist_names import Document


_CREDIT = r"[A-Za-zÀ-ÖØ-öø-ÿ가-힣][A-Za-zÀ-ÖØ-öø-ÿ가-힣 .'-]{0,90}"
_BYLINE = re.compile(rf"({_CREDIT}?)(?: \((?:b\. [0-9]{{4}}|[0-9]{{4}}-[0-9]{{4}})\))?(?: \(작사 : [가-힣]{{2,8}}\))?")
_PLAYER = re.compile(r"(?:Soprano|Trumpet|Saxophone) [가-힣]{2,8}(?:, [가-힣]{2,8})*")
_EXCLUDE = re.compile(r"\b(?:arr\.|arranged|arrangement|arranger)|편곡|작품해설|예매", re.I)
_MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
_WEEK = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()


def blocks(text, style):
    if not isinstance(text,str) or len(text.encode())>32000 or style not in {"stacked","bullets"}:
        return []
    lines=text.replace("\r\n","\n").split("\n")
    if len(lines)>200 or lines[0].strip()!="[PROGRAM]" or any(re.search(r"[\[\]<>]",s) for s in lines[1:]):
        return []
    result=[]
    if style=="bullets":
        for raw in lines[1:]:
            s=raw.strip()
            if not s:continue
            if not s.startswith("*"):return []
            parts=[x.strip() for x in s[1:].strip().split(" / ")]
            result.append(tuple(parts) if len(parts)==2 and re.fullmatch(_CREDIT,parts[0]) and parts[1] and not _EXCLUDE.search(s) else None)
    else:
        for section in re.split(r"\n[ \t]*\n", "\n".join(lines[1:]).strip()):
            ls=[s.strip() for s in section.split("\n") if s.strip()]
            if not ls or ls==["INTERMISSION"]:continue
            if len(ls)==1:return []
            m=_BYLINE.fullmatch(ls[0])
            ok=len(ls) in (2,3) and m and not _EXCLUDE.search(section) and (len(ls)==2 or _PLAYER.fullmatch(ls[2]))
            result.append((m[1],ls[1]) if ok else None)
    return result if 0<len(result)<=60 else []


def _fold(value):
    return value.strip().lower().replace("é","e").replace("Ⅱ","II").replace("ⅱ","ii")


def cover_matches(r, p):
    if (r.get("status")!="text_extracted" or r.get("coverage")!="complete" or r.get("extraction_status")!="no_program_identified"
            or r.get("items")!=[] or any(l.get("page_index")!=0 for l in r.get("lines",[]))):
        return False
    try:
        ls=[l["text"] for l in r["lines"]];day=date.fromisoformat(p["day"]);wk=day.weekday();k="월화수목금토일"[wk]
        m=re.fullmatch(k+r"요일\(((?:[01][0-9]|2[0-3])):([0-5][0-9])\)",p["schedule"])
        if not m or not 6<=len(ls)<=18:return False
        hh,mm=map(int,m.groups())
        if p["style"]=="bullets":
            if p["venue"]!="쌀롱드무지끄 (쌀롱드무지끄)" or not p["title"].startswith("쌀롱드무지끄, "):return False
            title=p["title"].split(", ",1)[1].removesuffix(f" ({day.month}.{day.day})")
            return (ls[0]=="Salon de Musique" and _fold(title).removeprefix("the ")==_fold(ls[1])
                    and ls[2:7]==[f"{_MONTHS[day.month-1]} {day.year}",f"{day.month} / {day.day}",str(day.year),f"{_WEEK[wk]} {hh:02}:{mm:02}","Line up"]
                    and bool(ls[7:]) and all(re.fullmatch(r"(?:Violin|Piano|Cello) [가-힣]{2,8}|Ticket OPEN *: .+",s) for s in ls[7:]))
        if p["style"]=="stacked":
            venue=p["venue"].split(" (")[0]
            return (len(ls)>=8 and re.sub(r" \[[^][]+\]$","",p["title"])==" ".join(ls[:2])
                    and ls[2:4]==["With","SEOULKUNST ORCHESTRA"] and all(" | " in s and not re.search(r"[0-9]",s) for s in ls[4:-3])
                    and ls[-3:]==[f"{day.year}. {day.month}. {day.day}. ({k})",f"{'오전' if hh<12 else '오후'} {hh%12 or 12}시 {mm}분",venue])
    except (KeyError,TypeError,ValueError,IndexError):
        pass
    return False


def _credit(printed, composer):
    p,c=_fold(printed),_fold(composer)
    return p==c or (bool(re.fullmatch(r"[a-z]\. [^ .]+",p)) and len(c.split())>=2 and p[3:]==c.split()[-1] and any(p[0]==v[0] for v in c.split()[:-1]))


_OPUS = re.compile(r"\bop\.?\s*([0-9]+[a-z]?)(?:,\s*(?:no\.?\s*)?([0-9]+))?\b",re.I)


def _work(row):
    title,canonical,w,detail=(row[k] for k in ("title","canonical_title","work_witness","detail"))
    t,c,v=_fold(title),_fold(canonical),_fold(w)
    if not c or not t or not v:return False
    if row["scope"]=="excerpt":
        return detail==title and t!=c and t in v and c in v
    if row["scope"]!="unknown" or detail is not None:return False
    parts=t.split(" 中 ".lower())
    if len(parts)>2 or (len(parts)==2 and (parts[0] not in v or parts[1]!=c)):return False
    root,_,suffix=parts[-1].partition(", op. ")
    if suffix:
        number=_OPUS.fullmatch("op. "+suffix);db=_OPUS.fullmatch((row.get("catalogue") or "").lower())
        if (not number or not db or number[1]!=db[1] or (db[2] and number[2]!=db[2])
                or [m.groups() for m in _OPUS.finditer(v)]!=[number.groups()]):return False
    if not (root==c or (len(root)>=8 and c.startswith(root+" in "))):return False
    if root in v:return True
    # Some critical editions list key and opus group rather than ordinal sonata number.
    m=re.fullmatch(r"violin sonata no\. [1-9][0-9]? in ([a-g] (?:major|minor))",root)
    return bool(m and suffix and "violin sonata" in v and m[1] in v)


def source_supports(raw, witnesses):
    if not witnesses or any(not isinstance(w,str) or not w for w in witnesses):return False
    dom=Document(raw.decode("utf-8-sig"))
    pending=set(witnesses)
    for tag in ("h1","h2","h3","h4","li","p","dt","dd","span","a","strong","td","title","div"):
        for node in dom.root.descendants(tag):
            value=" ".join(node.text().split())
            pending={s for s in pending if s not in value}
            if not pending:return True
    return False


def verified_items(text,proof):
    try:
        pieces=blocks(text,proof["style"]);out=[];last=-1;ids=set()
        for row in proof["rows"]:
            i=row["position"];s=proof["sources"][row["source"]]
            if (type(i) is not int or not last<i<len(pieces) or pieces[i]!=(row["credit"],row["title"])
                    or not re.fullmatch(r"[a-f0-9]{64}",s["sha"]) or not re.fullmatch(r"https://[^/\s]+/.+",s["url"])
                    or not _credit(row["credit"],row["composer"]) or not row["credit_witness"]
                    or _fold(row["composer"]).split()[-1] not in _fold(row["credit_witness"])
                    or not _work(row) or row["work_id"] in ids):
                return []
            out.append(dict(position=i,work_id=row["work_id"],composer_name=row["composer"],display_title=row["title"],
                            performed_scope=row["scope"],scope_details=[row["detail"]] if row["detail"] is not None else []))
            ids.add(row["work_id"]);last=i
        return out
    except (TypeError,ValueError,AttributeError,KeyError,IndexError):
        return []


def publish(repository,store,client,kopis,performance_id,authority,*,apply=False):
    target=repository.load_vision_target(performance_id)
    if (not target or not target.get("starts_on") or target["starts_on"]!=target.get("ends_on")
            or len(target.get("intro_image_urls") or [])!=1 or store.bucket!="classic-hubble-sources"):
        return {"status":"date_or_source_binding_required","items":0}
    proof=json.loads(_archive(store,"extractions",authority))
    url,=target["intro_image_urls"];src=repository.load_vision_source(url)
    if (not src or src.get("source_url")!=url or performance_id not in (src.get("performance_ids") or [])
            or src.get("bucket")!=store.bucket or proof.get("version")!="kopis-typed-blocks-v1"
            or [proof.get(x) for x in ("id","day","title","cover_sha") ]!=[performance_id,target["starts_on"],target["title"],src.get("sha256")]):
        return {"status":"stale_evidence","items":0}
    identity=_identity(store,src["sha256"])
    if src.get("object_key")!=identity["source_object_key"]:return {"status":"stale_evidence","items":0}
    cached=_cached(repository,store,identity)
    if not cached or digest(cached)!=proof["envelope_sha"] or not cover_matches(cached["reading"],proof):
        return {"status":"cover_binding_unverified","items":0}
    _original(store,identity)
    if not 1<=len(proof["sources"])<=60:return {"status":"work_evidence_unverified","items":0}
    for k,source in proof["sources"].items():
        raw=_archive(store,"originals",source["sha"])
        if len(raw)>2500000:return {"status":"work_evidence_unverified","items":0}
        witnesses=[row[f] for row in proof["rows"] if row["source"]==k for f in ("work_witness","credit_witness")]
        if not source_supports(raw,witnesses):return {"status":"work_evidence_unverified","items":0}
    rows=verified_items(proof["sty"],proof)
    if not rows:return {"status":"work_evidence_unverified","items":0}
    packet=dict(authority=authority,sha=src["sha256"],reading_key=digest(identity),envelope_utf8=json_bytes(cached).decode())
    preview=repository.publish_kopis_text_program(performance_id,packet,None)
    if not apply or preview["status"]!="ready":return preview
    if preview.get("program")!=rows:raise ValueError("KOPIS text programme preview mismatch")
    detail=kopis.get_performance_detail(proof["kopis"]).raw_payload
    if detail.get("sty")!=proof["sty"] or any(k not in detail for k in _DETAIL):return {"status":"stale_kopis_detail","items":0}
    obj,mime=download_source(client,url);h=hashlib.sha256(obj).hexdigest()
    if h!=src["sha256"] or mime!=src["content_type"]:return {"status":"cover_changed","items":0}
    packet.update(live_detail={k:detail[k] for k in _DETAIL},live_sty_sha=hashlib.sha256(detail["sty"].encode()).hexdigest(),live_sha=h,
                  content_type=mime,checked_at=datetime.now(UTC).isoformat())
    return repository.publish_kopis_text_program(performance_id,packet,rows)
