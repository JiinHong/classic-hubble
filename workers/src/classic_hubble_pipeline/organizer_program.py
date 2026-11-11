"""Cross-check an official programme against a saved reading without promoting its OCR status."""
import hashlib
import json
import re
from datetime import UTC, date, datetime

from .worklist_names import Document
from .direct_vision import _cached, _identity, _original
from .music_extraction import digest, json_bytes
from .source_archive import download_source


def _text(node):
    return " ".join(node.text().split())


def _one(values):
    values = list(values)
    if len(values) != 1:
        raise ValueError("Absent or ambiguous official field")
    return values[0]


def _matched(pattern, value):
    match = re.fullmatch(pattern, value)
    if not match:
        raise ValueError("Unexpected official field")
    return match.groups()


def official_event(layout, raw):
    if len(raw) > 2_000_000:
        raise ValueError("Official document too large")
    doc = Document(raw.decode("utf-8-sig")).root
    if layout == "national_theatre":
        event = _one(x for x in doc.descendants("div") if "viewLft" in x.attrs.get("class","").split())
        fields = [_text(x) for x in event.descendants("li")]
        start, end = _matched(r"기간 *(\d{4}-\d\d-\d\d) *~ *(\d{4}-\d\d-\d\d)", _one(x for x in fields if x.startswith("기간")))
        weekday, clock = _matched(r"시간 *([월화수목금토일]) (\d\d:\d\d)", _one(x for x in fields if x.startswith("시간")))
        hall, = _matched(r"장소 *(.+)", _one(x for x in fields if x.startswith("장소")))
        heading = _one(x for x in doc.descendants("h3") if x.attrs.get("id") == "viewTab02" and _text(x) == "프로그램")
        code = heading.attrs.get("data-id")
        if not code or not code.isdecimal():
            raise ValueError("Missing official programme section")
        block = _one(x for x in doc.descendants("div") if x.attrs.get("data-id") == code and "inrdc" in x.attrs.get("class","").split())
        program = [_text(x) for x in block.descendants("p") if _text(x)]
        header = _one(x for x in event.descendants("div") if "tit" in x.attrs.get("class","").split())
        title = _text(_one(header.descendants("span")))
        if not 1 <= len(program) <= 150:
            raise ValueError("Unbounded programme")
    elif layout == "paju_hwp":
        title = _text(_one(x for x in doc.descendants("h3") if "txt_b" in x.attrs.get("class","").split()))
        places = [n for n in doc.descendants("dl") if [_text(t) for t in n.descendants("dt")]==["장소"]]
        hall = _text(_one(_one(places).descendants("dd")))
        span = _one(_text(x) for x in doc.descendants("p") if "date" in x.attrs.get("class","").split())
        start, a, end, b = _matched(r"(\d{4}-\d\d-\d\d)\(([월화수목금토일])\) ~ (\d{4}-\d\d-\d\d)\(([월화수목금토일])\)",span)
        slot = _one(_text(x) for x in doc.descendants("p") if _text(x).startswith("- 공연일시:"))
        y,m,d,weekday,clock = _matched(r"- 공연일시: (\d{4})\. *(\d{1,2})\. *(\d{1,2})\.\(([월화수목금토일])\) (\d\d:\d\d)",slot)
        if a != b or b != weekday or date(int(y),int(m),int(d)).isoformat() != start:
            raise ValueError("Conflicting venue dates")
        program = []
    else:
        raise ValueError("Unsupported official layout")
    if start != end or "월화수목금토일"[date.fromisoformat(start).weekday()] != weekday or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock):
        raise ValueError("Multiple sessions or invalid schedule")
    return dict(day=start,clock=clock,hall=hall,title=title,program=program)


def _quote(lines, spans):
    q = _one(spans)
    line, = _matched(r"L(\d{6})", q["line_id"])
    s, quote = lines[int(line)], q["quote"]
    if s.get("page_index") != 0 or not quote or quote not in s["text"]:
        raise ValueError("Ungrounded poster quote")
    return quote


def _credit(full, printed, official):
    if not full or not official or not printed:
        return False
    if full == official == printed:
        return True
    # Do not generalize the documented bilingual identity to arbitrary surname matches.
    return full == "Felix Mendelssohn" and (printed,official) in {
        ("Felix Mendelssohn Bartholdy","Felix Mendelssohn Bartholdy"), ("멘델스존","펠릭스 멘델스존")}


