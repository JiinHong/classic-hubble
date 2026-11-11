import hashlib
from copy import deepcopy
from html import escape

import pytest

from classic_hubble_pipeline.venue_vocal import venue_lines, verified_songs


def fixture():
    stub = ["리스트 서거 140년 기념음악회", "리스트가 사랑한 시인들", "제29회 한국성악예술학회 정기연주회", "2026. 10. 20. TUE. 7:30 PM", "세종체임버홀"]
    reading = dict(coverage="complete",status="text_extracted",extraction_status="no_program_identified",items=[],lines=[dict(text=s,page_index=0) for s in stub])
    printed = ["1. Ich liebe dich, S. 315 (F. Rückert) - Sop. 이소정", "2. Freudvoll und Leidvoll, S. 280-1 (J. W. Goethe) - Sop. 이소정"]
    heading = stub[2]+" <"+stub[0]+" "+stub[1]+">"
    section=[heading,"기간 2026.10.20(화)","장소 세종체임버홀 위치보기","시간 19:30",*printed]
    row=dict(position=0,work_id="w",composer="Franz Liszt",title="Ich liebe dich",catalogue="S. 315",slug="liszt-vocal-s315")
    proof=dict(day="2026-10-20",title=stub[2],schedule="화요일(19:30)",venue="세종문화회관 (세종체임버홀)",
               session=section,session_sha=hashlib.sha256("\n".join(section).encode()).hexdigest(),
               sources={"venue":dict(sha="b"*64,url="https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?menuNo=200320&performIdx=37693")},
               sty="[PROGRAM]\n독일 시인 “뤼케르트” - Acc. 김현정\n"+"\n".join(printed),rows=[row],held={"1":"specific_setting"})
    return proof,reading


def test_only_exact_dated_vocal_work_without_edition_claim():
    p,r=fixture()
    assert verified_songs(r,p)==[dict(position=0,work_id="w",composer_name="Franz Liszt",display_title="Ich liebe dich",performed_scope="unknown",scope_details=[])]
    for k,v in (("composer","F. Rückert"),("composer","이소정"),("catalogue","S. 532"),("position",1),("title","Ich liebe"),("catalogue","S. 315-1")):
        q=deepcopy(p);q["rows"][0][k]=v;assert not verified_songs(r,q)
    for k,v in (("day","2026-10-21"),("venue","다른 홀 (세종체임버홀)"),("schedule","화요일(07:30)"),("held",{})):
        assert not verified_songs(r,{**p,k:v})
    for ix in (0,1,2,3,4):
        changed=deepcopy(r);changed["lines"][ix]["text"]+="?";assert not verified_songs(changed,p)


def test_scoped_program_does_not_take_numbered_biography_or_ignore_change():
    p,_=fixture();s=p["session"]
    top='<div class="show_sub_top"><p class="tit">'+escape(s[0])+'</p></div>'
    info='<table><tr>'+''.join('<td>'+v+'</td>' for v in s[1:4])+'</tr></table>'
    def html(lines):
        return (top+info+'<li id="tabMove2"><div class="editer"><p>[PROGRAM]</p>'+''.join('<p>'+escape(v)+'</p>' for v in lines)+'</div></li><li><p>3. A previous performance</p></li>').encode()
    assert venue_lines(html(s[4:]))==s
    for extra in ("공연 취소", "※ 곡목 변경 안내", "다른 날짜 공연", "2. Unmarked song"):
        with pytest.raises(ValueError):venue_lines(html([*s[4:],extra]))
    with pytest.raises(ValueError):
        venue_lines(html(s[4:])+b'<li id="tabMove1"><p>'+ "※ 프로그램 변경 안내".encode()+b'</p></li>')
