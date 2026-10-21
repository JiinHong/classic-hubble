from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .work_matching import CanonicalWork


class SupabaseError(RuntimeError):
    """Base exception for Supabase worker failures."""


class SupabaseConfigurationError(SupabaseError):
    """Raised when worker-side Supabase credentials are missing or unsafe."""


class SupabaseResponseError(SupabaseError):
    """Raised when the Supabase Data API returns an invalid response."""


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    api_key: str
    timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        url = self.url.strip().rstrip("/")
        api_key = self.api_key.strip()
        parsed = urlparse(url)
        is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        is_hosted = (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and parsed.hostname.endswith(".supabase.co")
        )

        if not url:
            raise SupabaseConfigurationError("SUPABASE_URL is required")
        if not (is_hosted or (is_local and parsed.scheme in {"http", "https"})):
            raise SupabaseConfigurationError(
                "SUPABASE_URL must be a hosted Supabase HTTPS URL or a local URL"
            )
        if not api_key:
            raise SupabaseConfigurationError(
                "SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is required"
            )
        if api_key.startswith("sb_publishable_"):
            raise SupabaseConfigurationError(
                "The worker requires a Supabase secret key, not a publishable key"
            )
        if self.timeout_seconds <= 0:
            raise SupabaseConfigurationError(
                "SUPABASE_TIMEOUT_SECONDS must be positive"
            )

        object.__setattr__(self, "url", url)
        object.__setattr__(self, "api_key", api_key)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> SupabaseSettings:
        values = os.environ if environ is None else environ
        url = (
            values.get("SUPABASE_URL", "").strip()
            or values.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
        )
        api_key = (
            values.get("SUPABASE_SECRET_KEY", "").strip()
            or values.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        )
        try:
            timeout_seconds = float(values.get("SUPABASE_TIMEOUT_SECONDS", "15"))
        except ValueError as error:
            raise SupabaseConfigurationError(
                "SUPABASE_TIMEOUT_SECONDS must be numeric"
            ) from error
        return cls(url=url, api_key=api_key, timeout_seconds=timeout_seconds)


