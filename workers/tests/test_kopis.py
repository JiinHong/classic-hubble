from __future__ import annotations

from datetime import date

import httpx
import pytest

from classic_hubble_pipeline import kopis


LIST_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <mt20id>PF300001</mt20id>
    <prfnm>라흐마니노프 피아노 협주곡 2번</prfnm>
    <prfpdfrom>2026.07.18</prfpdfrom>
    <prfpdto>2026.07.18</prfpdto>
    <fcltynm>예술의전당 콘서트홀</fcltynm>
    <poster>https://kopis.or.kr/posters/PF300001.jpg</poster>
    <area>서울특별시</area>
    <genrenm>서양음악(클래식)</genrenm>
    <openrun>N</openrun>
    <prfstate>공연예정</prfstate>
  </db>
  <db>
    <mt20id>PF300002</mt20id>
    <prfnm>베토벤 교향곡 5번</prfnm>
    <prfpdfrom>2026.07.24</prfpdfrom>
    <prfpdto>2026.07.25</prfpdto>
    <fcltynm>롯데콘서트홀</fcltynm>
    <poster>https://kopis.or.kr/posters/PF300002.jpg</poster>
    <area>서울특별시</area>
    <genrenm>서양음악(클래식)</genrenm>
    <openrun>N</openrun>
    <prfstate>공연예정</prfstate>
  </db>
</dbs>
"""

DETAIL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <mt20id>PF300001</mt20id>
    <prfnm>라흐마니노프 피아노 협주곡 2번</prfnm>
    <mt10id>FC000001</mt10id>
    <mt13id>FC000001-01</mt13id>
    <fcltynm>예술의전당 콘서트홀</fcltynm>
    <frstregdt>2026-06-01 09:00:00</frstregdt>
    <prfpdfrom>2026.07.18</prfpdfrom>
    <prfpdto>2026.07.18</prfpdto>
    <prfcast>홍길동, 클래식 허블 오케스트라</prfcast>
    <prfcrew>지휘 김지휘</prfcrew>
    <prfruntime>120분</prfruntime>
    <prfage>8세 이상</prfage>
    <entrpsnm>클래식 허블</entrpsnm>
    <pcseguidance>R석 100,000원, S석 70,000원</pcseguidance>
    <poster>https://kopis.or.kr/posters/PF300001.jpg</poster>
    <sty>라흐마니노프 피아노 협주곡 2번</sty>
    <area>서울특별시</area>
    <genrenm>서양음악(클래식)</genrenm>
    <openrun>N</openrun>
    <updatedate>2026-07-01 13:00:00</updatedate>
    <prfstate>공연예정</prfstate>
    <dtguidance>토요일(17:00)</dtguidance>
    <styurls>
      <styurl>https://kopis.or.kr/intros/PF300001-1.jpg</styurl>
      <styurl>https://kopis.or.kr/intros/PF300001-2.jpg</styurl>
    </styurls>
    <relates>
      <relate>
        <relatenm>NOL 티켓</relatenm>
        <relateurl>https://tickets.example/PF300001</relateurl>
      </relate>
      <relate>
        <relatenm>공연장</relatenm>
        <relateurl>https://venue.example/PF300001</relateurl>
      </relate>
    </relates>
  </db>
</dbs>
"""

INVALID_KEY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <returncode>02</returncode>
    <errmsg>SERVICE KEY IS NOT REGISTERED ERROR</errmsg>
    <responsetime>2026-07-10 21:18:55</responsetime>
  </db>
</dbs>
"""

NO_DATA_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <returncode>04</returncode>
    <errmsg>NODATA ERROR</errmsg>
  </db>
</dbs>
"""

LAST_PAGE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <mt20id>PF300003</mt20id>
    <prfnm>드보르자크 교향곡 9번</prfnm>
    <prfpdfrom>2026.07.30</prfpdfrom>
    <prfpdto>2026.07.30</prfpdto>
    <fcltynm>LG아트센터 서울</fcltynm>
    <poster>https://kopis.or.kr/posters/PF300003.jpg</poster>
    <area>서울특별시</area>
    <genrenm>서양음악(클래식)</genrenm>
    <openrun>N</openrun>
    <prfstate>공연예정</prfstate>
  </db>
