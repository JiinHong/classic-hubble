from classic_hubble_pipeline.archive_names import extract_archive_names


def test_archive_names_keep_bilingual_pairs_and_public_detail_links():
    html = """<a href="./video_detail.html?NO=12&amp;cno=405" class="box swiper-slide">
    <p class="subject">멘델스존 / 핑갈의 동굴, 작품26
    <span class="subject2">F. Mendelssohn / Fingal's Cave, Op.26</span></p>
    <p class="date">2006-10-20</p></a>"""
    assert extract_archive_names(html) == [
        {
            "url": "https://digitalkhall.kbssymphony.org/renew/concert/video_detail.html?NO=12&cno=405",
            "composer_ko": "멘델스존",
            "composer_en": "F. Mendelssohn",
            "title_ko": "핑갈의 동굴, 작품26",
            "title_en": "Fingal's Cave, Op.26",
            "date": "2006-10-20",
        }
    ]


def test_archive_ignores_malformed_pairs_editorials_and_foreign_links():
    html = """<a href="https://example.org/video_detail.html?NO=1"><p class="subject">작곡가 / 제목<span class="subject2">Composer / Title</span></p></a>
    <a href="video_detail.html?NO=2"><p class="subject">이야기<span class="subject2">Composer / Title</span></p></a>
    <a href="video_detail.html?NO=3"><p class="subject">작곡가 / 제목</p></a>"""
    assert extract_archive_names(html) == []


def test_archive_rejects_movements_versions_and_inconsistent_bilingual_labels():
    from classic_hubble_pipeline.archive_names import archive_name_conflict

    work = {"title": "Cello Suite No. 1 in G major", "catalogue": "BWV 1007"}
    for ko, en in [
        ("첼로 모음곡 1번 사라방드", "Cello Suite No.1, BWV1007 - Sarabande"),
        ("첼로 모음곡 1번", "Cello Suite No.1, BWV1007 'I. Prelude'"),
        ("첼로 모음곡 1번 편곡", "Cello Suite No.1, BWV1007"),
    ]:
        assert archive_name_conflict({"title_ko": ko, "title_en": en}, work)
    assert archive_name_conflict(
        {"title_ko": "교향적 환상곡 작품16", "title_en": "Eine Alpensinfonie, Op.64"},
        {"title": "An Alpine Symphony", "catalogue": "Op. 64"},
    )
    assert archive_name_conflict(
        {"title_ko": "플루트 협주곡", "title_en": "Violin Concerto in d minor"},
        {"title": "Violin Concerto in D minor", "catalogue": None},
    )


def test_archive_does_not_promote_one_piece_to_a_complete_collection():
    from classic_hubble_pipeline.archive_names import archive_name_conflict

    row = {
        "title_ko": "회화적 연습곡 제5번 작품39",
        "title_en": "Etudes-Tableaux No.5 in E-flat minor, Op.39",
    }
    assert archive_name_conflict(
        row, {"title": "Études-Tableaux, Op. 39", "catalogue": "Op. 39"}
    )
    row = {
        "title_ko": "관현악 모음곡 제2번, 작품1067",
        "title_en": "Orchestral Suite No.2 in B minor, BWV1067",
    }
    assert not archive_name_conflict(
        row, {"id": "w", "title": "Suite No. 2 in B minor", "catalogue": "BWV 1067"}
    )


def test_archive_rejects_a_suite_extracted_from_a_larger_work():
    from classic_hubble_pipeline.archive_names import archive_name_conflict

    assert archive_name_conflict(
        {
            "title_ko": "이상한 중국 관리 모음곡",
            "title_en": "The Miraculous Mandarin Suite, Op.19",
        },
        {"title": "The Miraculous Mandarin", "catalogue": "Op. 19"},
    )
