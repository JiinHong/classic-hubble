from __future__ import annotations

import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx


DEFAULT_BASE_URL = "https://api-ticketfront.interpark.com"
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
OFFICIAL_SOURCE_HOSTS = frozenset({"ticket.interpark.com", "tickets.interpark.com"})
PROGRAM_HEADINGS = frozenset({"PROGRAM", "PROGRAMME", "프로그램", "공연 프로그램"})
COMPOSER_LIFESPAN_PATTERN = re.compile(
    r"^(?P<composer>.+?)\s*\((?P<lifespan>\d{4}\s*[-\u2013]\s*\d{4})\)\s*$"
)


class NolError(RuntimeError):
    """Base exception for NOL ingestion failures."""


class NolConfigurationError(NolError):
    """Raised when NOL client configuration is invalid."""


class NolResponseError(NolError):
    """Raised when NOL returns malformed or incomplete JSON."""


class NolTransportError(NolError):
    """Raised when NOL cannot be reached after retrying."""


@dataclass(frozen=True)
class NolSettings:
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 10.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.25

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        if not base_url:
            raise NolConfigurationError("NOL_BASE_URL cannot be empty")

        parsed = urlparse(base_url)
        try:
            port = parsed.port
        except ValueError as error:
            raise NolConfigurationError("NOL_BASE_URL contains an invalid port") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api-ticketfront.interpark.com"
            or port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise NolConfigurationError(
                "NOL_BASE_URL must use the official NOL HTTPS API host"
            )
        if self.timeout_seconds <= 0:
            raise NolConfigurationError("NOL_TIMEOUT_SECONDS must be positive")
        if self.max_retries < 0:
            raise NolConfigurationError("NOL_MAX_RETRIES cannot be negative")
        if self.retry_backoff_seconds < 0:
            raise NolConfigurationError("NOL_RETRY_BACKOFF_SECONDS cannot be negative")

        object.__setattr__(self, "base_url", base_url)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> NolSettings:
        values = os.environ if environ is None else environ
        try:
            return cls(
                base_url=values.get("NOL_BASE_URL", DEFAULT_BASE_URL),
                timeout_seconds=float(values.get("NOL_TIMEOUT_SECONDS", "10")),
                max_retries=int(values.get("NOL_MAX_RETRIES", "3")),
                retry_backoff_seconds=float(
                    values.get("NOL_RETRY_BACKOFF_SECONDS", "0.25")
                ),
            )
        except ValueError as error:
            raise NolConfigurationError(
                "NOL timeout and retry settings must be numeric"
            ) from error


@dataclass(frozen=True)
class NolProgramItem:
    position: int
    display_title: str
    composer: str | None
    composer_lifespan: str | None
    work_title: str


@dataclass(frozen=True)
class NolPerformanceData:
    goods_code: str
    title: str
    venue_name: str
    program_status: str
    program_source_url: str
    program_image_urls: tuple[str, ...]
    program_items: tuple[NolProgramItem, ...]
    raw_summary: Mapping[str, object]
    raw_play_db: Mapping[str, object] | None


