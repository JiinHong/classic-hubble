from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote, urlparse
from xml.etree import ElementTree

import httpx


DEFAULT_BASE_URL = "https://kopis.or.kr/openApi/restful"
RETRYABLE_STATUS_CODES = frozenset({400, 429, 500, 502, 503, 504})


class KopisError(RuntimeError):
    """Base exception for KOPIS ingestion failures."""


class KopisConfigurationError(KopisError):
    """Raised when required worker configuration is missing or invalid."""


class KopisResponseError(KopisError):
    """Raised when KOPIS returns malformed or incomplete XML."""


class KopisTransportError(KopisError):
    """Raised when KOPIS cannot be reached after retrying."""

    def __init__(self, message: str, *, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class KopisApiError(KopisResponseError):
    def __init__(self, code: str, message: str, response_time: str | None = None):
        self.code = code
        self.message = message
        self.response_time = response_time
        super().__init__(f"KOPIS API error {code}: {message}")


@dataclass(frozen=True)
class KopisSettings:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 10.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.25

    def __post_init__(self) -> None:
        api_key = self.api_key.strip()
        base_url = self.base_url.strip().rstrip("/")

        if not api_key:
            raise KopisConfigurationError("KOPIS_API_KEY is required")
        if not base_url:
            raise KopisConfigurationError("KOPIS_BASE_URL cannot be empty")
        parsed_base_url = urlparse(base_url)
        try:
            port = parsed_base_url.port
        except ValueError as error:
            raise KopisConfigurationError("KOPIS_BASE_URL contains an invalid port") from error
        if (
            parsed_base_url.scheme != "https"
            or parsed_base_url.hostname not in {"kopis.or.kr", "www.kopis.or.kr"}
            or port not in {None, 443}
            or parsed_base_url.username is not None
            or parsed_base_url.password is not None
        ):
            raise KopisConfigurationError(
                "KOPIS_BASE_URL must use the official KOPIS HTTPS host"
            )
        if self.timeout_seconds <= 0:
            raise KopisConfigurationError("KOPIS_TIMEOUT_SECONDS must be positive")
        if self.max_retries < 0:
            raise KopisConfigurationError("KOPIS_MAX_RETRIES cannot be negative")
        if self.retry_backoff_seconds < 0:
            raise KopisConfigurationError("KOPIS_RETRY_BACKOFF_SECONDS cannot be negative")

        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "base_url", base_url)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> KopisSettings:
        values = os.environ if environ is None else environ
        api_key = values.get("KOPIS_API_KEY", "").strip()
        if not api_key:
            raise KopisConfigurationError("KOPIS_API_KEY is required")

        try:
            return cls(
                api_key=api_key,
                base_url=values.get("KOPIS_BASE_URL", DEFAULT_BASE_URL),
                timeout_seconds=float(values.get("KOPIS_TIMEOUT_SECONDS", "10")),
                max_retries=int(values.get("KOPIS_MAX_RETRIES", "3")),
                retry_backoff_seconds=float(
                    values.get("KOPIS_RETRY_BACKOFF_SECONDS", "0.25")
                ),
            )
        except ValueError as error:
            raise KopisConfigurationError(
                "KOPIS timeout and retry settings must be numeric"
            ) from error


@dataclass(frozen=True)
class KopisSyncWindow:
    start_date: date
    end_date: date
    genre_code: str = "CCCA"

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("KOPIS sync end date cannot precede the start date")
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("KOPIS performance-list windows cannot exceed 31 days")
        if not self.genre_code.strip():
            raise ValueError("KOPIS genre code cannot be empty")
        object.__setattr__(self, "genre_code", self.genre_code.strip())


@dataclass(frozen=True)
class KopisBookingLink:
    name: str | None
    url: str


