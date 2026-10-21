import hashlib
import importlib
import io

import pytest
from classic_hubble_pipeline.ocr import PIPELINE_VERSION
from classic_hubble_pipeline.r2 import R2Error, StoredObject
from PIL import Image


def module():
    return importlib.import_module("classic_hubble_pipeline.ocr_worker")


class Store:
    bucket = "test-bucket"

    def __init__(self):
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(buf, format="PNG")
        self.data = buf.getvalue()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.reads = 0
        self.saved = []

    def read(self, key):
        self.reads += 1
        return self.data

    def archive_ocr_result(self, result):
        self.saved.append(result)
        return StoredObject(
            "ocr/sha256/aa/" + "a" * 64, "a" * 64, 100, "application/json", True
        )


class Repository:
    def __init__(self, store):
        self.sources = [
            {
                "sha256": store.sha,
                "bucket": store.bucket,
                "object_key": f"originals/sha256/{store.sha[:2]}/{store.sha}",
                "content_type": "image/png",
            }
        ] * 2
        self.records = {}
        self.finished = []

    def start_ingestion_run(self, provider):
        return "run1"

    def finish_ingestion_run(self, run_id, **kwargs):
        self.finished.append(kwargs)

    def load_source_archives(self):
        return self.sources

    def load_ocr_results(self):
        return [v for (kind, _), v in self.records.items() if kind == "ocr_result"]

    def upsert_provider_record(self, *, entity_type, provider_id, payload, **kwargs):
        self.records[entity_type, provider_id] = payload


def test_batch_deduplicates_by_hash_and_resumes_without_inference():
    store = Store()
    repo = Repository(store)
    result = module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert result["counters"]["processed"] == 1
    assert len(store.saved) == store.reads == 1
    metadata = repo.load_ocr_results()[0]
    assert metadata["status"] == "no_text"
    assert metadata["review_status"] == "unverified"
    assert "lines" not in metadata
    again = module().process_archives(
        repo, store, lambda _: pytest.fail(), max_seconds=60
    )
    assert again["counters"]["cached"] == 1
    assert store.reads == 1


def test_changed_pipeline_or_source_is_not_reused():
    store = Store()
    repo = Repository(store)
    repo.records["ocr_result", "old"] = {
        "source_sha256": store.sha,
        "pipeline_version": "old",
        "bucket": store.bucket,
        "status": "no_text",
    }
    module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert len(store.saved) == 1
    assert any(
        row["pipeline_version"] == PIPELINE_VERSION for row in repo.load_ocr_results()
    )


def test_storage_failure_never_marks_ocr_complete():
    store = Store()
    repo = Repository(store)

    def fail(_):
        raise R2Error("storage failure")

    store.archive_ocr_result = fail
    with pytest.raises(R2Error):
        module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert not repo.load_ocr_results()
    assert repo.finished[-1]["status"] == "failed"


def test_deadline_is_resumable_and_does_not_claim_all_completed():
    store = Store()
    repo = Repository(store)
    ticks = iter([0, 61])
    result = module().process_archives(
        repo, store, lambda _: [], max_seconds=60, clock=lambda: next(ticks)
    )
    assert result["complete"] is False
    assert result["counters"]["remaining"] == 1
    assert store.reads == 0


def test_pdf_gets_explicit_manual_handling_record_not_empty_success():
    store = Store()
    repo = Repository(store)
    repo.sources[0]["content_type"] = "application/pdf"
    result = module().process_archives(
        repo, store, lambda _: pytest.fail(), max_seconds=60
    )
    assert result["counters"]["manual"] == 1
    assert repo.load_ocr_results()[0]["status"] == "needs_manual_handling"
    assert store.reads == 0


def test_wrong_source_hash_is_never_processed():
    store = Store()
    repo = Repository(store)
    repo.sources[0]["sha256"] = "b" * 64
    with pytest.raises(ValueError):
        module().process_archives(repo, store, lambda _: pytest.fail(), max_seconds=60)
    assert not repo.load_ocr_results()


def test_termination_interrupt_is_not_swallowed_as_a_file_error():
    store = Store()
    repo = Repository(store)

    def interrupted(_):
        raise TimeoutError("termination")

    with pytest.raises(TimeoutError):
        module().process_archives(repo, store, interrupted, max_seconds=60)
    assert repo.finished[-1]["status"] == "failed"
    assert not repo.load_ocr_results()


def test_inference_failure_remains_pending_and_can_be_retried():
    store = Store()
    repo = Repository(store)

    def broken(_):
        raise RuntimeError("native inference failed")

    failed = module().process_archives(repo, store, broken, max_seconds=60)
    assert failed["status"] == "failed"
    assert failed["counters"]["remaining"] == 1
    assert repo.load_ocr_results() == []
    assert any(kind == "ocr_error" for kind, _ in repo.records)
    retried = module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert retried["complete"] is True
    assert retried["counters"]["processed"] == 1


def test_repeated_inference_failures_stop_after_five_sources():
    store = Store()
    repo = Repository(store)
    contents = {}
    repo.sources = []
    for i in range(10):
        content = store.data + str(i).encode()
        sha = hashlib.sha256(content).hexdigest()
        key = f"originals/sha256/{sha[:2]}/{sha}"
        contents[key] = content
        repo.sources.append(
            {
                "sha256": sha,
                "bucket": store.bucket,
                "object_key": key,
                "content_type": "image/png",
            }
        )
    store.read = contents.__getitem__
    calls = []

    def broken(_):
        calls.append(1)
        raise RuntimeError("inference failed")

    failed = module().process_archives(repo, store, broken, max_seconds=60)
    assert failed["status"] == "failed"
    assert failed["counters"]["remaining"] == 10
    assert len(calls) == 5


def test_failed_metadata_write_does_not_advance_result_and_retry_reuses_storage():
    store = Store()
    repo = Repository(store)
    real_save = repo.upsert_provider_record

    def fail(**kwargs):
        raise RuntimeError("database unavailable")

    repo.upsert_provider_record = fail
    with pytest.raises(RuntimeError):
        module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert len(store.saved) == 1
    assert not repo.load_ocr_results()
    repo.upsert_provider_record = real_save
    module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert store.saved[0] == store.saved[1]
    assert len(repo.load_ocr_results()) == 1


def test_old_source_result_is_not_reused_for_changed_image():
    store = Store()
    repo = Repository(store)
    module().process_archives(repo, store, lambda _: [], max_seconds=60)
    store.data += b"changed"
    store.sha = hashlib.sha256(store.data).hexdigest()
    repo.sources = [
        {
            "sha256": store.sha,
            "bucket": store.bucket,
            "object_key": f"originals/sha256/{store.sha[:2]}/{store.sha}",
            "content_type": "image/png",
        }
    ]
    result = module().process_archives(repo, store, lambda _: [], max_seconds=60)
    assert result["counters"]["processed"] == 1
    assert len(repo.load_ocr_results()) == 2
