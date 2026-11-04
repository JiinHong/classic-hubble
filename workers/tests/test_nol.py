from __future__ import annotations

import httpx
import pytest

from classic_hubble_pipeline import nol


def test_settings_read_optional_timeout_and_retry_values_from_environment():
    settings = nol.NolSettings.from_env(
        {
            "NOL_TIMEOUT_SECONDS": "7",
            "NOL_MAX_RETRIES": "2",
            "NOL_RETRY_BACKOFF_SECONDS": "0.5",
        }
    )

    assert settings.timeout_seconds == 7
    assert settings.max_retries == 2
    assert settings.retry_backoff_seconds == 0.5


def test_settings_reject_non_numeric_environment_values():
    with pytest.raises(nol.NolConfigurationError, match="numeric"):
        nol.NolSettings.from_env({"NOL_TIMEOUT_SECONDS": "slow"})


def test_extract_nol_goods_code_accepts_official_legacy_and_current_urls():
    assert (
        nol.extract_nol_goods_code(
            "http://ticket.interpark.com/Ticket/Goods/GoodsInfo.asp?GoodsCode=25012345"
        )
        == "25012345"
    )
    assert (
        nol.extract_nol_goods_code(
            "https://tickets.interpark.com/goods/25012345?app_tapbar_state=hide"
        )
        == "25012345"
    )
    assert (
        nol.extract_nol_goods_code(
            "https://tickets.interpark.com/play/goods/25012345"
        )
        == "25012345"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://ticket.interpark.com.attacker.example/Goods/GoodsInfo.asp?GoodsCode=25012345",
        "https://attacker.example/goods/25012345",
        "https://tickets.interpark.com.evil.example/goods/25012345",
        "https://tickets.interpark.com/contents/notice/detail/14081",
        "https://tickets.interpark.com/goods/not-a-code",
        "https://ticket.interpark.com/Goods/GoodsInfo.asp?GoodsCode=2501234",
        "ftp://tickets.interpark.com/goods/25012345",
        "https://user:pass@tickets.interpark.com/goods/25012345",
        "https://tickets.interpark.com:444/goods/25012345",
        "mailto:test@example.com",
    ],
)
def test_extract_nol_goods_code_rejects_lookalike_or_nongoods_urls(url: str):
    assert nol.extract_nol_goods_code(url) is None


def test_parse_nol_payload_prefers_live_play_db_html_and_extracts_en_dash_lifespans():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(),
        play_db={
            "common": {"message": "success", "internalHttpStatusCode": 200},
            "data": {
                "playNo": "P0001",
                "programInfo": (
                    "W. A. Mozart (1756&ndash;1791)<br />"
                    "Symphony No. 40 in G minor, K. 550<br />"
                    "I. Molto allegro<br />&nbsp;<br />"
                    "Franz Schubert (1797–1828)<br />"
                    "Symphony No. 8 in B minor, D. 759 &lt;Unfinished&gt;"
                ),
            },
        },
    )

    assert data.goods_code == "25012345"
    assert data.program_status == "confirmed"
    assert data.program_source_url == "https://tickets.interpark.com/goods/25012345"
    assert data.program_image_urls == (
        "https://ticketimage.interpark.com/Play/image1.jpg",
    )
    assert [item.position for item in data.program_items] == [0, 1]
    assert data.program_items[0].composer == "W. A. Mozart"
    assert data.program_items[0].composer_lifespan == "1756-1791"
    assert data.program_items[0].work_title == (
        "Symphony No. 40 in G minor, K. 550\nI. Molto allegro"
    )
    assert data.program_items[0].display_title == (
        "W. A. Mozart (1756-1791)\nSymphony No. 40 in G minor, K. 550\nI. Molto allegro"
    )
    assert data.program_items[1].composer == "Franz Schubert"
    assert data.program_items[1].composer_lifespan == "1797-1828"
    assert data.program_items[1].work_title == "Symphony No. 8 in B minor, D. 759 <Unfinished>"


def test_parse_nol_payload_keeps_a_single_line_work_in_the_program_field():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(content_html=""),
        play_db={
            "common": {"message": "success", "internalHttpStatusCode": 200},
            "data": {"programInfo": "La mer"},
        },
    )

    assert data.program_status == "confirmed"
    assert len(data.program_items) == 1
    assert data.program_items[0].composer is None
    assert data.program_items[0].work_title == "La mer"