@dataclass(frozen=True)
class KopisPerformanceSummary:
    performance_id: str
    title: str
    start_date: date
    end_date: date
    facility_name: str
    poster_url: str | None
    area: str | None
    genre_name: str | None
    open_run: bool
    state: str | None
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class KopisPerformanceDetail:
    performance_id: str
    title: str
    facility_id: str | None
    hall_id: str | None
    facility_name: str
    registered_at: str | None
    start_date: date
    end_date: date
    cast: str | None
    crew: str | None
    runtime: str | None
    age: str | None
    producer: str | None
    price: str | None
    poster_url: str | None
    synopsis: str | None
    area: str | None
    genre_name: str | None
    open_run: bool
    updated_at: str | None
    state: str | None
    schedule_text: str | None
    intro_image_urls: tuple[str, ...]
    booking_links: tuple[KopisBookingLink, ...]
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class KopisFacilitySummary:
    facility_id: str
    name: str
    hall_count: int | None
    characteristic: str | None
    city: str | None
    district: str | None
    opening_year: int | None
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class KopisHallDetail:
    hall_id: str
    name: str
    seat_count: int | None
    has_orchestra_pit: bool | None
    has_rehearsal_room: bool | None
    has_dressing_room: bool | None
    has_outdoor_stage: bool | None
    disabled_seat_count: int | None
    stage_area: str | None
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class KopisFacilityDetail:
    facility_id: str
    name: str
    hall_count: int | None
    characteristic: str | None
    opening_year: int | None
    seat_count: int | None
    phone: str | None
    homepage_url: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    has_restaurant: bool | None
    has_cafe: bool | None
    has_store: bool | None
    has_playroom: bool | None
    has_nursing_room: bool | None
    has_accessible_parking: bool | None
    has_accessible_restroom: bool | None
    has_accessible_ramp: bool | None
    has_accessible_elevator: bool | None
    has_parking: bool | None
    halls: tuple[KopisHallDetail, ...]
    raw_payload: dict[str, object]


def build_performance_list_params(
    window: KopisSyncWindow,
    *,
    page: int = 1,
    rows: int = 100,
    after_date: date | None = None,
) -> dict[str, str]:
    if not 1 <= page <= 999:
        raise ValueError("KOPIS page must be between 1 and 999")
    if not 1 <= rows <= 100:
        raise ValueError("KOPIS rows must be between 1 and 100")

    params = {
        "stdate": window.start_date.strftime("%Y%m%d"),
        "eddate": window.end_date.strftime("%Y%m%d"),
        "cpage": str(page),
        "rows": str(rows),
        "shcate": window.genre_code,
    }
    if after_date is not None:
        params["afterdate"] = after_date.strftime("%Y%m%d")
    return params


def build_facility_list_params(
    *,
    page: int = 1,
    rows: int = 100,
    name: str | None = None,
    characteristic_code: str | None = None,
    region_code: str | None = None,
    district_code: str | None = None,
    after_date: date | None = None,
) -> dict[str, str]:
    if not 1 <= page <= 999:
        raise ValueError("KOPIS page must be between 1 and 999")
    if not 1 <= rows <= 100:
        raise ValueError("KOPIS rows must be between 1 and 100")

    params = {
        "cpage": str(page),
        "rows": str(rows),
    }
    filters = {
        "shprfnmfct": name,
        "fcltychartr": characteristic_code,
        "signgucode": region_code,
        "signgucodesub": district_code,
    }
    for key, value in filters.items():
        if value is not None and (normalized := value.strip()):
            params[key] = normalized
    if after_date is not None:
        params["afterdate"] = after_date.strftime("%Y%m%d")
    return params


def parse_performance_list(
    xml_payload: str | bytes,
) -> tuple[KopisPerformanceSummary, ...]:
    root = _parse_xml(xml_payload)
    api_error = _find_api_error(root)
    if api_error is not None:
        if api_error.code == "04":
            return ()
        raise api_error

    performances: list[KopisPerformanceSummary] = []
    for record in root.findall("./db"):
        performances.append(
            KopisPerformanceSummary(
                performance_id=_required_text(record, "mt20id"),
                title=_required_text(record, "prfnm"),
                start_date=_parse_date(record, "prfpdfrom"),
                end_date=_parse_date(record, "prfpdto"),
                facility_name=_required_text(record, "fcltynm"),
                poster_url=_optional_text(record, "poster"),
                area=_optional_text(record, "area"),
                genre_name=_optional_text(record, "genrenm"),
                open_run=_optional_text(record, "openrun") == "Y",
                state=_optional_text(record, "prfstate"),
                raw_payload=_element_to_mapping(record),
            )
        )
    return tuple(performances)


