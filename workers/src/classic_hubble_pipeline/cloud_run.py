"""Full-window KOPIS collection with durable, per-sweep progress."""

from __future__ import annotations

import calendar
import json
import os
import signal
import sys
from datetime import date, datetime

from .kopis import KopisClient, KopisSettings
from .kopis_sync import KOREA_TIMEZONE, KopisSyncService
from .supabase import SupabaseRepository, SupabaseSettings


def _shift_months(value: date, offset: int) -> date:
    year, month = divmod(value.year * 12 + value.month - 1 + offset, 12)
    month += 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def collect(
    service: KopisSyncService,
    repository: SupabaseRepository,
    *,
    as_of: date,
) -> dict[str, object]:
    start, end = _shift_months(as_of, -3), _shift_months(as_of, 6)
    key = f"catalog-v1:{as_of.isoformat()}"
    checkpoint = repository.load_collection_checkpoint(key) or {}
    if checkpoint.get("complete"):
        return {"status": "already_completed", "checkpoint": key}
    completed = set(checkpoint.get("completed_ids", []))
    complete = False
    last_count = len(completed)

    def save() -> None:
        repository.save_collection_checkpoint(key, {
            "start": start.isoformat(), "end": end.isoformat(),
            "completed_ids": sorted(completed), "complete": complete,
        })

    def persisted(performance_id: str) -> None:
        nonlocal last_count
        completed.add(performance_id)
        if len(completed) - last_count >= 25:
            save()
            last_count = len(completed)
            print(json.dumps({"event": "collection_progress", "saved": last_count}), flush=True)

    try:
        result = service.run(
            start_date=start, end_date=end, rows=100,
            completed_ids=frozenset(completed), on_performance_complete=persisted,
            continue_on_source_error=True,
        )
        complete = result.status == "completed"
        return {
            "status": result.status, "run_id": result.run_id,
            "checkpoint": key, "total_saved": len(completed),
            "counters": result.counters,
        }
    finally:
        # Failed or terminated sweeps retain completed writes; upserts safely
        # replay at most the unflushed batch after an uncatchable hard kill.
        save()


def _terminated(signum: int, frame: object) -> None:
    raise TimeoutError("Collection interrupted; resume with the same COLLECTION_DATE")


def main() -> int:
    signal.signal(signal.SIGTERM, _terminated)
    try:
        as_of = (
            date.fromisoformat(os.environ["COLLECTION_DATE"])
            if os.environ.get("COLLECTION_DATE")
            else datetime.now(KOREA_TIMEZONE).date()
        )
        with KopisClient(KopisSettings.from_env()) as client:
            with SupabaseRepository(SupabaseSettings.from_env()) as repository:
                result = collect(KopisSyncService(client, repository), repository, as_of=as_of)
        print(json.dumps(result), flush=True)
        return 0 if result["status"] in {"completed", "already_completed"} else 1
    except Exception as error:
        print(f"Collection failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
