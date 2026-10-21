from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from classic_hubble_pipeline.kopis import (
    KopisBookingLink,
    KopisFacilityDetail,
    KopisHallDetail,
    KopisPerformanceDetail,
    KopisPerformanceSummary,
)
from classic_hubble_pipeline.kopis_sync import (
    KopisSyncService,
    map_performance,
    map_venue,
    split_sync_windows,
)
from classic_hubble_pipeline.nol import (
    NolPerformanceData,
    NolProgramItem,
    NolTransportError,
)
from classic_hubble_pipeline.work_matching import CanonicalWork


def performance_summary(performance_id: str = "PF300001") -> KopisPerformanceSummary:
    return KopisPerformanceSummary(
        performance_id=performance_id,
        title="라흐마니노프 피아노 협주곡 2번",
        start_date=date(2026, 7, 18),
        end_date=date(2026, 7, 18),
        facility_name="예술의전당 콘서트홀",
        poster_url="https://kopis.or.kr/posters/PF300001.jpg",
        area="서울특별시",
        genre_name="서양음악(클래식)",
        open_run=False,
        state="공연예정",
        raw_payload={"mt20id": performance_id, "source": "summary"},
    )


def performance_detail(performance_id: str = "PF300001") -> KopisPerformanceDetail:
    return KopisPerformanceDetail(
        performance_id=performance_id,
        title="라흐마니노프 피아노 협주곡 2번",
        facility_id="FC000001",
        hall_id="FC000001-01",
        facility_name="예술의전당 콘서트홀",
        registered_at="2026-06-01 09:00:00",
        start_date=date(2026, 7, 18),
        end_date=date(2026, 7, 18),
        cast="홍길동, 클래식 허블 오케스트라",
        crew="지휘 김지휘",
        runtime="120분",
        age="8세 이상",
        producer="클래식 허블",
        price="R석 100,000원, S석 70,000원",
        poster_url="https://kopis.or.kr/posters/PF300001.jpg",
        synopsis="공연 소개",
        area="서울특별시",
        genre_name="서양음악(클래식)",
        open_run=False,
        updated_at="2026-07-01 13:00:00",
        state="공연예정",
        schedule_text="토요일(17:00)",
        intro_image_urls=(
            "https://kopis.or.kr/intros/PF300001-1.jpg",
            "https://kopis.or.kr/intros/PF300001-2.jpg",
        ),
        booking_links=(
            KopisBookingLink(
                name="NOL 티켓",
                url="https://tickets.example/PF300001",
            ),
        ),
        raw_payload={"mt20id": performance_id, "source": "detail"},
    )


def facility_detail() -> KopisFacilityDetail:
    hall = KopisHallDetail(
        hall_id="FC000001-01",
        name="콘서트홀",
        seat_count=2523,
        has_orchestra_pit=True,
        has_rehearsal_room=True,
        has_dressing_room=True,
        has_outdoor_stage=False,
        disabled_seat_count=20,
        stage_area="360㎡",
        raw_payload={"mt13id": "FC000001-01"},
    )
    return KopisFacilityDetail(
        facility_id="FC000001",
        name="예술의전당",
        hall_count=1,
        characteristic="문예회관",
        opening_year=1988,
        seat_count=2523,
        phone="02-580-1300",
        homepage_url="https://www.sac.or.kr/",
        address="서울특별시 서초구 남부순환로 2406",
        latitude=37.4781,
        longitude=127.0118,
        has_restaurant=True,
        has_cafe=True,
        has_store=True,
        has_playroom=False,
        has_nursing_room=True,
        has_accessible_parking=True,
        has_accessible_restroom=True,
        has_accessible_ramp=True,
        has_accessible_elevator=True,
        has_parking=True,
        halls=(hall,),
        raw_payload={"mt10id": "FC000001"},
    )


def test_split_sync_windows_never_exceeds_31_calendar_days():
    windows = split_sync_windows(date(2026, 7, 1), date(2026, 9, 2))

    assert [(item.start_date, item.end_date) for item in windows] == [
        (date(2026, 7, 1), date(2026, 7, 31)),
        (date(2026, 8, 1), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 2)),
    ]


def test_performance_mapping_preserves_provider_detail_and_korean_time():
    mapped = map_performance(
        performance_summary(),
        performance_detail(),
        venue_id="venue-1",
        venue_hall_id="hall-1",
    )

    assert mapped["kopis_performance_id"] == "PF300001"
    assert mapped["starts_at"] == "2026-07-18T17:00:00+09:00"
    assert mapped["starts_on"] == "2026-07-18"
    assert mapped["ends_on"] == "2026-07-18"
    assert mapped["status"] == "upcoming"
    assert mapped["artists"] == ["홍길동", "클래식 허블 오케스트라"]
    assert mapped["booking_url"] == "https://tickets.example/PF300001"
    assert mapped["schedule_text"] == "토요일(17:00)"
    assert mapped["raw_payload"] == {
        "summary": {"mt20id": "PF300001", "source": "summary"},
        "detail": {"mt20id": "PF300001", "source": "detail"},
    }