def extract_nol_goods_code(url: str) -> str | None:
    parsed = urlparse(url.strip())
    try:
        port = parsed.port
    except ValueError:
        return None
    if parsed.hostname not in OFFICIAL_SOURCE_HOSTS:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if port not in {None, 80, 443}:
        return None

    if parsed.hostname == "ticket.interpark.com":
        normalized_path = parsed.path.rstrip("/").lower()
        if normalized_path not in {
            "/goods/goodsinfo.asp",
            "/ticket/goods/goodsinfo.asp",
        }:
            return None
        query = parse_qs(parsed.query)
        goods_codes = next(
            (value for key, value in query.items() if key.lower() == "goodscode"),
            [],
        )
        if len(goods_codes) != 1 or not re.fullmatch(r"\d{8}", goods_codes[0]):
            return None
        return goods_codes[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    for index, part in enumerate(path_parts[:-1]):
        if part.lower() == "goods" and re.fullmatch(r"\d{8}", path_parts[index + 1]):
            return path_parts[index + 1]
    return None


def parse_nol_payload(
    goods_code: str,
    summary: Mapping[str, object],
    play_db: Mapping[str, object] | None,
) -> NolPerformanceData:
    summary_data = _extract_envelope_data(summary, label="summary")
    summary_goods_code = _required_string(summary_data, "goodsCode", label="summary")
    if summary_goods_code != goods_code:
        raise NolResponseError("NOL summary goodsCode did not match the requested goods code")

    title = _required_string(summary_data, "goodsName", label="summary")
    venue_name = _required_string_from_aliases(
        summary_data, ("placeName", "playPlaceName"), label="summary"
    )
    program_source_url = f"https://tickets.interpark.com/goods/{goods_code}"
    content_html = _optional_string(summary_data, "contentHtml") or ""
    html_program_blocks, html_image_urls = _extract_program_data_from_html(content_html)
    program_image_urls = html_image_urls or _extract_detail_image_urls(summary_data)

    play_db_data = _extract_optional_play_db_data(play_db)
    play_db_program = _optional_string(play_db_data, "programInfo") if play_db_data else None

    text = (play_db_program or "").strip()
    if text:
        play_db_program_blocks = _extract_program_text_blocks(text)
        program_items = _build_program_items(
            [_normalize_block_text(block) for block in play_db_program_blocks],
            allow_single_line=True,
        )
        text = "\n\n".join(block for block in play_db_program_blocks if block).strip()
    else:
        program_items = _parse_program_blocks(html_program_blocks)
        text = "\n\n".join(block for block in html_program_blocks if block).strip()

    if program_items:
        status = "confirmed"
    else:
        status = _classify_program_status(text, program_image_urls)

    return NolPerformanceData(
        goods_code=goods_code,
        title=title,
        venue_name=venue_name,
        program_status=status,
        program_source_url=program_source_url,
        program_image_urls=program_image_urls,
        program_items=program_items,
        raw_summary=summary,
        raw_play_db=play_db,
    )


class NolClient:
    def __init__(
        self,
        settings: NolSettings | None = None,
        *,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings or NolSettings()
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            timeout=self._settings.timeout_seconds,
            follow_redirects=False,
        )
        self._sleep = sleep

    def __enter__(self) -> NolClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def fetch(self, url: str) -> NolPerformanceData:
        goods_code = extract_nol_goods_code(url)
        if goods_code is None:
            raise ValueError("NOL goods URL must use an official Interpark/NOL host and goods code")

        request_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://tickets.interpark.com",
            "Referer": f"https://tickets.interpark.com/goods/{goods_code}",
        }

        summary = self._get_json(
            f"/v1/goods/{goods_code}/summary",
            headers=request_headers,
        )
        if summary is None:
            raise NolResponseError("NOL summary response was unexpectedly missing")
        play_db = self._get_json(
            "/v1/goods/play-db",
            params={"goodsCode": goods_code},
            headers=request_headers,
            allow_not_found=True,
        )
        return parse_nol_payload(goods_code, summary, play_db)

    def _get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        allow_not_found: bool = False,
    ) -> Mapping[str, object] | None:
        url = f"{self._settings.base_url}{path}"
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = self._http_client.get(
                    url,
                    params=params,
                    headers=headers,
                    follow_redirects=False,
                )
            except httpx.TransportError:
                if attempt == self._settings.max_retries:
                    raise NolTransportError("NOL request failed after retrying") from None
            else:
                if allow_not_found and response.status_code == 404:
                    return None
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError:
                        raise NolTransportError(
                            f"NOL returned HTTP {response.status_code}"
                        ) from None
                    try:
                        payload = response.json()
                    except ValueError as error:
                        raise NolResponseError("NOL returned malformed JSON") from error
                    if not isinstance(payload, Mapping):
                        raise NolResponseError("NOL returned a non-object JSON payload")
                    return payload

                if attempt == self._settings.max_retries:
                    raise NolTransportError(
                        f"NOL remained unavailable with HTTP {response.status_code}"
                    )

            if attempt < self._settings.max_retries:
                self._sleep(self._settings.retry_backoff_seconds * (2**attempt))

        raise NolTransportError("NOL request failed after retrying")


def _extract_envelope_data(
    payload: Mapping[str, object], *, label: str
) -> Mapping[str, object]:
    _validate_common_envelope(payload, label=label)
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise NolResponseError(f"NOL {label} response did not contain an object data envelope")
    return data


