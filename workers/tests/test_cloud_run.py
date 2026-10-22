from datetime import date
import importlib
import importlib.util

import pytest


def module():
    assert importlib.util.find_spec("classic_hubble_pipeline.cloud_run") is not None
    return importlib.import_module("classic_hubble_pipeline.cloud_run")


class Repository:
    def __init__(self):
        self.checkpoints = {}

    def load_collection_checkpoint(self, key):
        return self.checkpoints.get(key)

    def save_collection_checkpoint(self, key, payload):
        self.checkpoints[key] = dict(payload)


class Service:
    def __init__(self, *, fail=False):
        self.calls = []
        self.fail = fail

    def run(self, **kwargs):
        from classic_hubble_pipeline.kopis_sync import KopisSyncResult
        self.calls.append(kwargs)
        kwargs["on_performance_complete"]("PF1")
        if self.fail:
            raise RuntimeError("source unavailable")
        return KopisSyncResult("run-1", "completed", {"performances": 1})


def test_full_range_has_no_record_limit_and_uses_calendar_months():
    service, repo = Service(), Repository()
    module().collect(service, repo, as_of=date(2026, 10, 21))
    call = service.calls[0]
    assert call["start_date"] == date(2026, 7, 21)
    assert call["end_date"] == date(2027, 4, 21)
    assert call.get("limit") is None
    assert call["continue_on_source_error"] is True
    assert list(repo.checkpoints.values())[0]["complete"] is True


def test_month_window_handles_short_months():
    service, repo = Service(), Repository()
    module().collect(service, repo, as_of=date(2026, 8, 31))
    assert service.calls[0]["end_date"] == date(2027, 2, 28)


def test_failed_run_saves_progress_and_retry_skips_persisted_records():
    service, repo = Service(fail=True), Repository()
    with pytest.raises(RuntimeError, match="source unavailable"):
        module().collect(service, repo, as_of=date(2026, 10, 21))
    assert list(repo.checkpoints.values())[0]["complete"] is False
    service = Service()
    module().collect(service, repo, as_of=date(2026, 10, 21))
    assert service.calls[0]["completed_ids"] == frozenset({"PF1"})


def test_completed_run_is_not_repeated_but_next_day_refreshes():
    service, repo = Service(), Repository()
    module().collect(service, repo, as_of=date(2026, 10, 21))
    module().collect(service, repo, as_of=date(2026, 10, 21))
    assert len(service.calls) == 1
    module().collect(service, repo, as_of=date(2026, 10, 22))
    assert len(service.calls) == 2
    assert not service.calls[-1]["completed_ids"]


def test_progress_is_flushed_during_a_large_run():
    repo = Repository()

    class LargeService:
        def run(self, **kwargs):
            for i in range(25):
                kwargs["on_performance_complete"](f"PF{i}")
            assert len(list(repo.checkpoints.values())[0]["completed_ids"]) == 25
            raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError, match="interrupted"):
        module().collect(LargeService(), repo, as_of=date(2026, 10, 21))


def test_partial_failure_does_not_mark_the_checkpoint_complete():
    from classic_hubble_pipeline.kopis_sync import KopisSyncResult
    repo = Repository()

    class PartialService:
        def run(self, **kwargs):
            kwargs["on_performance_complete"]("PF1")
            return KopisSyncResult("run-1", "failed", {"source_errors": 1})

    result = module().collect(PartialService(), repo, as_of=date(2026, 10, 21))
    assert result["status"] == "failed"
    assert list(repo.checkpoints.values())[0]["complete"] is False
    assert list(repo.checkpoints.values())[0]["completed_ids"] == ["PF1"]


def test_explicit_historical_range_is_not_replaced_by_recent_window():
    service, repo = Service(), Repository()
    result = module().collect(
        service, repo, as_of=date(2026, 10, 22),
        start_date=date(2024, 1, 1), end_date=date(2026, 10, 22),
    )
    call = service.calls[0]
    assert call["start_date"] == date(2024, 1, 1)
    assert call["end_date"] == date(2026, 10, 22)
    assert call.get("limit") is None
    assert result["checkpoint"] == "catalog-range-v1:2024-01-01:2026-10-22"


def test_historical_resume_uses_range_not_execution_date():
    repo = Repository()
    with pytest.raises(RuntimeError, match="source unavailable"):
        module().collect(
            Service(fail=True), repo, as_of=date(2026, 10, 22),
            start_date=date(2024, 1, 1), end_date=date(2026, 10, 22),
        )
    service = Service()
    module().collect(
        service, repo, as_of=date(2026, 10, 23),
        start_date=date(2024, 1, 1), end_date=date(2026, 10, 22),
    )
    assert service.calls[0]["completed_ids"] == frozenset({"PF1"})


def test_complete_recent_sweep_does_not_skip_historical_range():
    service, repo = Service(), Repository()
    module().collect(service, repo, as_of=date(2026, 10, 22))
    module().collect(
        service, repo, as_of=date(2026, 10, 22),
        start_date=date(2024, 1, 1), end_date=date(2026, 10, 22),
    )
    assert len(service.calls) == 2
    assert service.calls[1]["completed_ids"] == frozenset()


@pytest.mark.parametrize("start,end", [
    (date(2024, 1, 1), None),
    (None, date(2026, 10, 22)),
    (date(2026, 10, 23), date(2024, 1, 1)),
])
def test_invalid_explicit_range_makes_no_collection_or_checkpoint_writes(start, end):
    service, repo = Service(), Repository()
    with pytest.raises(ValueError):
        module().collect(
            service, repo, as_of=date(2026, 10, 22), start_date=start, end_date=end,
        )
    assert service.calls == []
    assert repo.checkpoints == {}


def test_cloud_entrypoint_passes_execution_range(monkeypatch):
    from contextlib import nullcontext

    target = module()
    service, repo = Service(), Repository()
    monkeypatch.setenv("COLLECTION_DATE", "2026-10-22")
    monkeypatch.setenv("COLLECTION_START", "2024-01-01")
    monkeypatch.setenv("COLLECTION_END", "2026-10-22")
    monkeypatch.setenv("KOPIS_API_KEY", "test")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test")
    monkeypatch.setattr(target, "KopisClient", lambda settings: nullcontext(object()))
    monkeypatch.setattr(target, "SupabaseRepository", lambda settings: nullcontext(repo))
    monkeypatch.setattr(target, "KopisSyncService", lambda client, repository: service)
    monkeypatch.setattr(target.signal, "signal", lambda *args: None)
    assert target.main() == 0
    assert service.calls[0]["start_date"] == date(2024, 1, 1)
    assert service.calls[0]["end_date"] == date(2026, 10, 22)