def test_venue_mapping_keeps_facility_metadata_and_booking_channels():
    mapped = map_venue(
        facility_detail(),
        area="서울특별시",
        booking_links=performance_detail().booking_links,
    )

    assert mapped["kopis_facility_id"] == "FC000001"
    assert mapped["city"] == "서울"
    assert mapped["booking_channels"] == ["NOL 티켓"]
    assert mapped["accessibility"] == {
        "parking": True,
        "restroom": True,
        "ramp": True,
        "elevator": True,
    }
    assert mapped["raw_payload"] == {"mt10id": "FC000001"}


def test_sync_writes_raw_records_before_normalized_rows_and_deduplicates_facilities():
    summaries = (performance_summary(), performance_summary("PF300002"))
    details = {
        item.performance_id: performance_detail(item.performance_id)
        for item in summaries
    }
    events: list[tuple[object, ...]] = []

    class FakeClient:
        facility_requests = 0

        def iter_performances(self, window, *, rows):
            assert rows == 100
            return iter(summaries)

        def get_performance_detail(self, performance_id):
            return details[performance_id]

        def get_facility_detail(self, facility_id):
            self.facility_requests += 1
            return facility_detail()

    class FakeRepository:
        def start_ingestion_run(self, provider):
            events.append(("start", provider))
            return "run-1"

        def upsert_provider_record(
            self, *, entity_type, provider_id, payload, ingestion_run_id
        ):
            events.append(("raw", entity_type, provider_id))
            return f"raw-{provider_id}"

        def upsert_venue(self, payload):
            events.append(("venue", payload["kopis_facility_id"]))
            return "venue-1"

        def upsert_hall(self, payload):
            events.append(("hall", payload["kopis_hall_id"]))
            return "hall-1"

        def upsert_performance(self, payload):
            events.append(("performance", payload["kopis_performance_id"]))
            return f"db-{payload['kopis_performance_id']}"

        def upsert_poster_review_item(self, payload):
            events.append(("review", payload["image_url"]))
            return "review-1"

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            events.append(("finish", run_id, status, counters, error))

    client = FakeClient()
    result = KopisSyncService(client, FakeRepository()).run(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    first_performance_index = events.index(("performance", "PF300001"))
    assert (
        events.index(("raw", "performance_summary", "PF300001"))
        < first_performance_index
    )
    assert (
        events.index(("raw", "performance_detail", "PF300001"))
        < first_performance_index
    )
    assert events.index(("raw", "facility_detail", "FC000001")) < events.index(
        ("venue", "FC000001")
    )
    assert events.index(("raw", "hall_detail", "FC000001-01")) < events.index(
        ("hall", "FC000001-01")
    )
    assert client.facility_requests == 1
    assert result.status == "completed"
    assert result.counters == {
        "performance_summaries": 2,
        "performance_details": 2,
        "facilities": 1,
        "halls": 1,
        "performances": 2,
        "review_items": 4,
        "nol_records": 0,
        "program_items": 0,
        "nol_errors": 0,
    }
    assert events[-1][0:3] == ("finish", "run-1", "completed")


def test_sync_marks_the_ingestion_run_failed_before_reraising():
    events: list[tuple[object, ...]] = []

    class FailingClient:
        def iter_performances(self, window, *, rows):
            raise RuntimeError("provider unavailable")

    class FakeRepository:
        def start_ingestion_run(self, provider):
            return "run-1"

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            events.append((run_id, status, counters, error))

    with pytest.raises(RuntimeError, match="provider unavailable"):
        KopisSyncService(FailingClient(), FakeRepository()).run(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )

    assert events[0][0:2] == ("run-1", "failed")
    assert events[0][3] == "provider unavailable"


def test_sync_writes_nol_raw_data_before_program_rows_and_fetches_one_goods_code():
    detail = replace(
        performance_detail(),
        facility_id=None,
        hall_id=None,
        intro_image_urls=(),
        booking_links=(
            KopisBookingLink(
                name="놀유니버스",
                url=(
                    "http://ticket.interpark.com/Ticket/Goods/"
                    "GoodsInfo.asp?GoodsCode=26007299"
                ),
            ),
            KopisBookingLink(
                name="NOL 티켓",
                url="https://tickets.interpark.com/goods/26007299",
            ),
        ),
    )
    events: list[tuple[object, ...]] = []

    class FakeKopisClient:
        def iter_performances(self, window, *, rows):
            return iter((performance_summary(),))

        def get_performance_detail(self, performance_id):
            return detail

    class FakeNolClient:
        requests: list[str] = []

        def fetch(self, url):
            self.requests.append(url)
            return NolPerformanceData(
                goods_code="26007299",
                title="라흐마니노프 피아노 협주곡 2번",
                venue_name="예술의전당 콘서트홀",
                program_status="confirmed",
                program_source_url="https://tickets.interpark.com/goods/26007299",
                program_image_urls=(
                    "https://ticketimage.interpark.com/Play/program.jpg",
                ),
                program_items=(
                    NolProgramItem(
                        position=0,
                        display_title=(
                            "Sergei Rachmaninoff (1873-1943)\n"
                            "Piano Concerto No. 2 in C minor, Op. 18"
                        ),
                        composer="Sergei Rachmaninoff",
                        composer_lifespan="1873-1943",
                        work_title="Piano Concerto No. 2 in C minor, Op. 18",
                    ),
                ),
                raw_summary={"data": {"goodsCode": "26007299"}},
                raw_play_db={"data": {"programInfo": "Rachmaninoff"}},
            )

    class FakeRepository:
        def start_ingestion_run(self, provider):
            return "run-1"

        def upsert_provider_record(
            self,
            *,
            entity_type,
            provider_id,
            payload,
            ingestion_run_id,
            provider="kopis",
        ):
            events.append(("raw", provider, entity_type, provider_id, payload))
            return f"raw-{provider_id}"

        def upsert_performance(self, payload):
            events.append(("performance", payload["kopis_performance_id"]))
            return "db-performance-1"

        def update_performance_program_source(self, performance_id, payload):
            events.append(("program_source", performance_id, payload))

        def replace_program_items(self, performance_id, source_provider, items):
            events.append(
                ("program_items", performance_id, source_provider, tuple(items))
            )

        def load_work_catalog(self):
            return [
                CanonicalWork(
                    "work-rach",
                    "rach-2",
                    ("Piano Concerto No. 2",),
                    ("Sergei Rachmaninoff",),
                    "Op. 18",
                )
            ]

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            events.append(("finish", status, counters, error))

    nol_client = FakeNolClient()
    result = KopisSyncService(
        FakeKopisClient(), FakeRepository(), nol_client=nol_client
    ).run(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    assert nol_client.requests == [detail.booking_links[0].url]
    nol_raw_index = next(
        index
        for index, event in enumerate(events)
        if event[:4] == ("raw", "nol", "performance_detail", "26007299")
    )
    source_index = next(
        index for index, event in enumerate(events) if event[0] == "program_source"
    )
    items_index = next(
        index for index, event in enumerate(events) if event[0] == "program_items"
    )
    assert nol_raw_index < items_index < source_index

    source_payload = events[source_index][2]
    assert source_payload == {
        "program_status": "confirmed",
        "program_source_url": "https://tickets.interpark.com/goods/26007299",
        "program_image_urls": ["https://ticketimage.interpark.com/Play/program.jpg"],
    }
    stored_item = events[items_index][3][0]
    assert stored_item == {
        "work_id": "work-rach",
        "display_title": "Piano Concerto No. 2 in C minor, Op. 18",
        "composer_name": "Sergei Rachmaninoff",
        "source_type": "official",
        "confidence": 0.98,
        "position": 0,
        "source_url": "https://tickets.interpark.com/goods/26007299",
    }
    assert result.counters["nol_records"] == 1
    assert result.counters["program_items"] == 1
    assert result.counters["nol_errors"] == 0


def test_nol_failure_is_counted_without_discarding_the_kopis_performance():
    detail = replace(
        performance_detail(),
        facility_id=None,
        hall_id=None,
        intro_image_urls=(),
        booking_links=(
            KopisBookingLink(
                name="놀유니버스",
                url="https://tickets.interpark.com/goods/26007299",
            ),
        ),
    )
    events: list[tuple[object, ...]] = []

    class FakeKopisClient:
        def iter_performances(self, window, *, rows):
            return iter((performance_summary(),))

        def get_performance_detail(self, performance_id):
            return detail

    class FailingNolClient:
        def fetch(self, url):
            raise NolTransportError("temporary NOL failure")

    class FakeRepository:
        def start_ingestion_run(self, provider):
            return "run-1"

        def upsert_provider_record(self, **kwargs):
            events.append(("raw", kwargs.get("provider", "kopis")))
            return "raw-1"

        def upsert_performance(self, payload):
            events.append(("performance", payload["kopis_performance_id"]))
            return "db-performance-1"

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            events.append(("finish", status, counters, error))

    result = KopisSyncService(
        FakeKopisClient(), FakeRepository(), nol_client=FailingNolClient()
    ).run(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))

    assert ("performance", "PF300001") in events
    assert result.status == "failed"
    assert result.counters["nol_records"] == 0
    assert result.counters["program_items"] == 0
    assert result.counters["nol_errors"] == 1
    assert "NolTransportError" in events[-1][-1]