</dbs>
"""

FACILITY_LIST_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <mt10id>FC000001</mt10id>
    <fcltynm>예술의전당</fcltynm>
    <mt13cnt>6</mt13cnt>
    <fcltychartr>문예회관</fcltychartr>
    <sidonm>서울</sidonm>
    <gugunnm>서초구</gugunnm>
    <opende>1988</opende>
  </db>
</dbs>
"""

FACILITY_DETAIL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dbs>
  <db>
    <mt10id>FC000001</mt10id>
    <fcltynm>예술의전당</fcltynm>
    <mt13cnt>6</mt13cnt>
    <fcltychartr>문예회관</fcltychartr>
    <opende>1988</opende>
    <seatscale>12,044</seatscale>
    <telno>02-580-1300</telno>
    <relateurl>https://www.sac.or.kr/</relateurl>
    <adres>서울특별시 서초구 남부순환로 2406</adres>
    <la>37.4781</la>
    <lo>127.0118</lo>
    <restaurant>Y</restaurant>
    <cafe>Y</cafe>
    <store>Y</store>
    <nolibang>N</nolibang>
    <suyu>Y</suyu>
    <parkbarrier>Y</parkbarrier>
    <restbarrier>Y</restbarrier>
    <runwbarrier>Y</runwbarrier>
    <elevbarrier>Y</elevbarrier>
    <parkinglot>Y</parkinglot>
    <mt13s>
      <mt13>
        <mt13id>FC000001-01</mt13id>
        <prfplcnm>콘서트홀</prfplcnm>
        <seatscale>2,523</seatscale>
        <stageorchat>Y</stageorchat>
        <stagepracat>Y</stagepracat>
        <stagedresat>Y</stagedresat>
        <stageoutdrat>N</stageoutdrat>
        <disabledseatscale>20</disabledseatscale>
        <stagearea>23.4X15.0</stagearea>
      </mt13>
    </mt13s>
  </db>
