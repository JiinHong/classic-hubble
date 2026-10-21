from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from .kopis import (
    KopisBookingLink,
    KopisClient,
    KopisFacilityDetail,
    KopisHallDetail,
    KopisPerformanceDetail,
    KopisPerformanceSummary,
    KopisSyncWindow,
)
from .nol import NolError, NolPerformanceData, extract_nol_goods_code
from .work_matching import CanonicalWork, match_work


KOREA_TIMEZONE = ZoneInfo("Asia/Seoul")
TIME_PATTERN = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)")
CITY_NAMES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


class SyncRepository(Protocol):
    def load_work_catalog(self) -> list[CanonicalWork]: ...

    def start_ingestion_run(self, provider: str) -> str: ...

    def finish_ingestion_run(
        self,
        run_id: str,
        *,
        status: str,
        counters: Mapping[str, int],
        error: str | None = None,
    ) -> None: ...

    def upsert_provider_record(
        self,
        *,
        entity_type: str,
        provider_id: str,
        payload: Mapping[str, object],
        ingestion_run_id: str,
        provider: str = "kopis",
    ) -> str: ...

    def upsert_venue(self, payload: Mapping[str, object]) -> str: ...

    def upsert_hall(self, payload: Mapping[str, object]) -> str: ...

    def upsert_performance(self, payload: Mapping[str, object]) -> str: ...

    def upsert_poster_review_item(self, payload: Mapping[str, object]) -> str: ...

    def update_performance_program_source(
        self,
        performance_id: str,
        payload: Mapping[str, object],
    ) -> None: ...

    def replace_program_items(
        self,
        performance_id: str,
        source_provider: str,
        items: Sequence[Mapping[str, object]],
    ) -> None: ...


class NolClientProtocol(Protocol):
    def fetch(self, url: str) -> NolPerformanceData: ...


@dataclass(frozen=True)
class KopisSyncResult:
    run_id: str
    status: str
    counters: dict[str, int]


