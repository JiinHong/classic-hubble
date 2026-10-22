import hashlib
import importlib
import importlib.util
from datetime import date

import httpx
import pytest

URL = "http://www.kopis.or.kr/upload/pfmIntroImage/program.jpg"
IMAGE = b"\xff\xd8\xfforiginal"


def module():
    assert (
        importlib.util.find_spec("classic_hubble_pipeline.source_archive") is not None
    )
    return importlib.import_module("classic_hubble_pipeline.source_archive")


def test_download_upgrades_kopis_to_https_and_identifies_image():
    def handler(request):
        assert request.url.scheme == "https"
        assert request.url.host == "kopis.or.kr"
        return httpx.Response(200, content=IMAGE)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        data, kind = module().download_source(client, URL)
    assert data == IMAGE
    assert kind == "image/jpeg"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/internal",
        "https://example.com/image.jpg",
        "https://www.kopis.or.kr.evil.com/upload/file.jpg",
        "https://user:pass@www.kopis.or.kr/upload/file.jpg",
        "https://www.kopis.or.kr:444/upload/file.jpg",
    ],
)
def test_download_rejects_unknown_hosts_before_fetch(url):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("must not fetch"))
        ) as client,
        pytest.raises(module().SourceDownloadError),
    ):
        module().download_source(client, url)


def test_download_does_not_follow_redirects_or_store_html():
    for response in [
        httpx.Response(302, headers={"location": "http://169.254.169.254/"}),
        httpx.Response(200, content=b"<html>Error</html>"),
    ]:
        with (
            httpx.Client(
                transport=httpx.MockTransport(lambda _, reply=response: reply),
                follow_redirects=True,
            ) as client,
            pytest.raises(module().SourceDownloadError),
        ):
            module().download_source(client, URL)


def test_stream_download_enforces_actual_size_without_content_length():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=IMAGE))
        ) as client,
        pytest.raises(module().SourceDownloadError, match="size"),
    ):
        module().download_source(client, URL, max_bytes=3)


class Repository:
    def __init__(self, urls=None):
        self.urls = urls or [URL, URL]
        self.records = {}
        self.finished = []
        self.started = []
        self.queries = []

    def start_ingestion_run(self, provider):
        self.started.append(provider)
        return "run-1"

    def finish_ingestion_run(self, run_id, **kwargs):
        self.finished.append(kwargs)

    def load_source_performances(self, **kwargs):
        self.queries.append(kwargs)
        return [{"id": "p1", "intro_image_urls": self.urls}]

    def load_source_archives(self):
        return [
            v for (entity, _), v in self.records.items() if entity == "source_archive"
        ]

    def upsert_provider_record(self, *, entity_type, provider_id, payload, **kwargs):
        self.records[entity_type, provider_id] = dict(payload)
        return "record"


class Store:
    bucket = "classic-hubble-sources"

    def __init__(self):
        self.objects = {}

    def archive(self, content, content_type):
        from classic_hubble_pipeline.r2 import StoredObject

        digest = hashlib.sha256(content).hexdigest()
        key = f"originals/sha256/{digest[:2]}/{digest}"
        created = key not in self.objects
        self.objects[key] = content
        return StoredObject(key, digest, len(content), content_type, created)


def run(repo, store, handler, day=21, **kwargs):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return module().archive_sources(
            repo, store, client, as_of=date(2026, 10, day), **kwargs
        )


def test_default_archive_window_still_uses_calendar_months():
    repo = Repository()
    run(repo, Store(), lambda _: httpx.Response(200, content=IMAGE))
    assert repo.queries == [{"start": date(2026, 7, 21), "end": date(2027, 4, 21)}]


@pytest.mark.parametrize("start,end", [
    (date(2024, 1, 1), date(2026, 10, 22)),
    (date(2024, 2, 29), date(2024, 2, 29)),
])
def test_explicit_archive_window_replaces_recent_window(start, end):
    repo = Repository()
    result = run(
        repo, Store(), lambda _: httpx.Response(200, content=IMAGE),
        start_date=start, end_date=end,
    )
    assert repo.queries == [{"start": start, "end": end}]
    assert result["status"] == "completed"
    assert result["counters"]["archived"] == 1


@pytest.mark.parametrize("start,end", [
    (date(2024, 1, 1), None),
    (None, date(2026, 10, 22)),
    (date(2026, 10, 22), date(2024, 1, 1)),
])
def test_invalid_archive_window_fails_before_any_side_effect(start, end):
    repo, store = Repository(), Store()
    with pytest.raises(ValueError):
        run(
            repo, store, lambda _: pytest.fail("must not download"),
            start_date=start, end_date=end,
        )
    assert repo.started == []
    assert repo.queries == []
    assert repo.records == {}
    assert store.objects == {}


def test_historical_archive_resumes_with_pinned_collection_date():
    repo, store = Repository(), Store()
    dates = {"start_date": date(2024, 1, 1), "end_date": date(2026, 10, 22)}
    run(repo, store, lambda _: httpx.Response(200, content=IMAGE), day=22, **dates)
    result = run(
        repo, store, lambda _: pytest.fail("saved sources must be skipped"),
        day=22, **dates,
    )
    assert result["counters"]["skipped"] == 1
    assert result["counters"]["uploaded_bytes"] == 0
    assert len(store.objects) == 1