class SupabaseRepository:
    def __init__(
        self,
        settings: SupabaseSettings,
        *,
        http_client: httpx.Client | None = None,
    ):
        self._settings = settings
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )

    def __enter__(self) -> SupabaseRepository:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def start_ingestion_run(self, provider: str) -> str:
        normalized_provider = provider.strip()
        if not normalized_provider:
            raise ValueError("Ingestion provider cannot be empty")
        return self._insert_one(
            "ingestion_runs",
            {"provider": normalized_provider, "status": "running"},
        )

    def finish_ingestion_run(
        self,
        run_id: str,
        *,
        status: str,
        counters: Mapping[str, int],
        error: str | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "finished_at": _utc_now(),
            "status": status,
            "counters": dict(counters),
            "error": error,
        }
        self._request(
            "PATCH",
            "ingestion_runs",
            params={"id": f"eq.{run_id}"},
            json=payload,
            prefer="return=minimal",
        )

    def upsert_provider_record(
        self,
        *,
        entity_type: str,
        provider_id: str,
        payload: Mapping[str, object],
        ingestion_run_id: str,
        provider: str = "kopis",
    ) -> str:
        normalized_provider = _require_provider(provider)
        return self._upsert_one(
            "provider_records",
            {
                "provider": normalized_provider,
                "entity_type": entity_type,
                "provider_id": provider_id,
                "ingestion_run_id": ingestion_run_id,
                "payload": dict(payload),
                "fetched_at": _utc_now(),
            },
            on_conflict="provider,entity_type,provider_id",
        )

    def upsert_venue(self, payload: Mapping[str, object]) -> str:
        values = dict(payload)
        values["updated_at"] = _utc_now()
        return self._upsert_one(
            "venues",
            values,
            on_conflict="kopis_facility_id",
        )

    def upsert_hall(self, payload: Mapping[str, object]) -> str:
        values = dict(payload)
        values["updated_at"] = _utc_now()
        return self._upsert_one(
            "venue_halls",
            values,
            on_conflict="kopis_hall_id",
        )

    def upsert_performance(self, payload: Mapping[str, object]) -> str:
        values = dict(payload)
        values["updated_at"] = _utc_now()
        return self._upsert_one(
            "performances",
            values,
            on_conflict="kopis_performance_id",
        )

    def upsert_poster_review_item(self, payload: Mapping[str, object]) -> str:
        return self._upsert_one(
            "poster_review_items",
            payload,
            on_conflict="performance_id,image_url",
        )

    def update_performance_program_source(
        self,
        performance_id: str,
        payload: Mapping[str, object],
    ) -> None:
        values = dict(payload)
        values["program_source_updated_at"] = _utc_now()
        self._request(
            "PATCH",
            "performances",
            params={"id": f"eq.{performance_id}"},
            json=values,
            prefer="return=minimal",
        )

    def replace_program_items(
        self,
        performance_id: str,
        source_provider: str,
        items: Sequence[Mapping[str, object]],
    ) -> None:
        normalized_provider = _require_provider(source_provider)
        positions: list[int] = []
        if items:
            rows: list[dict[str, object]] = []
            for item in items:
                row = dict(item)
                position = row.get("position")
                if (
                    not isinstance(position, int)
                    or isinstance(position, bool)
                    or position < 0
                ):
                    raise ValueError(
                        "Program item position must be a non-negative integer"
                    )
                if position in positions:
                    raise ValueError("Program item positions must be unique")
                positions.append(position)
                row["performance_id"] = performance_id
                row["source_provider"] = normalized_provider
                rows.append(row)

            self._request(
                "POST",
                "program_items",
                params={"on_conflict": "performance_id,source_provider,position"},
                json=rows,
                prefer="resolution=merge-duplicates,return=minimal",
            )

        params = {
            "performance_id": f"eq.{performance_id}",
            "source_provider": f"eq.{normalized_provider}",
        }
        if positions:
            params["position"] = (
                "not.in.(" + ",".join(str(item) for item in positions) + ")"
            )
        self._request(
            "DELETE",
            "program_items",
            params=params,
            prefer="return=minimal",
        )

    def load_work_catalog(self, *, page_size: int = 500) -> list[CanonicalWork]:
        rows = self._read_pages(
            "works",
            {
                "select": "id,slug,title,title_ko,catalogue,composers(name,name_ko),work_aliases(alias)",
            },
            page_size=page_size,
        )
        return [
            CanonicalWork(
                id=row["id"],
                slug=row["slug"],
                titles=tuple(
                    value for value in (row["title"], row.get("title_ko")) if value
                ),
                composers=tuple(
                    value
                    for value in (
                        row["composers"]["name"],
                        row["composers"].get("name_ko"),
                    )
                    if value
                ),
                catalogue=row.get("catalogue"),
                aliases=tuple(alias["alias"] for alias in row.get("work_aliases", [])),
            )
            for row in rows
        ]

    def load_unlinked_program_items(
        self, *, page_size: int = 500
    ) -> list[dict[str, Any]]:
        return self._read_pages(
            "program_items",
            {
                "select": "id,display_title,composer_name,source_url",
                "source_provider": "eq.nol",
                "work_id": "is.null",
            },
            page_size=page_size,
        )

    def link_program_item(self, item: Mapping[str, Any], work_id: str) -> bool:
        response = self._request(
            "PATCH",
            "program_items",
            params={
                "id": f"eq.{item['id']}",
                "work_id": "is.null",
                "source_provider": "eq.nol",
                "display_title": f"eq.{item['display_title']}",
                "composer_name": f"eq.{item['composer_name']}"
                if item["composer_name"]
                else "is.null",
                "select": "id",
            },
            json={"work_id": work_id},
            prefer="return=representation",
        )
        return bool(response.json())

    def _read_pages(
        self, table: str, params: Mapping[str, str], *, page_size: int
    ) -> list[dict[str, Any]]:
        if not 1 <= page_size <= 1000:
            raise ValueError("Page size must be between 1 and 1000")
        rows: list[dict[str, Any]] = []
        while True:
            response = self._request(
                "GET",
                table,
                params={
                    **params,
                    "order": "id.asc",
                    "offset": str(len(rows)),
                    "limit": str(page_size),
                },
                prefer="count=exact",
            )
            page = response.json()
            if not isinstance(page, list):
                raise SupabaseResponseError(f"Supabase returned invalid {table} rows")
            rows.extend(page)
            if len(page) < page_size:
                return rows

    def _insert_one(self, table: str, payload: Mapping[str, object]) -> str:
        response = self._request(
            "POST",
            table,
            json=dict(payload),
            prefer="return=representation",
        )
        return _response_id(response)

    def _upsert_one(
        self,
        table: str,
        payload: Mapping[str, object],
        *,
        on_conflict: str,
    ) -> str:
        response = self._request(
            "POST",
            table,
            params={"on_conflict": on_conflict},
            json=dict(payload),
            prefer="resolution=merge-duplicates,return=representation",
        )
        return _response_id(response)

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: Mapping[str, str] | None = None,
        json: Mapping[str, object] | Sequence[Mapping[str, object]] | None = None,
        prefer: str,
    ) -> httpx.Response:
        headers = {
            "apikey": self._settings.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": prefer,
            "User-Agent": "classic-hubble-pipeline/0.1",
        }
        if not self._settings.api_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        try:
            response = self._http_client.request(
                method,
                f"{self._settings.url}/rest/v1/{table}",
                params=params,
                json=json,
                headers=headers,
                follow_redirects=False,
            )
        except httpx.TransportError as error:
            raise SupabaseResponseError(
                f"Supabase request failed: {type(error).__name__}"
            ) from error

        if response.is_error:
            message = _response_error_message(response)
            raise SupabaseResponseError(
                f"Supabase {table} request returned HTTP "
                f"{response.status_code}: {message}"
            )
        return response


def _response_id(response: httpx.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError as error:
        raise SupabaseResponseError(
            "Supabase response did not contain valid JSON"
        ) from error
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise SupabaseResponseError("Supabase response did not contain a row")
    row_id = payload[0].get("id")
    if not isinstance(row_id, str) or not row_id:
        raise SupabaseResponseError("Supabase response row did not contain an ID")
    return row_id


def _response_error_message(response: httpx.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        return "invalid error response"
    if not isinstance(payload, dict):
        return "unexpected error response"
    parts = [payload.get("message"), payload.get("hint"), payload.get("code")]
    return " | ".join(str(part) for part in parts if part)[:1000] or "unknown error"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_provider(provider: str) -> str:
    normalized_provider = provider.strip()
    if not normalized_provider:
        raise ValueError("Provider cannot be empty")
    return normalized_provider
