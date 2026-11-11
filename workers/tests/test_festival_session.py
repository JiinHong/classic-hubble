import hashlib
from copy import deepcopy
from html import escape

import pytest

from classic_hubble_pipeline.festival_session import session_lines, verified_session


def fixture():
    lines = ["2026 PAN Music Festival", "PAN Music Festival 앙상블 - 역대 명예회장 작품전", "PMF Ensemble - Works",
             "시간을 잇는 소리", "Sounds Across Generations", "진규영 플룻, 클라리넷 피아노를 위한 < 트리오 > (1998)",
             "CHIN Kyu-Yung < Trio > for Flute, Clarinet and Piano", "장소 Venue", "거암아트홀", "GEOAM ART HALL",
             "일시 Date", "2026년 10월 21일 (Wed) 19:30"]
    sty = "[PROGRAM]\n시간을 잇는 소리\nSounds Across Generations\n\n진규영 - 플룻, 클라리넷 피아노를 위한 <트리오>\nCHIN Kyu-Yung <Trio> for Flute, Clarinet and Piano"
    proof = dict(day="2026-10-21", title="제54회 범음악제, 콘서트 1. 역대 명예회장 작품전", venue="거암아트홀 (거암아트홀)", schedule="수요일(19:30)",
                 sources={"session":{"url":"https://www.iscm-korea.com/2026-PMF","sha":"a"*64}}, sty=sty, session=lines,
                 session_sha=hashlib.sha256("\n".join(lines).encode()).hexdigest(), rows=[dict(work_id="w", composer="CHIN Kyu-Yung", credit_ko="진규영",
                     title="Trio for Flute, Clarinet and Piano",title_ko="플룻, 클라리넷 피아노를 위한 트리오",year="1998")])
    r = dict(status="text_extracted", coverage="complete", extraction_status="no_program_identified",items=[],lines=[
        dict(page_index=0,text=x) for x in ["제54회 범음악제","2026. 10. 21 Wed.","- 10. 30 Fri.","The 54th PAN Music Festival","※ 상세 일정은 범음악제 홈페이지(QR) 참조 바랍니다."]])
    return proof,r


def test_session_binds_instrumentation_date_and_two_languages():
    p,r=fixture()
    assert verified_session(r,p)==[dict(position=0,work_id="w",composer_name="CHIN Kyu-Yung",display_title=p["rows"][0]["title_ko"],performed_scope="unknown",scope_details=[])]
    for key,v in (("day","2026-10-22"),("venue","일신홀 (일신홀)"),("schedule","수요일(17:30)"),("title","제54회 범음악제, 콘서트 1. 다른 연주회")):
        assert not verified_session(r,{**p,key:v})
    for key,v in (("composer","Yi ManBang"),("title","Trio for Clarinet, Violine and Piano"),("year","1999")):
        q=deepcopy(p);q["rows"][0][key]=v;assert not verified_session(r,q)
    assert not verified_session(r,{**p,"sty":p["sty"].replace("진규영 -","배우 -")})
    assert not verified_session(r,{**p,"sty":p["sty"].replace("<트리오>","<트리오> (2003)")})
    for i,v in ((0,"제55회 범음악제"),(1,"2026. 10. 22 Thu."),(2,"- 10. 30 Sat.")):
        s=deepcopy(r);s["lines"][i]["text"]=v;assert not verified_session(s,p)


def test_session_splits_cards_before_reading_a_date():
    p,_=fixture()
    def block(ls):
        return '<div data-selector="div.text">'+''.join('<div>'+escape(s)+'</div>' for s in ls)+'</div>'
    html=block(["Another concert","일시 Date","2026년 10월 22일 (Thu) 19:30"])+block(p["session"])
    assert session_lines(html.encode(),p["sty"])==p["session"]
    for bad in (html+block(p["session"]),block(p["session"][:-2])+block(p["session"][-2:]),block(p["session"]+["일시 Date","2026년 10월 22일 (Thu) 19:30"]),
                block(p["session"]+["공연 취소 및 곡목 변경 안내"])):
        with pytest.raises(ValueError):session_lines(bad.encode(),p["sty"])