def test_parse_nol_payload_falls_back_to_summary_program_heading_content_html():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(
            content_html=(
                "<div>"
                "<h3>공연소개</h3><p>일반 소개 텍스트</p>"
                "<h3>PROGRAM</h3>"
                "<p>Gustav Mahler (1860-1911)<br/>Symphony No. 5 in C-sharp minor</p>"
                "<p>&nbsp;</p>"
                "<p>작곡가 소개처럼 보이지만 heading 밖 내용은 무시</p>"
                "<h3>출연진</h3><p>홍길동</p>"
                "</div>"
            ),
        ),
        play_db={"programInfo": "   "},
    )

    assert data.program_status == "confirmed"
    assert len(data.program_items) == 1
    assert data.program_items[0].composer == "Gustav Mahler"
    assert data.program_items[0].composer_lifespan == "1860-1911"
    assert data.program_items[0].work_title == "Symphony No. 5 in C-sharp minor"


def test_parse_nol_payload_recognizes_exact_program_strong_block_heading():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(
            content_html=(
                "<div>"
                "<p><strong>공연소개</strong></p><p>일반 소개</p>"
                "<p><strong>PROGRAM </strong></p>"
                "<p>Antonin Dvorak (1841-1904)<br />Cello Concerto in B minor, Op. 104</p>"
                "<p><strong>출연진</strong></p><p>홍길동</p>"
                "</div>"
            )
        ),
        play_db={"common": {"message": "success", "internalHttpStatusCode": 200}, "data": None},
    )

    assert data.program_status == "confirmed"
    assert [item.position for item in data.program_items] == [0]
    assert data.program_items[0].composer == "Antonin Dvorak"
    assert data.program_items[0].work_title == "Cello Concerto in B minor, Op. 104"


def test_parse_nol_payload_marks_image_only_when_only_detail_images_exist():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(
            content_html=(
                '<div><img src="//ticketimage.interpark.com/Play/image1.jpg"/>'
                '<img src="http://ticketimage.interpark.com/Play/image2.jpg"/></div>'
            )
        ),
        play_db=None,
    )

    assert data.program_status == "image_only"
    assert data.program_items == ()
    assert data.program_image_urls == (
        "https://ticketimage.interpark.com/Play/image1.jpg",
        "https://ticketimage.interpark.com/Play/image2.jpg",
    )


@pytest.mark.parametrize(
    ("content_html", "expected_status"),
    [
        ("<div><h3>PROGRAM</h3><p>프로그램은 공연 당일 공개됩니다.</p></div>", "selected_on_day"),
        ("<div><h3>PROGRAM</h3><p>프로그램은 추후 공개 예정입니다.</p></div>", "announced_later"),
        ("<div><h3>PROGRAM</h3><p>프로그램 미기재</p></div>", "not_published"),
    ],
)
def test_parse_nol_payload_classifies_nonconfirmed_program_states(
    content_html: str, expected_status: str
):
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(content_html=content_html),
        play_db=None,
    )

    assert data.program_status == expected_status
    assert data.program_items == ()


@pytest.mark.parametrize(
    "summary_payload",
    [
        {},
        {"data": None},
        {"data": {"goodsName": "Title"}},
        {"data": {"goodsName": "Title", "placeName": "Venue", "goodsCode": 25012345}},
        {
            "common": {"message": "success", "internalHttpStatusCode": 403},
            "data": {"goodsCode": "25012345", "goodsName": "Title", "placeName": "Venue"},
        },
        {
            "common": {"message": "blocked", "internalHttpStatusCode": 200},
            "data": {"goodsCode": "25012345", "goodsName": "Title", "placeName": "Venue"},
        },
    ],
)
def test_parse_nol_payload_rejects_malformed_summary_envelopes(summary_payload: object):
    with pytest.raises(nol.NolResponseError, match="summary"):
        nol.parse_nol_payload("25012345", summary=summary_payload, play_db=None)  # type: ignore[arg-type]


def test_parse_nol_payload_rejects_malformed_play_db_envelopes():
    with pytest.raises(nol.NolResponseError, match="play DB"):
        nol.parse_nol_payload(
            "25012345",
            summary=_summary_payload(),
            play_db={
                "common": {"message": "success", "internalHttpStatusCode": 200},
                "data": "not-a-mapping",
            },
        )


def test_parse_nol_payload_accepts_play_db_data_null_as_no_record():
    data = nol.parse_nol_payload(
        "25012345",
        summary=_summary_payload(
            content_html="<div><h3>PROGRAM</h3><p>프로그램은 추후 공개 예정입니다.</p></div>"
        ),
        play_db={"common": {"message": "success", "internalHttpStatusCode": 200}, "data": None},
    )

    assert data.program_status == "announced_later"


def test_parse_nol_payload_rejects_malformed_play_db_common_envelope():
    with pytest.raises(nol.NolResponseError, match="play DB"):
        nol.parse_nol_payload(
            "25012345",
            summary=_summary_payload(),
            play_db={
                "common": {"message": "forbidden", "internalHttpStatusCode": 403},
                "data": {"playNo": "P0001", "programInfo": ""},
            },
        )