def test_archive_entrypoint_passes_execution_range(monkeypatch):
    from contextlib import nullcontext

    archive = module()
    repo, store = Repository(), Store()
    monkeypatch.setenv("COLLECTION_DATE", "2026-10-22")
    monkeypatch.setenv("COLLECTION_START", "2024-01-01")
    monkeypatch.setenv("COLLECTION_END", "2026-10-22")
    monkeypatch.setattr(archive.R2Settings, "from_env", lambda: None)
    monkeypatch.setattr(archive.SupabaseSettings, "from_env", lambda: None)
    monkeypatch.setattr(archive, "R2Store", lambda _: nullcontext(store))
    monkeypatch.setattr(archive, "SupabaseRepository", lambda _: nullcontext(repo))
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=IMAGE))
    ) as client:
        monkeypatch.setattr(archive.httpx, "Client", lambda **_: nullcontext(client))
        assert archive.main() == 0
    assert repo.queries == [{"start": date(2024, 1, 1), "end": date(2026, 10, 22)}]


def test_archival_deduplicates_urls_and_resumes_same_day_without_fetch():
    repo, store = Repository(), Store()
    first = run(repo, store, lambda _: httpx.Response(200, content=IMAGE))
    assert first["counters"]["archived"] == 1
    again = run(repo, store, lambda _: pytest.fail("completed source must be skipped"))
    assert again["counters"]["skipped"] == 1
    assert len(store.objects) == 1


def test_same_url_replacement_keeps_original_object_and_version():
    repo, store = Repository(), Store()
    run(repo, store, lambda _: httpx.Response(200, content=IMAGE))
    changed = run(
        repo, store, lambda _: httpx.Response(200, content=IMAGE + b"new"), day=22
    )
    assert changed["counters"]["changed"] == 1
    assert len(store.objects) == 2
    assert len([k for k in repo.records if k[0] == "source_version"]) == 2
    latest = repo.load_source_archives()[0]
    assert latest["sha256"] == hashlib.sha256(IMAGE + b"new").hexdigest()
    assert latest["source_url"] == URL
    assert latest["performance_ids"] == ["p1"]


def test_storage_failure_does_not_advance_source_checkpoint():
    repo = Repository()

    class FailingStore(Store):
        def archive(self, *args):
            raise RuntimeError("storage unavailable")

    with pytest.raises(RuntimeError):
        run(repo, FailingStore(), lambda _: httpx.Response(200, content=IMAGE))
    assert repo.load_source_archives() == []
    assert repo.finished[-1]["status"] == "failed"


def test_missing_source_is_recorded_and_other_urls_continue():
    repo, store = Repository([URL, URL + "2"]), Store()
    result = run(
        repo,
        store,
        lambda req: (
            httpx.Response(404)
            if str(req.url).endswith("jpg")
            else httpx.Response(200, content=IMAGE)
        ),
    )
    assert result["status"] == "failed"
    assert result["counters"]["source_errors"] == 1
    assert result["counters"]["archived"] == 1
    assert len(repo.load_source_archives()) == 1
    assert any(k[0] == "source_error" for k in repo.records)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_access_and_rate_limits_stop_archival(status):
    repo, store = Repository([URL, URL + "2"]), Store()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    result = run(repo, store, handler)
    assert result["status"] == "failed"
    assert len(calls) == 1
    assert repo.load_source_archives() == []


def test_repeated_failures_stop_after_five_requests():
    repo, store = Repository([URL + str(i) for i in range(10)]), Store()
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectTimeout("unavailable")

    result = run(repo, store, handler)
    assert result["counters"]["sources"] == 10
    assert result["status"] == "failed"
    assert len(calls) == 5


def test_unchanged_source_next_day_updates_check_time_without_new_object():
    repo, store = Repository(), Store()
    run(repo, store, lambda _: httpx.Response(200, content=IMAGE))
    result = run(repo, store, lambda _: httpx.Response(200, content=IMAGE), day=22)
    assert result["counters"]["changed"] == 0
    assert result["counters"]["reused"] == 1
    assert result["counters"]["uploaded_bytes"] == 0
    assert len(store.objects) == 1
    assert repo.load_source_archives()[0]["checked_on"] == "2026-10-22"


def test_failed_version_write_does_not_publish_checkpoint_and_can_resume():
    class FailingRepository(Repository):
        def upsert_provider_record(self, **kwargs):
            if kwargs["entity_type"] == "source_version":
                raise RuntimeError("database unavailable")
            return super().upsert_provider_record(**kwargs)

    repo, store = FailingRepository(), Store()
    with pytest.raises(RuntimeError):
        run(repo, store, lambda _: httpx.Response(200, content=IMAGE))
    assert repo.load_source_archives() == []
    result = run(Repository(), store, lambda _: httpx.Response(200, content=IMAGE))
    assert result["counters"]["reused"] == 1
