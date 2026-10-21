from classic_hubble_pipeline.worklist_names import extract_rows, match_rows


def test_table_names_keep_exact_codes_and_ignore_references():
    html = """<table class="wikitable"><tr><th>번호</th><th>제목, 조성</th></tr>
    <tr><td>Op. 18/1<sup>99</sup></td><td>현악 사중주 1번 F 장조</td></tr>
    <tr><td>Op. 18/2</td><td rowspan="2">현악 사중주 2번</td></tr>
    <tr><td>Op. 18/3</td></tr></table>"""
    assert extract_rows(html) == [
        {
            "code": "Op. 18 No. 1",
            "title": "현악 사중주 1번 F 장조",
            "evidence": ["Op. 18/1", "현악 사중주 1번 F 장조"],
        }
    ]


def test_list_items_do_not_inherit_child_movement_names_or_partial_catalogues():
    html = """<ul><li>클라리넷 협주곡 A 장조, K. 622 (1791년)<ul><li>2악장 아다지오</li></ul></li>
    <li>피아노 협주곡 11번 F 장조, K. 413/387a</li>
    <li>현악 사중주 K. 155-160</li><li>두 소나타 Op. 27, 1번과 2번</li></ul>"""
    assert extract_rows(html) == [
        {
            "code": "K. 622",
            "title": "클라리넷 협주곡 A 장조",
            "evidence": ["클라리넷 협주곡 A 장조, K. 622 (1791년)"],
        }
    ]


def test_match_is_composer_bound_unique_and_checks_ordinal_genre_and_scope():
    works = [
        {
            "id": "one",
            "composer_id": "c",
            "catalogue": "Op. 18 No. 1",
            "title": "String Quartet No. 1 in F major",
        },
        {
            "id": "two",
            "composer_id": "other",
            "catalogue": "Op. 18 No. 1",
            "title": "String Quartet No. 1",
        },
    ]
    rows = [{"code": "Op. 18 No. 1", "title": "현악 사중주 1번 F 장조", "evidence": []}]
    accepted, rejected = match_rows(rows, "c", works)
    assert accepted[0]["work_id"] == "one"
    assert not rejected
    for title in (
        "현악 사중주 2번",
        "피아노 소나타 1번",
        "현악 사중주 1번 중 2악장",
        "현악 사중주 1번 편곡",
    ):
        assert not match_rows([{**rows[0], "title": title}], "c", works)[0]
    assert not match_rows(rows, "c", works + [{**works[0], "id": "duplicate"}])[0]
    assert not match_rows([{**rows[0], "code": "Op. 18"}], "c", works)[0]


def test_conflicting_source_rows_and_key_conflicts_are_not_resolved_arbitrarily():
    work = {
        "id": "w",
        "composer_id": "c",
        "catalogue": "Op. 1",
        "title": "Piano Sonata No. 1 in C major",
    }
    rows = [
        {"code": "Op. 1", "title": "피아노 소나타 1번 C 장조", "evidence": []},
        {"code": "Op. 1", "title": "피아노 소나타 2번", "evidence": []},
    ]
    assert not match_rows(rows, "c", [work])[0]
    assert not match_rows(
        [{**rows[0], "title": "피아노 소나타 1번 D 장조"}], "c", [work]
    )[0]


def test_accidental_spellings_agree_but_quartet_and_quintet_do_not():
    work = {
        "id": "w",
        "composer_id": "c",
        "catalogue": "Op. 1",
        "title": "String Quartet No. 1 in E-flat major",
    }
    row = {"code": "Op. 1", "title": "현악 사중주 1번 E♭ 장조", "evidence": []}
    assert match_rows([row], "c", [work])[0]
    work["title"] = "Quintet for Piano and Winds in E-flat major"
    assert not match_rows(
        [{**row, "title": "피아노와 관악기를 위한 사중주"}], "c", [work]
    )[0]


def test_korean_solfege_key_and_incomplete_heading_dependent_names():
    work = {
        "id": "w",
        "composer_id": "c",
        "catalogue": "Op. 84",
        "title": "Piano Sonata No. 8 in B-flat major",
    }
    row = {"code": "Op. 84", "title": "피아노 소나타 8번 내림 나단조", "evidence": []}
    assert not match_rows([row], "c", [work])[0]
    assert match_rows([{**row, "title": "피아노 소나타 8번 내림 나장조"}], "c", [work])[
        0
    ]
    assert not match_rows([{**row, "title": "8번 내림 나장조"}], "c", [work])[0]
    assert not match_rows([{**row, "title": "피아노 소나타(Sonata"}], "c", [work])[0]


def test_collection_counts_and_movement_nicknames_are_not_work_aliases():
    work = {
        "id": "w",
        "composer_id": "c",
        "catalogue": "Op. 116",
        "title": "Seven Fantasies, Op. 116",
    }
    row = {"code": "Op. 116", "title": "여섯 환상곡, 피아노곡", "evidence": []}
    assert not match_rows([row], "c", [work])[0]


def test_manifest_preserves_display_title_and_exclusions_have_an_audit_reason():
    from classic_hubble_pipeline.worklist_names import build_manifest

    html = "<ul><li>교향곡 1번 C 장조 Op. 1</li><li>교향곡 2번 D 장조 Op. 2</li></ul>"
    source = {
        "composer": "Composer",
        "parse": {"pageid": 1, "revid": 12, "title": "작품 목록", "text": {"*": html}},
        "exclude": {"Op. 2": "Source scope needs review"},
    }
    works = [
        {
            "id": "w",
            "composer_id": "c",
            "title": "Symphony No. 1 in C major",
            "title_ko": "기존 제목",
            "catalogue": "Op. 1",
        },
        {
            "id": "v",
            "composer_id": "c",
            "title": "Symphony No. 2 in D major",
            "title_ko": None,
            "catalogue": "Op. 2",
        },
    ]
    links = [
        {"provider_id": "Q123", "payload": {"work_id": "w"}},
        {"provider_id": "Q124", "payload": {"work_id": "v"}},
    ]
    manifest, audit = build_manifest(
        [source], works, [{"id": "c", "name": "Composer"}], links
    )
    assert len(manifest["works"]) == 1
    entry = manifest["works"][0]
    assert entry["qid"] == "Q123"
    assert entry["title_ko"] == "기존 제목"
    assert entry["aliases"][0]["text"] == "교향곡 1번 C 장조"
    assert entry["evidence"][0]["code"] == "Op. 1"
    assert any(row["reason"] == "Source scope needs review" for row in audit)