def test_parse_nol_payload_always_derives_program_source_url_from_goods_code():
    data = nol.parse_nol_payload(
        "25012345",
        summary={
            "common": {"message": "success", "internalHttpStatusCode": 200},
            "data": {
                "goodsCode": "25012345",
                "goodsName": "테스트 공연",
                "placeName": "테스트홀",
                "goodsUrl": "https://attacker.example/goods/99999999",
                "contentHtml": '<div><img src="http://ticketimage.interpark.com/Play/image1.jpg"/></div>',
            },
        },
        play_db=None,
    )

    assert data.program_source_url == "https://tickets.interpark.com/goods/25012345"


def test_client_retries_temporary_statuses_before_returning_parsed_payload():
    attempts = 0
    delays: list[float] = []
    seen_headers: list[tuple[str | None, str | None, str | None, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        seen_headers.append(
            (
                request.headers.get("user-agent"),
                request.headers.get("accept"),
                request.headers.get("origin"),
                request.headers.get("referer"),
            )
        )
        if attempts < 3:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        if request.url.path == "/v1/goods/25012345/summary":
            return httpx.Response(200, json=_summary_payload())
        if request.url.path == "/v1/goods/play-db":
            return httpx.Response(
                200,
                json={
                    "common": {"message": "success", "internalHttpStatusCode": 200},
                    "data": {"playNo": "P0001", "programInfo": "Claude Debussy (1862-1918)<br />La mer"},
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = nol.NolClient(
        nol.NolSettings(max_retries=2),
        http_client=http_client,
        sleep=delays.append,
    )

    data = client.fetch("https://tickets.interpark.com/goods/25012345")

    assert data.program_status == "confirmed"
    assert data.program_items[0].composer == "Claude Debussy"
    assert data.program_items[0].position == 0
    assert attempts == 4
    assert delays == [0.25, 0.5]
    assert len(seen_headers) == 4
    for user_agent, accept, origin, referer in seen_headers:
        assert user_agent
        assert accept == "application/json, text/plain, */*"
        assert origin == "https://tickets.interpark.com"
        assert referer == "https://tickets.interpark.com/goods/25012345"
    http_client.close()


def test_client_treats_a_missing_optional_play_db_record_as_summary_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/goods/25012345/summary":
            return httpx.Response(
                200,
                json=_summary_payload(
                    content_html=(
                        '<div><img src="//ticketimage.interpark.com/Play/program.jpg"/></div>'
                    )
                ),
            )
        if request.url.path == "/v1/goods/play-db":
            return httpx.Response(404, json={"message": "not found"})
        raise AssertionError(f"unexpected path {request.url.path}")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = nol.NolClient(nol.NolSettings(), http_client=http_client)

    data = client.fetch("https://tickets.interpark.com/goods/25012345")

    assert data.program_status == "image_only"
    assert data.program_items == ()
    assert data.raw_play_db is None
    http_client.close()


def test_client_retries_transport_errors_then_raises_clean_failure():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("connection failed", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = nol.NolClient(
        nol.NolSettings(max_retries=2),
        http_client=http_client,
        sleep=lambda delay: None,
    )

    with pytest.raises(nol.NolTransportError, match="retrying") as error:
        client.fetch("https://tickets.interpark.com/goods/25012345")

    assert attempts == 3
    assert error.value.__cause__ is None
    http_client.close()


@pytest.mark.parametrize("status", [401, 403, 429])
def test_client_exposes_access_failures_without_retrying_or_changing_endpoints(status):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(status, text="access denied")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = nol.NolClient(nol.NolSettings(max_retries=3), http_client=http_client)
        with pytest.raises(nol.NolTransportError) as raised:
            client.fetch("https://tickets.interpark.com/goods/26012173")
    assert raised.value.status_code == status
    assert paths == ["/v1/goods/26012173/summary"]


def test_client_rejects_retired_null_summary_before_requesting_play_db():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={
            "common": {"message": "success", "internalHttpStatusCode": 200},
            "data": None,
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = nol.NolClient(http_client=http_client)
        with pytest.raises(nol.NolResponseError, match="summary"):
            client.fetch("https://tickets.interpark.com/goods/26012173")
    assert paths == ["/v1/goods/26012173/summary"]


def _summary_payload(
    *,
    goods_code: str = "25012345",
    goods_name: str = "테스트 공연",
    venue_name: str = "테스트홀",
    content_html: str = '<div><img src="http://ticketimage.interpark.com/Play/image1.jpg"/></div>',
) -> dict[str, object]:
    return {
        "common": {"message": "success", "internalHttpStatusCode": 200},
        "data": {
            "goodsCode": goods_code,
            "goodsName": goods_name,
            "placeName": venue_name,
            "contentHtml": content_html,
        }
    }