def _extract_optional_play_db_data(
    payload: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    if payload is None:
        return None
    if "data" in payload:
        _validate_common_envelope(payload, label="play DB")
        data = payload.get("data")
        if data is None:
            return None
        if not isinstance(data, Mapping):
            raise NolResponseError(
                "NOL play DB response did not contain an object data envelope"
            )
        return data
    return payload


def _extract_program_data_from_html(
    content_html: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not content_html.strip():
        return (), ()

    parser = _ProgramHtmlParser()
    parser.feed(content_html)
    parser.close()
    return parser.program_blocks(), parser.image_urls()


def _extract_program_text_blocks(content_html: str) -> tuple[str, ...]:
    if not content_html.strip():
        return ()

    parser = _ProgramTextParser()
    parser.feed(content_html)
    parser.close()
    return parser.blocks()


def _parse_program_blocks(blocks: tuple[str, ...]) -> tuple[NolProgramItem, ...]:
    if not blocks:
        return ()

    normalized_blocks: list[str] = []
    current_lines: list[str] = []
    for block in blocks:
        normalized = _normalize_block_text(block)
        if not normalized:
            if current_lines:
                normalized_blocks.append("\n".join(current_lines))
                current_lines = []
            continue
        current_lines.append(normalized)

    if current_lines:
        normalized_blocks.append("\n".join(current_lines))

    return _build_program_items(normalized_blocks, allow_single_line=False)


def _build_program_items(
    blocks: list[str],
    *,
    allow_single_line: bool,
) -> tuple[NolProgramItem, ...]:
    items: list[NolProgramItem] = []
    for block in blocks:
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or not _looks_like_program_block(
            lines,
            allow_single_line=allow_single_line,
        ):
            continue

        composer: str | None = None
        composer_lifespan: str | None = None
        work_title = "\n".join(lines)
        display_lines = list(lines)
        composer_match = COMPOSER_LIFESPAN_PATTERN.match(lines[0])
        if composer_match and len(lines) > 1:
            composer = composer_match.group("composer").strip()
            composer_lifespan = re.sub(r"\s+", "", composer_match.group("lifespan")).replace(
                "\u2013", "-"
            )
            display_lines[0] = f"{composer} ({composer_lifespan})"
            work_title = "\n".join(lines[1:])

        items.append(
            NolProgramItem(
                position=len(items),
                display_title="\n".join(display_lines),
                composer=composer,
                composer_lifespan=composer_lifespan,
                work_title=work_title,
            )
        )
    return tuple(items)


def _looks_like_program_block(
    lines: list[str],
    *,
    allow_single_line: bool,
) -> bool:
    if len(lines) > 1:
        return True
    if not allow_single_line:
        return False

    text = " ".join(lines[0].lower().split())
    if not text or COMPOSER_LIFESPAN_PATTERN.match(lines[0]) is not None:
        return False
    if text in {"intermission", "intermisson", "휴식", "중간 휴식"}:
        return False
    return not (
        _is_selected_on_day(text)
        or _is_announced_later(text)
        or _is_not_published(text)
    )


def _classify_program_status(text: str, image_urls: tuple[str, ...]) -> str:
    normalized_text = " ".join(text.lower().split())
    if _is_selected_on_day(normalized_text):
        return "selected_on_day"
    if _is_announced_later(normalized_text):
        return "announced_later"
    if normalized_text and _is_not_published(normalized_text):
        return "not_published"
    if image_urls:
        return "image_only"
    return "not_published"


def _is_selected_on_day(text: str) -> bool:
    if "당일" in text and any(token in text for token in ("공개", "선택", "발표")):
        return True
    return any(
        phrase in text
        for phrase in (
            "selected on the day",
            "announced on the day",
            "disclosed at the performance",
        )
    )


def _is_announced_later(text: str) -> bool:
    if "추후" in text and any(token in text for token in ("공개", "공지", "안내")):
        return True
    return any(
        phrase in text
        for phrase in ("to be announced", "announced later", "will be announced later")
    )


def _is_not_published(text: str) -> bool:
    return any(
        phrase in text
        for phrase in ("미기재", "없습니다", "not available", "not provided", "추후 업데이트")
    )


def _extract_detail_image_urls(summary_data: Mapping[str, object]) -> tuple[str, ...]:
    detail_images = summary_data.get("detailImageList")
    if not isinstance(detail_images, list):
        return ()

    urls: list[str] = []
    for item in detail_images:
        if not isinstance(item, Mapping):
            continue
        image_url = _optional_string(item, "imageUrl")
        if image_url:
            urls.append(image_url)
    return tuple(urls)


def _validate_common_envelope(payload: Mapping[str, object], *, label: str) -> None:
    common = payload.get("common")
    if common is None:
        return
    if not isinstance(common, Mapping):
        raise NolResponseError(f"NOL {label} response did not contain an object common envelope")
    message = _optional_string(common, "message")
    internal_http_status = common.get("internalHttpStatusCode")
    if message != "success" or internal_http_status != 200:
        raise NolResponseError(f"NOL {label} response common envelope was not successful")


def _required_string_from_aliases(
    payload: Mapping[str, object],
    keys: tuple[str, ...],
    *,
    label: str,
) -> str:
    for key in keys:
        value = _optional_string(payload, key)
        if value is not None:
            return value
    raise NolResponseError(
        f"NOL {label} response did not contain a valid {' or '.join(keys)}"
    )


def _required_string(payload: Mapping[str, object], key: str, *, label: str) -> str:
    value = _optional_string(payload, key)
    if value is None:
        raise NolResponseError(f"NOL {label} response did not contain a valid {key}")
    return value


def _optional_string(payload: Mapping[str, object] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_block_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r", "").split("\n")]
    kept_lines = [line for line in lines if line]
    return "\n".join(kept_lines)


class _ProgramHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._sections: list[tuple[str | None, tuple[str, ...]]] = []
        self._image_urls: list[str] = []
        self._current_heading: str | None = None
        self._current_blocks: list[str] = []
        self._current_parts: list[str] = []
        self._in_heading = False
        self._in_strong = False
        self._current_strong_parts: list[str] = []
        self._non_strong_text_seen = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._finish_block()
            self._finish_section()
            self._in_heading = True
            self._current_parts = []
            return
        if tag == "br":
            self._current_parts.append("\n")
            return
        if tag == "img":
            attributes = dict(attrs)
            src = attributes.get("src")
            normalized_url = _normalize_ticket_image_url(src)
            if normalized_url is not None:
                self._image_urls.append(normalized_url)
            return
        if tag == "strong":
            self._in_strong = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = _normalize_inline_text("".join(self._current_parts))
            self._current_heading = heading or None
            self._current_parts = []
            self._in_heading = False
            return
        if tag in {"p", "div", "li", "section", "article"}:
            self._finish_block()
            return
        if tag == "strong":
            self._in_strong = False

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._current_parts.append(data)
        if self._in_strong:
            self._current_strong_parts.append(data)
        elif data.strip():
            self._non_strong_text_seen = True

    def close(self) -> None:
        super().close()
        self._finish_block()
        self._finish_section()

    def program_blocks(self) -> tuple[str, ...]:
        for heading, blocks in self._sections:
            if heading in PROGRAM_HEADINGS:
                return blocks
        return ()

    def image_urls(self) -> tuple[str, ...]:
        deduped_urls: list[str] = []
        seen_urls: set[str] = set()
        for url in self._image_urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            deduped_urls.append(url)
        return tuple(deduped_urls)

    def _finish_block(self) -> None:
        if self._in_heading:
            return
        block = "".join(self._current_parts).replace("\xa0", " ")
        strong_text = _normalize_inline_text("".join(self._current_strong_parts).replace("\xa0", " "))
        self._current_parts = []
        self._current_strong_parts = []
        normalized = _normalize_inline_text(block)
        if (
            normalized
            and not self._non_strong_text_seen
            and strong_text == normalized
        ):
            self._finish_section()
            self._current_heading = strong_text
            self._non_strong_text_seen = False
            return
        self._current_blocks.append(normalized)
        self._non_strong_text_seen = False

    def _finish_section(self) -> None:
        if self._current_heading is None and not self._current_blocks:
            return
        self._sections.append((self._current_heading, tuple(self._current_blocks)))
        self._current_heading = None
        self._current_blocks = []


class _ProgramTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def blocks(self) -> tuple[str, ...]:
        text = "".join(self._parts).replace("\xa0", " ")
        if not text.strip():
            return ()
        return tuple(re.split(r"\n\s*\n+", text.strip()))


def _normalize_inline_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    if not any(lines):
        return ""
    return "\n".join(line for line in lines if line)


def _normalize_ticket_image_url(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    normalized = url.strip()
    if not normalized:
        return None
    if normalized.startswith("//ticketimage.interpark.com/"):
        return f"https:{normalized}"
    if normalized.startswith("http://ticketimage.interpark.com/"):
        return "https://" + normalized.removeprefix("http://")
    if normalized.startswith("https://ticketimage.interpark.com/"):
        return normalized
    return None