def parse_performance_detail(xml_payload: str | bytes) -> KopisPerformanceDetail:
    root = _parse_xml(xml_payload)
    api_error = _find_api_error(root)
    if api_error is not None:
        raise api_error

    record = root.find("./db")
    if record is None:
        raise KopisResponseError("KOPIS detail response did not contain a record")

    image_urls = tuple(
        value
        for node in record.findall("./styurls/styurl")
        if (value := _node_text(node)) is not None
    )
    booking_links = tuple(
        KopisBookingLink(name=_optional_text(node, "relatenm"), url=url)
        for node in record.findall("./relates/relate")
        if (url := _optional_text(node, "relateurl")) is not None
    )

    return KopisPerformanceDetail(
        performance_id=_required_text(record, "mt20id"),
        title=_required_text(record, "prfnm"),
        facility_id=_optional_text(record, "mt10id"),
        hall_id=_optional_text(record, "mt13id"),
        facility_name=_required_text(record, "fcltynm"),
        registered_at=_optional_text(record, "frstregdt"),
        start_date=_parse_date(record, "prfpdfrom"),
        end_date=_parse_date(record, "prfpdto"),
        cast=_optional_text(record, "prfcast"),
        crew=_optional_text(record, "prfcrew"),
        runtime=_optional_text(record, "prfruntime"),
        age=_optional_text(record, "prfage"),
        producer=_optional_text(record, "entrpsnm"),
        price=_optional_text(record, "pcseguidance"),
        poster_url=_optional_text(record, "poster"),
        synopsis=_optional_text(record, "sty"),
        area=_optional_text(record, "area"),
        genre_name=_optional_text(record, "genrenm"),
        open_run=_optional_text(record, "openrun") == "Y",
        updated_at=_optional_text(record, "updatedate"),
        state=_optional_text(record, "prfstate"),
        schedule_text=_optional_text(record, "dtguidance"),
        intro_image_urls=image_urls,
        booking_links=booking_links,
        raw_payload=_element_to_mapping(record),
    )


def parse_facility_list(
    xml_payload: str | bytes,
) -> tuple[KopisFacilitySummary, ...]:
    root = _parse_xml(xml_payload)
    api_error = _find_api_error(root)
    if api_error is not None:
        if api_error.code == "04":
            return ()
        raise api_error

    return tuple(
        KopisFacilitySummary(
            facility_id=_required_text(record, "mt10id"),
            name=_required_text(record, "fcltynm"),
            hall_count=_optional_int(record, "mt13cnt"),
            characteristic=_optional_text(record, "fcltychartr"),
            city=_optional_text(record, "sidonm"),
            district=_optional_text(record, "gugunnm"),
            opening_year=_optional_int(record, "opende"),
            raw_payload=_element_to_mapping(record),
        )
        for record in root.findall("./db")
    )


def parse_facility_detail(xml_payload: str | bytes) -> KopisFacilityDetail:
    root = _parse_xml(xml_payload)
    api_error = _find_api_error(root)
    if api_error is not None:
        raise api_error

    record = root.find("./db")
    if record is None:
        raise KopisResponseError(
            "KOPIS facility detail response did not contain a record"
        )

    halls = tuple(
        KopisHallDetail(
            hall_id=_required_text(node, "mt13id"),
            name=_required_text(node, "prfplcnm"),
            seat_count=_optional_int(node, "seatscale"),
            has_orchestra_pit=_optional_yn(node, "stageorchat"),
            has_rehearsal_room=_optional_yn(node, "stagepracat"),
            has_dressing_room=_optional_yn(node, "stagedresat"),
            has_outdoor_stage=_optional_yn(node, "stageoutdrat"),
            disabled_seat_count=_optional_int(node, "disabledseatscale"),
            stage_area=_optional_text(node, "stagearea"),
            raw_payload=_element_to_mapping(node),
        )
        for node in record.findall("./mt13s/mt13")
    )

    return KopisFacilityDetail(
        facility_id=_required_text(record, "mt10id"),
        name=_required_text(record, "fcltynm"),
        hall_count=_optional_int(record, "mt13cnt"),
        characteristic=_optional_text(record, "fcltychartr"),
        opening_year=_optional_int(record, "opende"),
        seat_count=_optional_int(record, "seatscale"),
        phone=_optional_text(record, "telno"),
        homepage_url=_optional_text(record, "relateurl"),
        address=_optional_text(record, "adres"),
        latitude=_optional_float(record, "la"),
        longitude=_optional_float(record, "lo"),
        has_restaurant=_optional_yn(record, "restaurant"),
        has_cafe=_optional_yn(record, "cafe"),
        has_store=_optional_yn(record, "store"),
        has_playroom=_optional_yn(record, "nolibang"),
        has_nursing_room=_optional_yn(record, "suyu"),
        has_accessible_parking=_optional_yn(record, "parkbarrier"),
        has_accessible_restroom=_optional_yn(record, "restbarrier"),
        has_accessible_ramp=_optional_yn(record, "runwbarrier"),
        has_accessible_elevator=_optional_yn(record, "elevbarrier"),
        has_parking=_optional_yn(record, "parkinglot"),
        halls=halls,
        raw_payload=_element_to_mapping(record),
    )


