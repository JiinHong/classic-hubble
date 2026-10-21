"""Resumable, private text extraction from archived images and PDFs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import sys
import time
from datetime import UTC, datetime

from .cloud_run import _terminated
from .ocr import PIPELINE_VERSION, OcrInputError, PaddleEngine, extract_image
from .pdf import PDF_PIPELINE_VERSION, extract_pdf
from .r2 import R2Settings, R2Store
from .supabase import SupabaseRepository, SupabaseSettings

CACHEABLE = {"text_extracted", "no_text", "needs_manual_handling"}


def _is_pdf(source):
    return source["content_type"].split(";", 1)[0].strip().lower() == "application/pdf"


def _version(source):
    return PDF_PIPELINE_VERSION if _is_pdf(source) else PIPELINE_VERSION


def process_archives(
    repository, store, read, *, max_seconds: int, clock=time.monotonic
) -> dict[str, object]:
    if not 0 < max_seconds <= 3300:
        raise ValueError("OCR_MAX_SECONDS must be between 1 and 3300")
    started = clock()
    run_id = repository.start_ingestion_run("paddleocr")
    counters = {
        "sources": 0,
        "cached": 0,
        "processed": 0,
        "manual": 0,
        "errors": 0,
        "remaining": 0,
        "lines": 0,
    }
    try:
        sources = {}
        for row in repository.load_source_archives():
            if row.get("bucket") != store.bucket:
                continue
            sha = row["sha256"]
            if (
                not re.fullmatch(r"[a-f0-9]{64}", sha)
                or row["object_key"] != f"originals/sha256/{sha[:2]}/{sha}"
            ):
                raise ValueError("Invalid archived source identity")
            sources[sha] = row
        cached = {
            row["source_sha256"]
            for row in repository.load_ocr_results()
            if row.get("source_sha256") in sources
            and row.get("pipeline_version") == _version(sources[row["source_sha256"]])
            and row.get("bucket") == store.bucket
            and row.get("status") in CACHEABLE
        }
        pending = sorted(set(sources) - cached)
        counters.update(
            sources=len(sources),
            cached=len(set(sources) & cached),
            remaining=len(pending),
        )
        consecutive_errors = 0
        for sha in pending:
            if clock() - started >= max_seconds:
                break
            source = sources[sha]
            version = _version(source)
            base = {
                "source_sha256": sha,
                "source_object_key": source["object_key"],
                "pipeline_version": version,
                "bucket": store.bucket,
                "review_status": "unverified",
            }
            item_started = clock()
            if not source["content_type"].startswith("image/") and not _is_pdf(source):
                result = {
                    **base,
                    "status": "needs_manual_handling",
                    "reason": "unsupported_media_type",
                    "lines": [],
                }
            else:
                data = store.read(source["object_key"])
                if hashlib.sha256(data).hexdigest() != sha:
                    raise ValueError("Source hash mismatch")
                try:
                    extract = extract_pdf if _is_pdf(source) else extract_image
                    result = {**extract(data, read), **base}
                except OcrInputError as error:
                    result = {
                        **base,
                        "status": "needs_manual_handling",
                        "reason": str(error),
                        "lines": [],
                    }
                except TimeoutError:
                    raise
                except Exception as error:  # noqa: BLE001 - isolate native OCR failures.
                    counters["errors"] += 1
                    consecutive_errors += 1
                    repository.upsert_provider_record(
                        provider="paddleocr",
                        entity_type="ocr_error",
                        provider_id=f"{version}:{sha}:{run_id}",
                        ingestion_run_id=run_id,
                        payload={**base, "error": type(error).__name__},
                    )
                    if consecutive_errors >= 5:
                        break
                    continue
            # Persist the large evidence file before the small completion record.
            saved = store.archive_ocr_result(result)
            metadata = {key: value for key, value in result.items() if key != "lines"}
            metadata.update(
                result_object_key=saved.key,
                result_sha256=saved.sha256,
                line_count=len(result["lines"]),
                duration_ms=round((clock() - item_started) * 1000),
                processed_at=datetime.now(UTC).isoformat(),
            )
            repository.upsert_provider_record(
                provider="paddleocr",
                entity_type="ocr_result",
                provider_id=f"{version}:{sha}",
                ingestion_run_id=run_id,
                payload=metadata,
            )
            consecutive_errors = 0
            counters["processed"] += 1
            counters["remaining"] -= 1
            counters["manual"] += int(result["status"] == "needs_manual_handling")
            counters["lines"] += len(result["lines"])
            print(
                json.dumps(
                    {
                        "event": "ocr_progress",
                        **counters,
                        "last_duration_ms": metadata["duration_ms"],
                    }
                ),
                flush=True,
            )
    except Exception as error:
        repository.finish_ingestion_run(
            run_id, status="failed", counters=counters, error=type(error).__name__
        )
        raise
    status = (
        "failed"
        if counters["errors"]
        else ("partial" if counters["remaining"] else "completed")
    )
    repository.finish_ingestion_run(run_id, status=status, counters=counters)
    return {
        "run_id": run_id,
        "status": status,
        "complete": counters["remaining"] == 0,
        "counters": counters,
    }


def main() -> int:
    signal.signal(signal.SIGTERM, _terminated)
    try:
        max_seconds = int(os.environ.get("OCR_MAX_SECONDS", "1500"))
        engine = PaddleEngine(os.environ.get("OCR_MODEL_DIR", "/models"))
        with (
            R2Store(R2Settings.from_env()) as store,
            SupabaseRepository(SupabaseSettings.from_env()) as repository,
        ):
            result = process_archives(
                repository, store, engine.read, max_seconds=max_seconds
            )
        print(json.dumps(result), flush=True)
        return 1 if result["status"] == "failed" else 0
    except Exception as error:  # noqa: BLE001 - redact provider errors at the boundary.
        print(f"OCR worker failed: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
