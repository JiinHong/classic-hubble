from classic_hubble_pipeline import official_program_sync as sync


def test_program_labels_scope_and_composer_reset():
    lines = [
        "출연자",
        "Liszt / Not a program",
        "[PROGRAM]",
        "R. Schumann (1810-1856)",
        "Symphonic Etudes, Op. 13",
        "M. Ravel (1875-1937)",
        "소개",
        "Wrong, Op. 13",
    ]
    assert sync.program_pairs(lines) == [("R. Schumann", "Symphonic Etudes, Op. 13")]
    assert sync.program_pairs(
        [
            "[프로그램]",
            "베토벤 / 교향곡 제5번 Op.67",
            "[출연]",
            "모차르트 / 교향곡 K.297",
        ]
    ) == [("베토벤", "교향곡 제5번 Op.67")]


def test_schubert_deutsch_number_is_not_a_key_or_a_movement():
    work = dict(title="Rastlose Liebe", title_ko=None, catalogue="D. 138",
                composers={"name": "Franz Schubert", "name_ko": "프란츠 슈베르트"}, work_aliases=[])
    assert sync.identify("F. Schubert", "Rastlose Liebe, D.138", [work]) == work
    assert sync.identify("F. Schubert", "Rastlose Liebe, D.139", [work]) is None
    assert sync.identify("F. Schubert", "Rastlose Liebe, D major", [work]) is None
    assert sync.identify("F. Schubert", "Rastlose Liebe, D.138 No. 2", [work]) is None


def test_title_and_catalogue_must_agree_not_just_number():
    work = dict(
        id="w",
        composer_id="c",
        catalogue="Op. 67",
        title="Symphony No. 5 in C minor",
        title_ko="교향곡 5번 '운명'",
        composers={"name": "Ludwig van Beethoven", "name_ko": "루트비히 판 베토벤"},
        work_aliases=[],
    )
    assert sync.identify("베토벤", "교향곡 제5번 c단조 Op.67", [work]) == work
    assert sync.identify("베토벤", "교향곡 제6번 Op.67", [work]) is None
    assert sync.identify("브람스", "교향곡 제5번 Op.67", [work]) is None
    assert sync.identify("베토벤", "교향곡 제5번 Op.67 중 1악장", [work]) is None
    assert (
        sync.identify("베토벤", "교향곡 제5번 Op.67", [work, dict(work, id="other")])
        is None
    )
    assert sync.identify("베토벤", "교향곡 제5번 G장조 Op.67", [work]) is None
    assert sync.identify("베토벤", "교향곡 제5번 Op.67 (피아노판)", [work]) is None


def test_scope_or_date_change_in_program_rejects_unbound_entries():
    assert sync.program_pairs(
        [
            "[PROGRAM]",
            "브람스, 클라리넷 삼중주",
            "Brahms, Clarinet Trio in A minor, Op. 114",
            "※ 프로그램 및 출연자는 변경될 수 있습니다.",
            "Brahms, Biography, Op. 12",
        ]
    ) == [
        ("브람스", "클라리넷 삼중주"),
        ("Brahms", "Clarinet Trio in A minor, Op. 114"),
    ]
    for instruction in ["2026.11.28 별도 공연", "11월 28일", "I. Allegro", "공연 취소"]:
        assert not sync.program_pairs(
            ["[프로그램]", "베토벤 / 교향곡 제5번 Op.67", instruction]
        )


def test_robots_hold_makes_no_content_request():
    import httpx
    import pytest

    def respond(request):
        assert request.url.path == "/robots.txt"
        return httpx.Response(200, text="User-agent: ChatGPT-User\nDisallow: /")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(PermissionError):
            sync.PublicPages(client).fetch("https://www.seoulphil.or.kr/")


def test_only_exact_official_sejong_urls():
    good = "https://www.sejongpac.or.kr/portal/performance/performance/performTicket.do?performIdx=37725&menuNo=200320"
    assert sync.sejong_id(good) == "37725"
    assert sync.sejong_id(good.replace(".or.kr/", ".or.kr.example.com/")) is None
    assert sync.sejong_id(good + "&performIdx=1") is None


def test_dates_and_halls_bind_even_for_direct_links():
    p = dict(
        starts_on="2026-11-16",
        ends_on="2026-11-16",
        title="조수연 피아노 독주회",
        venues={"name": "세종문화회관"},
        venue_halls={"name": "세종체임버홀"},
        schedule_text="월요일(19:30)",
    )
    e = sync.Event("조수연 피아노 독주회", "2026-11-16", "세종체임버홀", "19:30", [])
    assert sync.same_event(p, e, "sejong")
    assert not sync.same_event(dict(p, ends_on="2026-11-17"), e, "sejong")
    assert not sync.same_event(dict(p, venue_halls={"name": "세종대극장"}), e, "sejong")
    assert not sync.same_event(
        dict(p, schedule_text="월요일(15:00, 19:30)"), e, "sejong"
    )
    assert not sync.same_event(dict(p, title="홍길동 독주회"), e, "sejong")