class KopisClient:
    def __init__(
        self,
        settings: KopisSettings,
        *,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._settings = settings
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )
        self._sleep = sleep

    def __enter__(self) -> KopisClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def list_performances(
        self,
        window: KopisSyncWindow,
        *,
        page: int = 1,
        rows: int = 100,
        after_date: date | None = None,
    ) -> tuple[KopisPerformanceSummary, ...]:
        params = build_performance_list_params(
            window,
            page=page,
            rows=rows,
            after_date=after_date,
        )
        return parse_performance_list(self._get_xml("pblprfr", params))

    def iter_performances(
        self,
        window: KopisSyncWindow,
        *,
        rows: int = 100,
        after_date: date | None = None,
    ) -> Iterator[KopisPerformanceSummary]:
        seen_performance_ids: set[str] = set()
        for page in range(1, 1000):
            performances = self.list_performances(
                window,
                page=page,
                rows=rows,
                after_date=after_date,
            )
            new_count = 0
            for performance in performances:
                if performance.performance_id in seen_performance_ids:
                    continue
                seen_performance_ids.add(performance.performance_id)
                new_count += 1
                yield performance

            if len(performances) < rows:
                return
            if new_count == 0:
                raise KopisResponseError(
                    f"KOPIS repeated page {page} without pagination progress"
                )
        raise KopisResponseError("KOPIS pagination exceeded 999 pages")

    def get_performance_detail(self, performance_id: str) -> KopisPerformanceDetail:
        normalized_id = performance_id.strip()
        if not normalized_id:
            raise ValueError("KOPIS performance ID cannot be empty")
        path = f"pblprfr/{quote(normalized_id, safe='')}"
        return parse_performance_detail(self._get_xml(path, {}))

    def list_facilities(
        self,
        *,
        page: int = 1,
        rows: int = 100,
        name: str | None = None,
        characteristic_code: str | None = None,
        region_code: str | None = None,
        district_code: str | None = None,
        after_date: date | None = None,
    ) -> tuple[KopisFacilitySummary, ...]:
        params = build_facility_list_params(
            page=page,
            rows=rows,
            name=name,
            characteristic_code=characteristic_code,
            region_code=region_code,
            district_code=district_code,
            after_date=after_date,
        )
        return parse_facility_list(self._get_xml("prfplc", params))

    def iter_facilities(
        self,
        *,
        rows: int = 100,
        name: str | None = None,
        characteristic_code: str | None = None,
        region_code: str | None = None,
        district_code: str | None = None,
        after_date: date | None = None,
    ) -> Iterator[KopisFacilitySummary]:
        seen_facility_ids: set[str] = set()
        for page in range(1, 1000):
            facilities = self.list_facilities(
                page=page,
                rows=rows,
                name=name,
                characteristic_code=characteristic_code,
                region_code=region_code,
                district_code=district_code,
                after_date=after_date,
            )
            new_count = 0
            for facility in facilities:
                if facility.facility_id in seen_facility_ids:
                    continue
                seen_facility_ids.add(facility.facility_id)
                new_count += 1
                yield facility

            if len(facilities) < rows:
                return
            if new_count == 0:
                raise KopisResponseError(
                    f"KOPIS repeated facility page {page} without pagination progress"
                )
        raise KopisResponseError("KOPIS facility pagination exceeded 999 pages")

    def get_facility_detail(self, facility_id: str) -> KopisFacilityDetail:
        normalized_id = facility_id.strip()
        if not normalized_id:
            raise ValueError("KOPIS facility ID cannot be empty")
        path = f"prfplc/{quote(normalized_id, safe='')}"
        return parse_facility_detail(self._get_xml(path, {}))

    def _get_xml(self, path: str, params: Mapping[str, str]) -> str:
        request_params = {"service": self._settings.api_key, **params}
        url = f"{self._settings.base_url}/{path.lstrip('/')}"

        for attempt in range(self._settings.max_retries + 1):
            try:
                response = self._http_client.get(
                    url,
                    params=request_params,
                    follow_redirects=False,
                )
            except httpx.TransportError:
                if attempt == self._settings.max_retries:
                    raise KopisTransportError(
                        f"KOPIS request failed after retrying: {path}"
                    ) from None
            else:
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError:
                        raise KopisTransportError(
                            f"KOPIS returned HTTP {response.status_code}: {path}",
                            status_code=response.status_code,
                        ) from None
                    return response.text

                if attempt == self._settings.max_retries:
                    raise KopisTransportError(
                        f"KOPIS remained unavailable with HTTP {response.status_code}: {path}",
                        status_code=response.status_code,
                    )

            if attempt < self._settings.max_retries:
                delay = self._settings.retry_backoff_seconds * (2**attempt)
                self._sleep(delay)

        raise KopisTransportError("KOPIS request failed after retrying")