def split_sync_windows(start_date: date, end_date: date) -> tuple[KopisSyncWindow, ...]:
    if end_date < start_date:
        raise ValueError("KOPIS sync end date cannot precede the start date")

    windows: list[KopisSyncWindow] = []
    cursor = start_date
    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=30), end_date)
        windows.append(KopisSyncWindow(cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return tuple(windows)


def map_venue(
    detail: KopisFacilityDetail,
    *,
    area: str | None,
    booking_links: Sequence[KopisBookingLink],
) -> dict[str, object]:
    return {
        "kopis_facility_id": detail.facility_id,
        "name": detail.name,
        "city": _city_name(area, detail.address),
        "booking_channels": _booking_channel_names(booking_links),
        "address": detail.address,
        "phone": detail.phone,
        "homepage_url": detail.homepage_url,
        "latitude": detail.latitude,
        "longitude": detail.longitude,
        "seat_count": detail.seat_count,
        "hall_count": detail.hall_count,
        "characteristic": detail.characteristic,
        "opening_year": detail.opening_year,
        "amenities": {
            "restaurant": detail.has_restaurant,
            "cafe": detail.has_cafe,
            "store": detail.has_store,
            "playroom": detail.has_playroom,
            "nursing_room": detail.has_nursing_room,
            "parking": detail.has_parking,
        },
        "accessibility": {
            "parking": detail.has_accessible_parking,
            "restroom": detail.has_accessible_restroom,
            "ramp": detail.has_accessible_ramp,
            "elevator": detail.has_accessible_elevator,
        },
        "raw_payload": detail.raw_payload,
    }


def map_hall(detail: KopisHallDetail, *, venue_id: str) -> dict[str, object]:
    return {
        "venue_id": venue_id,
        "kopis_hall_id": detail.hall_id,
        "name": detail.name,
        "seat_count": detail.seat_count,
        "disabled_seat_count": detail.disabled_seat_count,
        "stage_metadata": {
            "area": detail.stage_area,
            "orchestra_pit": detail.has_orchestra_pit,
            "rehearsal_room": detail.has_rehearsal_room,
            "dressing_room": detail.has_dressing_room,
            "outdoor_stage": detail.has_outdoor_stage,
        },
        "raw_payload": detail.raw_payload,
    }


def map_performance(
    summary: KopisPerformanceSummary,
    detail: KopisPerformanceDetail,
    *,
    venue_id: str | None,
    venue_hall_id: str | None,
) -> dict[str, object]:
    starts_at = datetime.combine(
        detail.start_date,
        _first_schedule_time(detail.schedule_text),
        tzinfo=KOREA_TIMEZONE,
    )
    booking_links = [
        {"name": item.name, "url": item.url} for item in detail.booking_links
    ]
    return {
        "kopis_performance_id": detail.performance_id,
        "venue_id": venue_id,
        "venue_hall_id": venue_hall_id,
        "title": detail.title,
        "starts_at": starts_at.isoformat(),
        "starts_on": detail.start_date.isoformat(),
        "ends_on": detail.end_date.isoformat(),
        "status": _performance_status(detail.state),
        "artists": _split_people(detail.cast),
        "price_range": detail.price,
        "booking_url": detail.booking_links[0].url if detail.booking_links else None,
        "booking_links": booking_links,
        "poster_url": detail.poster_url or summary.poster_url,
        "intro_image_urls": list(detail.intro_image_urls),
        "source_label": "KOPIS Open API",
        "schedule_text": detail.schedule_text,
        "runtime_text": detail.runtime,
        "age_text": detail.age,
        "synopsis": detail.synopsis,
        "provider_updated_at": _provider_datetime(detail.updated_at),
        "raw_payload": {
            "summary": summary.raw_payload,
            "detail": detail.raw_payload,
        },
    }


class KopisSyncService:
    def __init__(
        self,
        client: KopisClient,
        repository: SyncRepository,
        *,
        nol_client: NolClientProtocol | None = None,
    ):
        self._client = client
        self._repository = repository
        self._nol_client = nol_client

    def run(
        self,
        *,
        start_date: date,
        end_date: date,
        rows: int = 100,
        limit: int | None = None,
    ) -> KopisSyncResult:
        if not 1 <= rows <= 100:
            raise ValueError("KOPIS rows must be between 1 and 100")
        if limit is not None and limit <= 0:
            raise ValueError("KOPIS sync limit must be positive")

        windows = split_sync_windows(start_date, end_date)
        counters = {
            "performance_summaries": 0,
            "performance_details": 0,
            "facilities": 0,
            "halls": 0,
            "performances": 0,
            "review_items": 0,
            "nol_records": 0,
            "program_items": 0,
            "nol_errors": 0,
        }
        run_id = self._repository.start_ingestion_run("kopis")
        facility_cache: dict[str, tuple[str, dict[str, str]]] = {}
        seen_performances: set[str] = set()
        work_catalog: list[CanonicalWork] | None = None
        first_nol_error: str | None = None

        try:
            for window in windows:
                for summary in self._client.iter_performances(window, rows=rows):
                    if summary.performance_id in seen_performances:
                        continue
                    if limit is not None and len(seen_performances) >= limit:
                        break
                    seen_performances.add(summary.performance_id)

                    self._repository.upsert_provider_record(
                        entity_type="performance_summary",
                        provider_id=summary.performance_id,
                        payload=summary.raw_payload,
                        ingestion_run_id=run_id,
                    )
                    counters["performance_summaries"] += 1

                    detail = self._client.get_performance_detail(summary.performance_id)
                    self._repository.upsert_provider_record(
                        entity_type="performance_detail",
                        provider_id=detail.performance_id,
                        payload=detail.raw_payload,
                        ingestion_run_id=run_id,
                    )
                    counters["performance_details"] += 1

                    venue_id: str | None = None
                    hall_id: str | None = None
                    if detail.facility_id is not None:
                        if detail.facility_id not in facility_cache:
                            facility = self._client.get_facility_detail(
                                detail.facility_id
                            )
                            self._repository.upsert_provider_record(
                                entity_type="facility_detail",
                                provider_id=facility.facility_id,
                                payload=facility.raw_payload,
                                ingestion_run_id=run_id,
                            )
                            venue_id = self._repository.upsert_venue(
                                map_venue(
                                    facility,
                                    area=detail.area,
                                    booking_links=detail.booking_links,
                                )
                            )
                            counters["facilities"] += 1

                            hall_ids: dict[str, str] = {}
                            for hall in facility.halls:
                                self._repository.upsert_provider_record(
                                    entity_type="hall_detail",
                                    provider_id=hall.hall_id,
                                    payload=hall.raw_payload,
                                    ingestion_run_id=run_id,
                                )
                                hall_ids[hall.hall_id] = self._repository.upsert_hall(
                                    map_hall(hall, venue_id=venue_id)
                                )
                                counters["halls"] += 1
                            facility_cache[detail.facility_id] = (
                                venue_id,
                                hall_ids,
                            )

                        venue_id, hall_ids = facility_cache[detail.facility_id]
                        if detail.hall_id is not None:
                            hall_id = hall_ids.get(detail.hall_id)

                    performance_id = self._repository.upsert_performance(
                        map_performance(
                            summary,
                            detail,
                            venue_id=venue_id,
                            venue_hall_id=hall_id,
                        )
                    )
                    counters["performances"] += 1

                    if (
                        self._nol_client is not None
                        and (nol_url := _first_nol_goods_url(detail.booking_links))
                        is not None
                    ):
                        try:
                            nol_data = self._nol_client.fetch(nol_url)
                        except NolError as error:
                            counters["nol_errors"] += 1
                            if first_nol_error is None:
                                first_nol_error = f"{type(error).__name__}: {error}"[
                                    :500
                                ]
                        else:
                            self._repository.upsert_provider_record(
                                provider="nol",
                                entity_type="performance_detail",
                                provider_id=nol_data.goods_code,
                                payload=_nol_raw_payload(nol_data),
                                ingestion_run_id=run_id,
                            )
                            counters["nol_records"] += 1
                            if work_catalog is None:
                                work_catalog = self._repository.load_work_catalog()
                            program_items = _map_nol_program_items(
                                nol_data, work_catalog
                            )
                            self._repository.replace_program_items(
                                performance_id,
                                "nol",
                                program_items,
                            )
                            self._repository.update_performance_program_source(
                                performance_id,
                                {
                                    "program_status": nol_data.program_status,
                                    "program_source_url": nol_data.program_source_url,
                                    "program_image_urls": list(
                                        nol_data.program_image_urls
                                    ),
                                },
                            )
                            counters["program_items"] += len(program_items)

                    for image_url in detail.intro_image_urls:
                        self._repository.upsert_poster_review_item(
                            {
                                "performance_id": performance_id,
                                "image_url": image_url,
                                "state": "needs_review",
                            }
                        )
                        counters["review_items"] += 1

                if limit is not None and len(seen_performances) >= limit:
                    break
        except Exception as error:
            self._repository.finish_ingestion_run(
                run_id,
                status="failed",
                counters=counters,
                error=str(error)[:2000],
            )
            raise

        status = "failed" if counters["nol_errors"] else "completed"
        self._repository.finish_ingestion_run(
            run_id,
            status=status,
            counters=counters,
            error=(
                f"NOL: {counters['nol_errors']} failed, {counters['nol_records']} succeeded. First error: {first_nol_error}"
                if first_nol_error
                else None
            ),
        )
        return KopisSyncResult(
            run_id=run_id,
            status=status,
            counters=counters,
        )


def _first_schedule_time(schedule_text: str | None) -> time:
    if schedule_text is not None and (match := TIME_PATTERN.search(schedule_text)):
        return time(hour=int(match.group(1)), minute=int(match.group(2)))
    return time.min


def _split_people(value: str | None) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in re.split(r"[,，]", value) if part.strip()]


def _performance_status(value: str | None) -> str:
    if value is None:
        return "upcoming"
    normalized = value.strip()
    if "매진" in normalized:
        return "soldout"
    if normalized == "공연중":
        return "open"
    if normalized == "공연예정":
        return "upcoming"
    if normalized in {"공연완료", "공연취소", "폐막"}:
        return "closed"
    return "upcoming"


def _booking_channel_names(
    booking_links: Sequence[KopisBookingLink],
) -> list[str]:
    names: list[str] = []
    for item in booking_links:
        if item.name is not None and item.name not in names:
            names.append(item.name)
    return names


def _city_name(area: str | None, address: str | None) -> str:
    candidate = (area or "").strip()
    if not candidate and address:
        candidate = address.strip().split(maxsplit=1)[0]
    return CITY_NAMES.get(candidate, candidate or "미상")


def _provider_datetime(value: str | None) -> str | None:
    if value is None:
        return None
    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(value, date_format)
        except ValueError:
            continue
        return parsed.replace(tzinfo=KOREA_TIMEZONE).isoformat()
    return None


def _first_nol_goods_url(
    booking_links: Sequence[KopisBookingLink],
) -> str | None:
    for item in booking_links:
        if extract_nol_goods_code(item.url) is not None:
            return item.url
    return None


def _nol_raw_payload(nol_data: NolPerformanceData) -> dict[str, object]:
    payload: dict[str, object] = {"summary": dict(nol_data.raw_summary)}
    payload["play_db"] = (
        dict(nol_data.raw_play_db) if nol_data.raw_play_db is not None else None
    )
    return payload


def _map_nol_program_items(
    nol_data: NolPerformanceData, works: Sequence[CanonicalWork]
) -> list[dict[str, object]]:
    return [
        {
            "work_id": match_work(item.work_title, item.composer, works).work_id,
            "display_title": item.work_title,
            "composer_name": item.composer,
            "source_type": "official",
            "confidence": 0.98,
            "position": item.position,
            "source_url": nol_data.program_source_url,
        }
        for item in nol_data.program_items
    ]
