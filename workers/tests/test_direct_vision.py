"""Synthetic fixtures test ingestion, not image-reading accuracy."""

import copy
import hashlib
import importlib
import importlib.util

import pytest

from classic_hubble_pipeline.music_extraction import MAX_RESPONSE_BYTES, json_bytes
from classic_hubble_pipeline.r2 import StoredObject
from test_music_extraction import WORK, document, response


def module():
    name = "classic_hubble_pipeline.direct_vision"
    assert importlib.util.find_spec(name) is not None, "Direct image evidence import is missing"
    return importlib.import_module(name)


class Store:
    bucket = "test-bucket"

    def __init__(self):
        self.source = b"synthetic image fixture, not an observed image"
        self.sha = hashlib.sha256(self.source).hexdigest()
        self.key = f"originals/sha256/{self.sha[:2]}/{self.sha}"
        self.objects = {self.key: self.source}
        self.saved = []

    def read(self, key):
        return self.objects[key]

    def archive_extraction_result(self, result):
        self.saved.append(copy.deepcopy(result))
        data = json_bytes(result)
        sha = hashlib.sha256(data).hexdigest()
        key = f"extractions/sha256/{sha[:2]}/{sha}"
        self.objects[key] = data
        return StoredObject(key, sha, len(data), "application/json", True)


class Repository:
    def __init__(self, store):
        self.sources = [{
            "sha256": store.sha, "object_key": store.key, "bucket": store.bucket,
            "source_url": "https://kopis.or.kr/upload/test.png",
            "content_type": "image/png", "performance_ids": ["p1"],
            "checked_at": "2026-10-22T10:00:00+00:00",
        }]
        self.cached = {}
        self.works = [WORK]
        self.writes = []
        self.runs = []
        self.finished = []

    def load_source_archives(self, *, source_sha256, bucket):
        assert source_sha256 in {None, self.sources[0]["sha256"]} if self.sources else True
        return copy.deepcopy(self.sources)

    def load_work_catalog(self):
        return self.works

    def load_direct_vision_result(self, key):
        return copy.deepcopy(self.cached.get(key))

    def save_direct_vision_result(self, key, payload, run_id):
        if key in self.cached:
            return False
        self.cached[key] = copy.deepcopy(payload)
        self.writes.append((key, copy.deepcopy(payload), run_id))
        return True

    def start_ingestion_run(self, provider):
        self.runs.append(provider)
        return "run1"

    def finish_ingestion_run(self, run_id, **kwargs):
        self.finished.append(kwargs)


def reading(store):
    return {
        "source_sha256": store.sha,
        "observed_at": "2026-10-22T11:00:00+00:00",
        "coverage": "complete",
        "status": "text_extracted",
        "lines": document()["lines"],
        "extraction_status": "items_extracted",
        "items": response()["items"],
        "notes": "Synthetic unit-test transcription only.",
    }


def run(repo, store, data=None, **kwargs):
    return module().import_reading(repo, store, store.sha, json_bytes(data or reading(store)), **kwargs)


def test_prepare_exports_hash_verified_bytes_without_ocr_or_model_calls(tmp_path):
    store = Store()
    repo = Repository(store)
    result = module().prepare(repo, store, store.sha, tmp_path / "source")
    assert result["mode"] == "prepared"
    assert (tmp_path / "source" / "original.png").read_bytes() == store.source
    assert (tmp_path / "source").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "source" / "original.png").stat().st_mode & 0o777 == 0o600
    assert result["source_sha256"] == store.sha
    assert result["method"] == "chat_model_direct_image_reading"
    assert not repo.writes and not store.saved
    with pytest.raises(FileExistsError):
        module().prepare(repo, store, store.sha, tmp_path / "source")


def test_dry_run_matches_exact_transcription_but_never_publishes():
    store = Store()
    repo = Repository(store)
    result = run(repo, store)
    assert result["mode"] == "dry_run"
    assert result["full_work_matches"] == 1
    assert result["published_items"] == 0
    assert not repo.writes and not store.saved and not repo.runs


