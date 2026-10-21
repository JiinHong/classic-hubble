"""Archive every KOPIS introduction image in the configured catalog window."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
from datetime import UTC, date, datetime
from urllib.parse import urlsplit, urlunsplit

import httpx

from .cloud_run import _shift_months, _terminated
from .kopis_sync import KOREA_TIMEZONE
from .r2 import MAX_SOURCE_BYTES, R2Settings, R2Store
from .supabase import SupabaseRepository, SupabaseSettings


class SourceDownloadError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def download_source(
    client: httpx.Client, url: str, *, max_bytes: int = MAX_SOURCE_BYTES
) -> tuple[bytes, str]:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.netloc not in {"www.kopis.or.kr", "kopis.or.kr"}
        or not parsed.path.startswith("/upload/")
        or parsed.fragment
    ):
        raise SourceDownloadError(
            "Source URL is outside the supported KOPIS upload hosts"
        )
    # KOPIS supplies http://www URLs but serves uploads on its HTTPS apex host.
    secure_url = urlunsplit(("https", "kopis.or.kr", parsed.path, parsed.query, ""))
    try:
        with client.stream("GET", secure_url, follow_redirects=False) as response:
            if response.status_code != 200:
                raise SourceDownloadError(
                    f"Source HTTP {response.status_code}", status=response.status_code
                )
            chunks = []
            size = 0
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise SourceDownloadError("Source size exceeds the per-file limit")
                chunks.append(chunk)
    except httpx.TransportError as error:
        raise SourceDownloadError(
            f"Source transport failure: {type(error).__name__}"
        ) from None
    data = b"".join(chunks)
    signatures = [
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"GIF87a", "image/gif"),
        (b"GIF89a", "image/gif"),
        (b"%PDF-", "application/pdf"),
    ]
    for signature, kind in signatures:
        if data.startswith(signature):
            return data, kind
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return data, "image/webp"
    raise SourceDownloadError(
        "Unsupported source signature; HTML and unknown files are not archived"
    )


def archive_sources(
    repository: SupabaseRepository, store: R2Store, client: httpx.Client, *, as_of: date
) -> dict[str, object]:
    run_id = repository.start_ingestion_run("r2")
    counters = {
        "sources": 0,
        "archived": 0,
        "reused": 0,
        "changed": 0,
        "skipped": 0,
        "source_errors": 0,
        "uploaded_bytes": 0,
    }
    failure = None
    try:
        performances = repository.load_source_performances(
            start=_shift_months(as_of, -3), end=_shift_months(as_of, 6)
        )
        sources: dict[str, set[str]] = {}
        for performance in performances:
            for url in performance["intro_image_urls"]:
                sources.setdefault(url, set()).add(performance["id"])
        previous = {row["source_url"]: row for row in repository.load_source_archives()}
        counters["sources"] = len(sources)
        consecutive_errors = 0
        for index, (url, performance_ids) in enumerate(sorted(sources.items())):
            prior = previous.get(url, {})
            ids = sorted(performance_ids)
            if (
                prior.get("checked_on") == as_of.isoformat()
                and prior.get("bucket") == store.bucket
                and prior.get("performance_ids") == ids
            ):
                counters["skipped"] += 1
                continue
            source_id = hashlib.sha256(url.encode()).hexdigest()
            try:
                data, content_type = download_source(client, url)
            except SourceDownloadError as error:
                counters["source_errors"] += 1
                consecutive_errors += 1
                failure = str(error)
                repository.upsert_provider_record(
                    provider="r2",
                    entity_type="source_error",
                    provider_id=f"{source_id}:{as_of.isoformat()}",
                    ingestion_run_id=run_id,
                    payload={
                        "source_url": url,
                        "performance_ids": ids,
                        "checked_on": as_of.isoformat(),
                        "error": str(error),
                    },
                )
                if error.status in {401, 403, 429} or consecutive_errors >= 5:
                    break
                continue
            consecutive_errors = 0
            stored = store.archive(data, content_type)
            payload = {
                "source_url": url,
                "performance_ids": ids,
                "bucket": store.bucket,
                "object_key": stored.key,
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "content_type": stored.content_type,
                "checked_on": as_of.isoformat(),
                "checked_at": datetime.now(UTC).isoformat(),
            }
            # Publish the resumable pointer only after both the object and its
            # version evidence are durable. No OCR/review state is overwritten.
            repository.upsert_provider_record(
                provider="r2",
                entity_type="source_version",
                provider_id=f"{source_id}:{stored.sha256}",
                ingestion_run_id=run_id,
                payload=payload,
            )
            repository.upsert_provider_record(
                provider="r2",
                entity_type="source_archive",
                provider_id=source_id,
                ingestion_run_id=run_id,
                payload=payload,
            )
            counters["archived"] += 1
            counters["reused"] += int(not stored.created)
            counters["uploaded_bytes"] += stored.size_bytes if stored.created else 0
            counters["changed"] += int(
                bool(prior.get("sha256")) and prior["sha256"] != stored.sha256
            )
            if (index + 1) % 25 == 0:
                print(
                    json.dumps({"event": "source_archive_progress", **counters}),
                    flush=True,
                )
    except Exception as error:
        repository.finish_ingestion_run(
            run_id, status="failed", counters=counters, error=type(error).__name__
        )
        raise
    status = "failed" if counters["source_errors"] else "completed"
    repository.finish_ingestion_run(
        run_id, status=status, counters=counters, error=failure
    )
    return {"status": status, "run_id": run_id, "counters": counters}


def main() -> int:
    signal.signal(signal.SIGTERM, _terminated)
    try:
        as_of = (
            date.fromisoformat(os.environ["COLLECTION_DATE"])
            if os.environ.get("COLLECTION_DATE")
            else datetime.now(KOREA_TIMEZONE).date()
        )
        with (
            R2Store(R2Settings.from_env()) as store,
            SupabaseRepository(SupabaseSettings.from_env()) as repository,
            httpx.Client(
                timeout=30,
                follow_redirects=False,
                headers={"User-Agent": "classic-hubble-pipeline/0.1"},
            ) as client,
        ):
            result = archive_sources(repository, store, client, as_of=as_of)
        print(json.dumps(result), flush=True)
        return 0 if result["status"] == "completed" else 1
    except Exception as error:  # noqa: BLE001 - CLI boundary must redact provider exceptions.
        print(f"Source archive failed: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
