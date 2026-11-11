from copy import deepcopy
import pytest

from classic_hubble_pipeline.organizer_program import official_event, verified_program_rows


NATIONAL = """<span>국립합창단 &lt;다른 공연&gt;</span><div class="viewLft"><div class="tit"><span>국립합창단 청년교육단원 결과보고회 &lt;Fermata : 음악이 머무는 자리&gt;</span></div>
<ul><li>기간2026-10-22 ~ 2026-10-22</li><li>장소달오름극장</li><li>시간목 19:30</li></ul></div>
<h3 id="viewTab02" data-id="123">프로그램</h3><div class="inrdc" data-id="123">
<p>Sure on this shining night 별빛 가득한 이밤에 ❘ Morten Lauridsen</p></div>
<h3 id="viewTab03">출연 및 제작진 소개</h3><div><p>Adagio ❘ Samuel Barber</p></div>"""
PAJU = """<h3 class="txt_b">[대관] 파주시립예술단 제57회 정기공연 &lt;엘리야&gt;</h3>
<p class="date mont">2026-10-22(목) ~ 2026-10-22(목)</p><dl><dt>장소</dt><dd>운정행복센터 공연장</dd></dl>
<p>- 예매기간: 2026. 10. 6.(화) 14:00</p><p>- 공연일시: 2026. 10. 22.(목) 19:30</p>"""


def test_official_schedule_is_not_a_booking_date_or_a_different_session():
    event=official_event("paju_hwp",PAJU.encode())
    assert (event["day"],event["clock"],event["hall"])==("2026-10-22","19:30","운정행복센터 공연장")
    for old,new in [("공연일시:","예매기간:"),("19:30","25:30"),("22.(목)","22.(수)"),("22.(목)","23.(금)"),
                    ("2026-10-22(목) ~","2026-10-21(수) ~")]:
        with pytest.raises(ValueError):
            official_event("paju_hwp",PAJU.replace(old,new).encode())


def test_theatre_uses_program_section_only_and_preserves_document_order():
    event=official_event("national_theatre",NATIONAL.encode())
    assert event["day"]=="2026-10-22" and event["program"]==["Sure on this shining night 별빛 가득한 이밤에 ❘ Morten Lauridsen"]
    for a,b in [("기간2026-10-22","기간2026-10-21"),("시간목","시간수"),('class="inrdc"','class="bio"'),("기간","예매일")]:
        with pytest.raises(ValueError):
            official_event("national_theatre",NATIONAL.replace(a,b).encode())


def test_same_title_different_composer_does_not_change_the_printed_identity():
    event=official_event("national_theatre",NATIONAL.encode())
    title,credit="Sure on this shining night","Morten Lauridsen"
    ref=lambda q:[{"line_id":"L000001","quote":q}]
    item=dict(context="program",scope="full_work",composer=ref(credit),title=ref(title),movements=[],key=None,catalogue=None)
    r=dict(status="text_extracted",coverage="complete",extraction_status="items_extracted",lines=[{"page_index":0,"text":"Program"},{"page_index":0,"text":title+" "+credit}],items=[item])
    w=dict(index=0,work_id="w",poster_title=title,poster_credit=credit,official_title=event["program"][0].split(" ❘ ")[0],official_credit=credit,line=0,canonical_credit=credit)
    proof=dict(format="national_theatre",event=event,rows=[w])
    assert verified_program_rows(r,proof)==[{"position":0,"work_id":"w","display_title":title,"scope_details":[],"performed_scope":"unknown","composer_name":credit}]
    for bad in ({**w,"official_credit":"Samuel Barber"},{**w,"poster_credit":"Barber"},{**w,"line":-1},{**w,"canonical_credit":"Samuel Barber"}):
        assert verified_program_rows(r,{**proof,"rows":[bad]})==[]
    for k,v in (("scope","arrangement"),("context","biography"),("title",ref("Sure")),("composer",ref("Lauridsen"))):
        altered=deepcopy(r);altered["items"][0][k]=v
        assert verified_program_rows(altered,proof)==[]
    altered=deepcopy(proof)
    altered["event"]["program"][0]=title+" II ❘ "+credit
    altered["rows"][0]["official_title"]=title+" II"
    assert verified_program_rows(r,altered)==[]


def test_venue_paths_and_agency_attachment_link_are_constrained_before_network():
    from classic_hubble_pipeline.organizer_program import _fetch, _linked_notice, _PUBLIC_PAGES
    url="https://www.paju.go.kr/component/file/ND_fileDownload.do?id=ab-12"
    assert _linked_notice(('<a href="'+url+'">보도자료.hwp</a>').encode(),url)
    assert not _linked_notice(('<a href="'+url+'">다른 파일</a>').encode(),url)
    for value in ("https://other.example/?url=www.ntok.go.kr","http://www.ntok.go.kr/",
                  "https://www.ntok.go.kr.other.example/ntok/pm/prfmng/performanceDetail.do?mi=21009&perfId=1"):
        with pytest.raises(ValueError,match="authorized organizer URL"):
            _fetch(None,value,_PUBLIC_PAGES["national_theatre"])