def test_apply_keeps_separate_provenance_and_immutable_cached_reading(tmp_path):
    store = Store()
    repo = Repository(store)
    result = run(repo, store, apply=True)
    assert result["mode"] == "stored"
    saved = store.saved[0]
    assert saved["method"] == "chat_model_direct_image_reading"
    assert saved["pipeline_version"] == "codex-direct-vision-v1"
    assert saved["reading"] == reading(store)
    assert saved["sources"][0]["source_url"] == repo.sources[0]["source_url"]
    assert saved["matching"]["items"][0]["suggested_work_id"] == "rach-2"
    assert saved["publication_status"] == "not_published"
    assert "confidence" not in saved and "model" not in saved
    assert repo.runs == ["codex_vision"]
    assert repo.finished[-1]["status"] == "completed"
    assert "reading" not in repo.writes[0][1]
    assert "matching" not in repo.writes[0][1]
    assert run(repo, store, apply=True)["mode"] == "cached"
    assert len(repo.writes) == len(store.saved) == 1
    assert module().prepare(repo, store, store.sha, tmp_path / "repeat")["mode"] == "cached"
    assert not (tmp_path / "repeat").exists()
    different = reading(store)
    different["notes"] = "Do not replace the first observation silently"
    with pytest.raises(ValueError, match="different reading"):
        run(repo, store, different, apply=True)


@pytest.mark.parametrize("problem", ["hash", "bucket", "removed", "key"])
def test_stale_or_corrupt_source_cannot_be_imported(problem):
    store = Store()
    repo = Repository(store)
    if problem == "hash":
        store.objects[store.key] += b"corrupt"
    elif problem == "bucket":
        repo.sources[0]["bucket"] = "other"
    elif problem == "removed":
        repo.sources = []
    else:
        repo.sources[0]["object_key"] = "originals/sha256/aa/" + "a" * 64
    with pytest.raises(ValueError):
        run(repo, store, apply=True)
    assert not repo.writes and not store.saved

@pytest.mark.parametrize("problem", ["source", "timezone", "future", "extra", "invented_quote", "empty", "status", "line"])
def test_invalid_or_ungrounded_reading_is_rejected_before_persistence(problem):
    store = Store()
    repo = Repository(store)
    data = reading(store)
    if problem == "source":
        data["source_sha256"] = "a" * 64
    elif problem == "timezone":
        data["observed_at"] = "2026-10-22T11:00:00"
    elif problem == "future":
        data["observed_at"] = "2099-01-01T00:00:00Z"
    elif problem == "extra":
        data["confidence"] = 0.99
    elif problem == "invented_quote":
        data["items"][0]["catalogue"][0]["quote"] = "Op. 99"
    elif problem == "empty":
        data["lines"] = []
    elif problem == "status":
        data["extraction_status"] = "no_program_identified"
    else:
        data["lines"][0]["page_index"] = -1
    with pytest.raises(ValueError):
        run(repo, store, data, apply=True)
    assert not repo.writes and not store.saved


@pytest.mark.parametrize("status", ["no_text", "unreadable"])
def test_no_text_and_unreadable_have_distinct_durable_outcomes(status):
    store = Store()
    repo = Repository(store)
    data = reading(store)
    data.update(status=status, lines=[], items=[], extraction_status="uncertain")
    result = run(repo, store, data, apply=True)
    assert result["status"] == status
    assert result["full_work_matches"] == 0
    assert store.saved[0]["matching"] is None
    assert repo.writes[0][1]["status"] == status


def test_partial_view_preserves_identity_but_is_not_eligible_for_automatic_publication():
    store = Store()
    repo = Repository(store)
    data = reading(store)
    data["coverage"] = "partial"
    result = run(repo, store, data, apply=True)
    assert result["full_work_matches"] == 1
    assert result["eligible_for_publication"] is False


def test_no_program_text_does_not_load_catalogue_or_become_publishable():
    store = Store()
    repo = Repository(store)
    data = reading(store)
    data.update(items=[], extraction_status="no_program_identified")

    def unexpected_catalogue_read():
        raise AssertionError("A biography-only image needs no work catalogue")

    repo.load_work_catalog = unexpected_catalogue_read
    result = run(repo, store, data, apply=True)
    assert result["item_count"] == 0
    assert result["eligible_for_publication"] is False
    assert store.saved[0]["reading"]["extraction_status"] == "no_program_identified"


def test_db_missing_work_is_not_invented_or_forced():
    store = Store()
    repo = Repository(store)
    repo.works = []
    result = run(repo, store, apply=True)
    assert result["full_work_matches"] == 0
    item = store.saved[0]["matching"]["items"][0]
    assert item["candidate_ids"] == []
    assert item["reason"] == "composer_unconfirmed"


def test_cached_reading_rechecks_current_catalogue_without_rewriting_evidence(tmp_path):
    store = Store()
    repo = Repository(store)
    assert run(repo, store, apply=True)["full_work_matches"] == 1
    original = copy.deepcopy(store.objects)
    repo.works = []
    assert run(repo, store, apply=True)["full_work_matches"] == 0
    assert module().prepare(repo, store, store.sha, tmp_path / "cached")[
        "eligible_for_publication"
    ] is False
    assert store.objects == original
    assert len(repo.writes) == 1