def _parse_xml(xml_payload: str | bytes) -> ElementTree.Element:
    try:
        root = ElementTree.fromstring(xml_payload)
    except ElementTree.ParseError as error:
        raise KopisResponseError("KOPIS returned malformed XML") from error
    if root.tag != "dbs":
        raise KopisResponseError(f"Unexpected KOPIS XML root: {root.tag}")
    return root


def _find_api_error(root: ElementTree.Element) -> KopisApiError | None:
    for record in root.findall("./db"):
        code = _optional_text(record, "returncode")
        if code is None or code == "00":
            continue
        message = _optional_text(record, "errmsg") or "Unknown KOPIS error"
        return KopisApiError(
            code=code,
            message=message,
            response_time=_optional_text(record, "responsetime"),
        )
    return None


def _parse_date(record: ElementTree.Element, field: str) -> date:
    raw_value = _required_text(record, field)
    try:
        return date.fromisoformat(raw_value.replace(".", "-"))
    except ValueError as error:
        raise KopisResponseError(
            f"KOPIS field '{field}' contains an invalid date: {raw_value}"
        ) from error


def _required_text(record: ElementTree.Element, field: str) -> str:
    value = _optional_text(record, field)
    if value is None:
        raise KopisResponseError(f"KOPIS response is missing required field '{field}'")
    return value


def _optional_text(record: ElementTree.Element, field: str) -> str | None:
    node = record.find(field)
    return _node_text(node) if node is not None else None


def _optional_int(record: ElementTree.Element, field: str) -> int | None:
    value = _optional_text(record, field)
    if value is None:
        return None
    normalized = value.replace(",", "")
    return int(normalized) if normalized.isdigit() else None


def _optional_float(record: ElementTree.Element, field: str) -> float | None:
    value = _optional_text(record, field)
    if value is None:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _optional_yn(record: ElementTree.Element, field: str) -> bool | None:
    value = _optional_text(record, field)
    if value == "Y":
        return True
    if value == "N":
        return False
    return None


def _node_text(node: ElementTree.Element) -> str | None:
    value = (node.text or "").strip()
    return value or None


def _element_to_mapping(element: ElementTree.Element) -> dict[str, object]:
    value = _element_value(element)
    if not isinstance(value, dict):
        raise KopisResponseError("KOPIS record could not be converted to a mapping")
    return value


def _element_value(element: ElementTree.Element) -> object:
    children = list(element)
    if not children:
        return _node_text(element) or ""

    result: dict[str, object] = {}
    for child in children:
        value = _element_value(child)
        existing = result.get(child.tag)
        if existing is None:
            result[child.tag] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            result[child.tag] = [existing, value]
    return result