def verified_program_rows(reading, proof):
    """Proof selects exact programme slots; other text cannot create a new candidate."""
    try:
        if (reading["status"] != "text_extracted" or reading["extraction_status"] != "items_extracted" or
            reading["coverage"] not in {"complete","partial"} or not 1 <= len(proof["rows"]) <= 50):
            return []
        out, last_line = [], -1
        for row in proof["rows"]:
            i = row["index"]
            if type(i) is not int or i < 0 or out and i <= out[-1]["position"]:
                return []
            ref = reading["items"][i]
            if ref["context"] != "program" or ref["scope"] not in {"unknown","full_work"} or ref.get("key") or ref.get("catalogue"):
                return []
            title = _quote(reading["lines"],ref["title"])
            credit = _quote(reading["lines"],ref["composer"])
            parts = [_quote(reading["lines"],s) for s in ref["movements"]]
            if (row["poster_title"] != title or row["poster_credit"] != credit or not row["work_id"] or
                not _credit(row["canonical_credit"],credit,row["official_credit"])):
                return []
            ot, oc = row["official_title"], row["official_credit"]
            if proof["format"] == "national_theatre":
                n = row["line"]
                if reading["coverage"] != "complete" or type(n) is not int or n <= last_line:
                    return []
                observed = proof["event"]["program"][n]
                if (observed != ot+" ❘ "+oc or oc!=credit or (ot.casefold()!=title.casefold() and not (
                    ot[:len(title)].casefold()==title.casefold() and re.fullmatch(r" [가-힣][가-힣 ]*",ot[len(title):])))):
                    return []
                last_line=n
                if parts:
                    if not (row["canonical_credit"]=="Felix Mendelssohn" and title=="Der 42. Psalm" and
                            row.get("independent_source")=="psalm" and len(parts)==7):
                        return []
                    title_line=int(ref["title"][0]["line_id"][1:])
                    if any(int(group[0]["line_id"][1:])!=title_line+j or not re.match(re.escape(roman)+r"\. ",part)
                           for j,(group,part,roman) in enumerate(zip(ref["movements"],parts,("I","II","III","IV","V","VI","VII")),1)):
                        return []
                elif (ref["title"][0]["line_id"]!=ref["composer"][0]["line_id"] or
                      reading["lines"][int(ref["title"][0]["line_id"][1:])]["text"]!=title+" "+credit):
                    return []
            elif proof["format"] == "paju_hwp":
                notice = proof["notice"]
                if (i != 0 or len(reading["items"]) != 1 or len(proof["rows"]) != 1 or ref["scope"]!="unknown" or
                    parts!=["제1부 | Erster Teil","제2부 | Zweiter Teil"] or ot!=title or
                    not notice["credit"].startswith("독일의 작곡가 "+oc+"이 작곡한 ‘"+ot+"’는 ") or
                    "정기공연 오라토리오 ‘"+ot+"’를 선보인다." not in notice["dated"] or
                    row["line"]!=notice["paragraph_indices"][1]):
                    return []
            else:
                return []
            out.append(dict(position=i,work_id=row["work_id"],display_title=title,composer_name=row["canonical_credit"],
                            performed_scope="unknown",scope_details=parts))
        return out
    except (KeyError, IndexError, ValueError, TypeError):
        return []


_PUBLIC_PAGES = {
    "national_theatre": r"https://www\.ntok\.go\.kr/ntok/pm/prfmng/performanceDetail\.do\?mi=21009&perfId=[0-9]+",
    "paju_hwp": r"https://www\.pajucf\.or\.kr/business/02_1_view\.php\?no=[0-9]+(?:&page=)?",
}
_RELEASE = r"https://www\.paju\.go\.kr/user/board/BD_board\.view\.do\?bbsCd=1023&seq=[0-9]+"
_ATTACHMENT = r"https://www\.paju\.go\.kr/component/file/ND_fileDownload\.do\?id=[a-f0-9-]+"


def _fetch(client, url, pattern):
    if not re.fullmatch(pattern,url):
        raise ValueError("Not an authorized organizer URL")
    with client.stream("GET", url, follow_redirects=False) as response:
        response.raise_for_status()
        raw = bytearray()
        for chunk in response.iter_bytes():
            if len(raw)+len(chunk)>2_000_000:
                raise ValueError("Organizer document too large")
            raw.extend(chunk)
    return bytes(raw)


def _archive(store, prefix, sha):
    if not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha):
        raise ValueError("Invalid organizer evidence checksum")
    data=store.read(f"{prefix}/sha256/{sha[:2]}/{sha}")
    if hashlib.sha256(data).hexdigest()!=sha:
        raise ValueError("Organizer evidence integrity mismatch")
    return data


