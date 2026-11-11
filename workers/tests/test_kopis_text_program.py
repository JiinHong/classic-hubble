from copy import deepcopy

from classic_hubble_pipeline.kopis_text_program import blocks, cover_matches, verified_items


def test_typed_blocks_do_not_inherit_a_composer_or_turn_a_soloist_into_one():
    s = "[PROGRAM]\r\n\r\n한태수 (b. 1973) (작사 : 채정은)\r\n아름다운 나라\r\nSoprano 서운정\r\n\r\nINTERMISSION\r\n\r\nThe Nutcracker 中 “Grand Pas de Deux”\r\n와이즈발레단 김민영, 박종희"
    assert blocks(s, "stacked") == [("한태수", "아름다운 나라"), None]
    assert blocks("[PROGRAM]\n* John Adams / Road Movies\n* No credit here\n* Claude Debussy / Beau soir, arranged for violin and piano", "bullets") == [
        ("John Adams","Road Movies"), None, None]
    assert blocks("[BIOGRAPHY]\n* John Adams / Road Movies","bullets") == []
    assert blocks("[PROGRAM]\n* John Adams / Road Movies\n[PROFILE]\n* John Adams / El Niño","bullets") == []
    for boundary in ("Program Notes","연주자 소개","2026. 10. 23. (금)"):
        assert blocks("[PROGRAM]\n\nJ. Haydn\nTrumpet Concerto\n\n"+boundary+"\n\nJ. Williams\nOlympic Fanfare and Theme","stacked")==[]


def cover(lines):
    return dict(status="text_extracted", coverage="complete", extraction_status="no_program_identified", items=[],
                lines=[dict(page_index=0,text=v) for v in lines])


def test_concert_date_and_room_not_the_ticket_open_date():
    p={"day":"2026-10-21","title":"쌀롱드무지끄, The last story Ⅱ","venue":"쌀롱드무지끄 (쌀롱드무지끄)","schedule":"수요일(19:00)","style":"bullets"}
    l=["Salon de Musique","Last Story II","OCT 2026","10 / 21","2026","Wednesday 19:00","Line up","Violin 이유진","Ticket OPEN: 10/7 Wed 9:00am"]
    assert cover_matches(cover(l),p)
    for i,bad in ((0,"Other venue"),(1,"First Story"),(2,"NOV 2026"),(3,"10 / 07"),(5,"Tuesday 19:00"),(6,"10 / 22")):
        a=l.copy();a[i]=bad;assert not cover_matches(cover(a),p)
    k={"day":"2026-10-22","title":"제3회 서울쿤스트오케스트라와 함께하는 장애인 한마음 열린음악회 [용인]","venue":"용인포은아트홀 (용인포은아트홀)","schedule":"목요일(19:30)","style":"stacked"}
    l=["제3회 서울쿤스트오케스트라와 함께하는","장애인 한마음 열린음악회","With","SEOULKUNST ORCHESTRA","G. Verdi | J. Haydn","2026. 10. 22. (목)","오후 7시 30분","용인포은아트홀"]
    assert cover_matches(cover(l),k)
    for i,bad in ((0,"다른 단체"),(5,"예매 2026. 10. 22. (목)"),(6,"오후 7시 20분"),(7,"다른 홀")):
        a=l.copy();a[i]=bad;assert not cover_matches(cover(a),k)


def test_immutable_references_protect_scope_credit_position_and_edition():
    s="[PROGRAM]\n\nG. Verdi (1813-1901)\nTriumphal March\n\nR. Løvland\nYou Raise Me Up\n\nT. Composer\nTest Suite, Op. 66"
    row=dict(position=0,credit="G. Verdi",title="Triumphal March",work_id="a",canonical_title="Aida",composer="Giuseppe Verdi",source="score",
             scope="excerpt",work_witness="Triumphal March from the opera Aida",credit_witness="Giuseppe Verdi",detail="Triumphal March")
    ref=dict(position=1,credit="R. Løvland",title="You Raise Me Up",work_id="b",canonical_title="You Raise Me Up",composer="Rolf Løvland",source="rights",
             scope="unknown",work_witness="You Raise Me Up",credit_witness="Rolf Løvland",detail=None)
    doc=dict(style="stacked",rows=[row,ref],sources={k:{"sha":"a"*64,"url":"https://example.org/"+k} for k in ["score","rights"]})
    got=verified_items(s,doc)
    assert [x["performed_scope"] for x in got]==["excerpt","unknown"] and got[0]["scope_details"]==["Triumphal March"]
    for change in (dict(credit="F. Loewe"),dict(position=-1),dict(scope="full_work"),dict(canonical_title="Rigoletto"),dict(detail="Entire opera"),dict(composer="Antonio Vivaldi")):
        d=deepcopy(doc);d["rows"][0].update(change);assert verified_items(s,d)==[]
    d=deepcopy(doc);d["rows"].append({**ref,"position":2,"credit":"T. Composer","title":"Test Suite, Op. 66","canonical_title":"Test Suite","composer":"T. Composer","catalogue":"Op. 66a","work_witness":"Test Suite, Op. 66a","credit_witness":"T. Composer","work_id":"c"})
    assert verified_items(s,d)==[]


def test_source_witness_must_confirm_the_entire_opus_not_a_numeric_prefix():
    from classic_hubble_pipeline.kopis_text_program import _work
    data=dict(title="Violin Sonata No. 8 in G major, Op. 30, No. 3",canonical_title="Violin Sonata No. 8 in G major",
              scope="unknown",detail=None,catalogue="Op. 30",work_witness="Violin Sonata G major op. 30,3")
    assert _work(data)
    for bad in ("Violin Sonata G major op. 30,31","Violin Sonata No. 8 in G major, Op. 31, No. 3","Violin Sonata No. 8 in G major"):
        assert not _work({**data,"work_witness":bad})