</dbs>
"""


def test_sync_window_rejects_more_than_31_calendar_days():
    with pytest.raises(ValueError, match="31"):
        kopis.KopisSyncWindow(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 1),
        )


def test_build_performance_list_params_supports_pagination_and_after_date():
    window = kopis.KopisSyncWindow(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    params = kopis.build_performance_list_params(
        window,
        page=3,
        rows=50,
        after_date=date(2026, 7, 10),
    )

    assert params == {
        "stdate": "20260701",
        "eddate": "20260731",
        "cpage": "3",
        "rows": "50",
        "shcate": "CCCA",
        "afterdate": "20260710",
    }


def test_sync_window_normalizes_the_genre_code():
    window = kopis.KopisSyncWindow(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        genre_code=" CCCA ",
    )

    assert kopis.build_performance_list_params(window)["shcate"] == "CCCA"


def test_build_facility_list_params_matches_v5_filters():
    params = kopis.build_facility_list_params(
        page=2,
        rows=50,
        name=" 예술의전당 ",
        characteristic_code="2",
        region_code="11",
        district_code="1165",
        after_date=date(2026, 7, 1),
    )

    assert params == {
        "cpage": "2",
        "rows": "50",
        "shprfnmfct": "예술의전당",
        "fcltychartr": "2",
        "signgucode": "11",
        "signgucodesub": "1165",
        "afterdate": "20260701",
    }


def test_parse_performance_list_returns_typed_summaries():
    performances = kopis.parse_performance_list(LIST_XML)

    assert [item.performance_id for item in performances] == ["PF300001", "PF300002"]
    assert performances[0].start_date == date(2026, 7, 18)
    assert performances[0].facility_name == "예술의전당 콘서트홀"
    assert performances[0].genre_name == "서양음악(클래식)"
    assert performances[0].open_run is False
    assert performances[0].raw_payload["mt20id"] == "PF300001"


def test_parse_performance_detail_keeps_images_and_booking_links():
    performance = kopis.parse_performance_detail(DETAIL_XML)

    assert performance.performance_id == "PF300001"
    assert performance.facility_id == "FC000001"
    assert performance.hall_id == "FC000001-01"
    assert performance.schedule_text == "토요일(17:00)"
    assert performance.intro_image_urls == (
        "https://kopis.or.kr/intros/PF300001-1.jpg",
        "https://kopis.or.kr/intros/PF300001-2.jpg",
    )
    assert [(link.name, link.url) for link in performance.booking_links] == [
        ("NOL 티켓", "https://tickets.example/PF300001"),
        ("공연장", "https://venue.example/PF300001"),
    ]
    assert performance.raw_payload["relates"]["relate"][0]["relatenm"] == "NOL 티켓"


def test_parse_facility_list_returns_typed_summaries():
    facilities = kopis.parse_facility_list(FACILITY_LIST_XML)

    assert len(facilities) == 1
    assert facilities[0].facility_id == "FC000001"
    assert facilities[0].name == "예술의전당"
    assert facilities[0].hall_count == 6
    assert facilities[0].city == "서울"
    assert facilities[0].district == "서초구"
    assert facilities[0].opening_year == 1988


def test_parse_facility_detail_keeps_halls_location_and_accessibility():
    facility = kopis.parse_facility_detail(FACILITY_DETAIL_XML)

    assert facility.facility_id == "FC000001"
    assert facility.seat_count == 12044
    assert facility.latitude == pytest.approx(37.4781)
    assert facility.longitude == pytest.approx(127.0118)
    assert facility.has_nursing_room is True
    assert facility.has_accessible_parking is True
    assert facility.has_parking is True
    assert len(facility.halls) == 1
    assert facility.halls[0].hall_id == "FC000001-01"
    assert facility.halls[0].name == "콘서트홀"
    assert facility.halls[0].seat_count == 2523
    assert facility.halls[0].has_orchestra_pit is True
    assert facility.halls[0].disabled_seat_count == 20


def test_parse_performance_list_raises_api_error_for_invalid_key():
    with pytest.raises(kopis.KopisApiError) as error:
        kopis.parse_performance_list(INVALID_KEY_XML)

    assert error.value.code == "02"
    assert "SERVICE KEY" in str(error.value)


def test_parse_performance_list_treats_no_data_as_an_empty_page():
    assert kopis.parse_performance_list(NO_DATA_XML) == ()


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("05", "최대 31일까지 조회가능합니다."),
        ("06", "최대 조회수는 100건까지 가능합니다."),
    ],
)
def test_parse_performance_list_preserves_documented_limit_errors(
    code: str,
    message: str,
):
    payload = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        f"<dbs><db><returncode>{code}</returncode>"
        f"<errmsg>{message}</errmsg></db></dbs>"
    )

    with pytest.raises(kopis.KopisApiError) as error:
        kopis.parse_performance_list(payload)

    assert error.value.code == code
    assert error.value.message == message


def test_client_retries_temporary_server_errors_before_parsing_response():
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            return httpx.Response(503, text="temporarily unavailable")
        return httpx.Response(200, text=LIST_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key", max_retries=3),
        http_client=http_client,
        sleep=delays.append,
    )

    performances = client.list_performances(
        kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31)),
        rows=2,
    )

    assert len(performances) == 2
    assert attempts == 4
    assert delays == [0.25, 0.5, 1.0]

    http_client.close()


def test_client_retries_a_transient_bad_request_before_parsing_response():
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(400, text="temporarily rejected")
        return httpx.Response(200, text=LIST_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key", max_retries=1),
        http_client=http_client,
        sleep=delays.append,
    )

    performances = client.list_performances(
        kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31)),
        rows=2,
    )

    assert len(performances) == 2
    assert attempts == 2
    assert delays == [0.25]

    http_client.close()


def test_transport_error_exposes_http_status_without_leaking_request_key():
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(403, text="forbidden")
    )) as http_client:
        client = kopis.KopisClient(kopis.KopisSettings(api_key="private-key"), http_client=http_client)
        with pytest.raises(kopis.KopisTransportError) as raised:
            client.get_performance_detail("PF1")
    assert raised.value.status_code == 403
    assert "private-key" not in str(raised.value)


def test_client_iterates_until_the_last_partial_page():
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["cpage"])
        requested_pages.append(page)
        return httpx.Response(200, text=LIST_XML if page == 1 else LAST_PAGE_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    performances = tuple(
        client.iter_performances(
            kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31)),
            rows=2,
        )
    )

    assert [item.performance_id for item in performances] == [
        "PF300001",
        "PF300002",
        "PF300003",
    ]
    assert requested_pages == [1, 2]

    http_client.close()


def test_client_fails_loudly_when_kopis_repeats_a_full_page():
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_pages.append(int(request.url.params["cpage"]))
        return httpx.Response(200, text=LIST_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    with pytest.raises(kopis.KopisResponseError, match="repeated page"):
        tuple(
            client.iter_performances(
                kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31)),
                rows=2,
            )
        )

    assert requested_pages == [1, 2]

    http_client.close()


def test_client_fetches_performance_detail_by_kopis_id():
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, text=DETAIL_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    performance = client.get_performance_detail("PF300001")

    assert performance.performance_id == "PF300001"
    assert requested_paths == ["/openApi/restful/pblprfr/PF300001"]

    http_client.close()


def test_client_uses_the_documented_facility_paths_and_filters():
    requested: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append((request.url.path, dict(request.url.params)))
        payload = (
            FACILITY_DETAIL_XML
            if request.url.path.endswith("/FC000001")
            else FACILITY_LIST_XML
        )
        return httpx.Response(200, text=payload)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    facilities = client.list_facilities(
        page=2,
        rows=50,
        name="예술의전당",
        region_code="11",
    )
    detail = client.get_facility_detail("FC000001")

    assert facilities[0].facility_id == "FC000001"
    assert detail.halls[0].hall_id == "FC000001-01"
    assert requested[0][0] == "/openApi/restful/prfplc"
    assert requested[0][1]["service"] == "test-key"
    assert requested[0][1]["shprfnmfct"] == "예술의전당"
    assert requested[0][1]["signgucode"] == "11"
    assert requested[1][0] == "/openApi/restful/prfplc/FC000001"

    http_client.close()


def test_client_iterates_facilities_until_an_empty_page():
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["cpage"])
        requested_pages.append(page)
        return httpx.Response(200, text=FACILITY_LIST_XML if page == 1 else NO_DATA_XML)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    facilities = tuple(client.iter_facilities(rows=1))

    assert [facility.facility_id for facility in facilities] == ["FC000001"]
    assert requested_pages == [1, 2]

    http_client.close()


def test_client_context_manager_does_not_close_an_injected_http_client():
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: None))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="test-key"),
        http_client=http_client,
    )

    with client as opened_client:
        assert opened_client is client

    assert http_client.is_closed is False
    http_client.close()


def test_client_does_not_chain_an_http_error_containing_the_api_key():
    http_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(400, text="bad request")
        )
    )
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="secret-test-key", max_retries=1),
        http_client=http_client,
    )

    with pytest.raises(kopis.KopisTransportError) as error:
        client.list_performances(
            kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31))
        )

    assert error.value.__cause__ is None
    assert "secret-test-key" not in str(error.value)
    http_client.close()


def test_client_does_not_chain_a_transport_error_containing_the_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="secret-test-key", max_retries=1),
        http_client=http_client,
        sleep=lambda delay: None,
    )

    with pytest.raises(kopis.KopisTransportError) as error:
        client.list_performances(
            kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31))
        )

    assert error.value.__cause__ is None
    assert "secret-test-key" not in str(error.value)
    http_client.close()


def test_client_does_not_follow_a_redirect_away_from_kopis():
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "kopis.or.kr":
            return httpx.Response(
                302,
                headers={"location": "https://attacker.example/collect"},
            )
        return httpx.Response(200, text=LIST_XML)

    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    client = kopis.KopisClient(
        kopis.KopisSettings(api_key="secret-test-key", max_retries=0),
        http_client=http_client,
    )

    with pytest.raises(kopis.KopisTransportError, match="HTTP 302"):
        client.list_performances(
            kopis.KopisSyncWindow(date(2026, 7, 1), date(2026, 7, 31))
        )

    assert requested_hosts == ["kopis.or.kr"]
    http_client.close()


def test_settings_allow_zero_retries_for_a_single_attempt():
    settings = kopis.KopisSettings(api_key="test-key", max_retries=0)

    assert settings.max_retries == 0


def test_settings_reject_a_base_url_outside_the_official_kopis_host():
    with pytest.raises(kopis.KopisConfigurationError, match="official KOPIS"):
        kopis.KopisSettings(
            api_key="secret-test-key",
            base_url="https://attacker.example/openApi/restful",
        )


def test_settings_require_a_kopis_api_key():
    with pytest.raises(kopis.KopisConfigurationError, match="KOPIS_API_KEY"):
        kopis.KopisSettings.from_env({})