def _linked_notice(raw, attachment):
    from urllib.parse import urljoin
    if not re.fullmatch(_ATTACHMENT,attachment):
        return False
    return any(urljoin("https://www.paju.go.kr/",a.attrs.get("href",""))==attachment
               and ".hwp" in _text(a).lower() for a in Document(raw.decode()).root.descendants("a"))


def publish(repository, store, client, kopis, performance_id, authority, *, apply=False):
    target=repository.load_vision_target(performance_id)
    if (not target or target.get("starts_on")!=target.get("ends_on") or not target.get("starts_on")
            or len(target.get("intro_image_urls") or [])!=1 or store.bucket!="classic-hubble-sources"):
        return {"status":"single_date_and_source_required","items":0}
    url,=target["intro_image_urls"];src=repository.load_vision_source(url)
    if not src or src.get("source_url")!=url or performance_id not in (src.get("performance_ids") or []):
        return {"status":"source_not_archived","items":0}
    identity=_identity(store,src["sha256"])
    if src.get("bucket")!=store.bucket or src.get("object_key")!=identity["source_object_key"]:
        raise ValueError("Archived poster identity mismatch")
    proof=json.loads(_archive(store,"extractions",authority))
    if (proof.get("version")!="corroborated-organizer-v1" or proof.get("id")!=performance_id or proof.get("date")!=target["starts_on"]
            or proof.get("image_url")!=url or proof.get("image_sha")!=src["sha256"] or proof.get("kopis_title")!=target["title"]):
        return {"status":"official_event_not_verified","items":0}
    cached=_cached(repository,store,identity)
    if (not cached or digest(cached)!=proof.get("envelope_sha") or cached["reading_sha256"]!=proof.get("reading_sha")):
        return {"status":"poster_evidence_changed","items":0}
    _original(store,identity)
    fmt=proof["format"];sources=proof["sources"];venue=sources["venue"];public_url=proof["public_url"]
    if (fmt not in _PUBLIC_PAGES or venue["url"]!=public_url or not re.fullmatch(_PUBLIC_PAGES[fmt],public_url)
            or not 1<=len(sources)<=51):
        return {"status":"unsupported_organizer","items":0}
    archived={name:_archive(store,"originals",entry["sha"]) for name,entry in sources.items()}
    if official_event(fmt,archived["venue"])!=proof["event"] or any(row["independent_source"] not in archived for row in proof["rows"]):
        return {"status":"official_document_changed","items":0}
    if fmt=="paju_hwp" and (hashlib.sha256(archived["attachment"]).hexdigest()!=proof["notice"]["source_sha"]
            or not _linked_notice(archived["release"],sources["attachment"]["url"])):
        return {"status":"unbound_native_notice","items":0}
    rows=verified_program_rows(cached["reading"],proof)
    if not rows:
        return {"status":"work_identity_not_verified","items":0}
    packet=dict(sha=src["sha256"],authority=authority,reading_key=digest(identity),envelope_utf8=json_bytes(cached).decode())
    preview=repository.publish_organizer_program(performance_id,packet,None)
    if not apply or preview["status"]!="ready":
        return preview
    if preview.get("program")!=rows:
        raise ValueError("Poster/official-programme preview mismatch")
    current=official_event(fmt,_fetch(client,public_url,_PUBLIC_PAGES[fmt]))
    if current!=proof["event"]:
        return {"status":"official_document_changed","items":0}
    if fmt=="paju_hwp":
        att=sources["attachment"]["url"]
        if not _linked_notice(_fetch(client,sources["release"]["url"],_RELEASE),att):
            return {"status":"unbound_native_notice","items":0}
        packet["live_attachment_sha"]=hashlib.sha256(_fetch(client,att,_ATTACHMENT)).hexdigest()
        if packet["live_attachment_sha"]!=proof["notice"]["source_sha"]:
            return {"status":"official_document_changed","items":0}
    detail=kopis.get_performance_detail(proof["kopis"]).raw_payload
    keys=("mt20id","prfnm","prfpdfrom","prfpdto","dtguidance","fcltynm","styurls")
    raw,mime=download_source(client,url);sha=hashlib.sha256(raw).hexdigest()
    if sha!=src["sha256"] or mime!=src["content_type"] or not all(k in detail for k in keys):
        return {"status":"live_sources_or_preview_changed","items":0}
    packet.update(live_event=current,live_detail={k:detail[k] for k in keys},live_sha=sha,content_type=mime,checked_at=datetime.now(UTC).isoformat())
    return repository.publish_organizer_program(performance_id,packet,rows)