def test_source_change_during_matching_is_rechecked_before_durable_import():
    store = Store()
    repo = Repository(store)
    def change():
        repo.sources = []
        return repo.works
    repo.load_work_catalog = change
    with pytest.raises(ValueError):
        run(repo, store, apply=True)
    assert not repo.writes and not store.saved


def test_storage_failure_does_not_complete_or_record_raw_error():
    store = Store()
    repo = Repository(store)
    def fail(_):
        raise RuntimeError("private error detail")
    store.archive_extraction_result = fail
    with pytest.raises(RuntimeError):
        run(repo, store, apply=True)
    assert not repo.writes
    assert repo.finished[-1]["error"] == "RuntimeError"


def test_cache_corruption_never_triggers_a_new_observation(tmp_path):
    store = Store()
    repo = Repository(store)
    run(repo, store, apply=True)
    key = next(iter(repo.cached.values()))["result_object_key"]
    store.objects[key] += b"corrupt"
    with pytest.raises(ValueError):
        module().prepare(repo, store, store.sha, tmp_path / "no-fallback")
    assert not (tmp_path / "no-fallback").exists()
    assert len(repo.writes) == 1


def test_lost_db_ack_can_be_recovered_without_overwrite():
    store = Store()
    repo = Repository(store)
    save = repo.save_direct_vision_result
    def fail(key, payload, run_id):
        save(key, payload, run_id)
        raise RuntimeError("lost database acknowledgement")
    repo.save_direct_vision_result = fail
    with pytest.raises(RuntimeError):
        run(repo, store, apply=True)
    assert run(repo, store, apply=True)["mode"] == "cached"
    assert len(repo.writes) == len(store.saved) == 1


def test_cache_record_bound_to_source_bucket_pipeline_and_reading():
    store = Store()
    repo = Repository(store)
    run(repo, store, apply=True)
    row = next(iter(repo.cached.values()))
    row["source_sha256"] = "a" * 64
    with pytest.raises(ValueError):
        run(repo, store, apply=True)


def test_invalid_timestamp_does_not_echo_untrusted_input():
    store = Store()
    repo = Repository(store)
    data = reading(store)
    data["observed_at"] = "SECRET invalid timestamp"
    with pytest.raises(ValueError) as error:
        run(repo, store, data, apply=True)
    assert "SECRET" not in str(error.value)


def test_oversized_saved_envelope_is_rejected_before_any_completion_write():
    store = Store()
    repo = Repository(store)
    data = reading(store)
    repo.works = []
    # Repeated, valid quotes can expand the report beyond the input size limit.
    data["lines"] = [
        {"text": f"Synthetic name {index} " + "x" * 1900, "page_index": 0}
        for index in range(20)
    ]
    item = copy.deepcopy(data["items"][0])
    quotes = [
        {"line_id": f"L{index:06}", "quote": line["text"]}
        for index, line in enumerate(data["lines"])
    ]
    item.update(composer=quotes, catalogue=None, key=None, movements=[])
    data["items"] = []
    for index in range(13):
        title = f"Synthetic long title {index} " + "x" * 1800
        data["lines"].append({"text": title, "page_index": 0})
        next_item = copy.deepcopy(item)
        next_item["title"] = [{"line_id": f"L{index + 20:06}", "quote": title}]
        data["items"].append(next_item)
    assert len(json_bytes(data)) < MAX_RESPONSE_BYTES
    with pytest.raises(ValueError, match="Saved reading size limit"):
        run(repo, store, data, apply=True)
    assert not repo.writes and not store.saved


def test_concurrent_identical_result_is_reused_and_different_result_is_not_overwritten():
    store = Store()
    repo = Repository(store)
    save = repo.save_direct_vision_result
    def concurrent(key, payload, run_id):
        save(key, payload, run_id)
        return False
    repo.save_direct_vision_result = concurrent
    assert run(repo, store, apply=True)["mode"] == "stored"
    assert len(repo.writes) == 1


def test_source_changes_after_starting_run_are_not_saved():
    store = Store()
    repo = Repository(store)
    start = repo.start_ingestion_run
    def change(provider):
        repo.sources = []
        return start(provider)
    repo.start_ingestion_run = change
    with pytest.raises(ValueError):
        run(repo, store, apply=True)
    assert not repo.writes and not store.saved
