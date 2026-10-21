import hashlib
import importlib
import importlib.util
import io
import json

import pytest
from classic_hubble_pipeline.r2 import StoredObject
from test_music_extraction import WORK, document, response


def module():
    name = "classic_hubble_pipeline.music_review"
    assert importlib.util.find_spec(name) is not None, (
        "Private extraction import is missing"
    )
    return importlib.import_module(name)


class Store:
    bucket = "test-bucket"

    def __init__(self):
        doc = document()
        doc.update(
            bucket=self.bucket, source_object_key="originals/sha256/aa/" + "a" * 64
        )
        self.data = json.dumps(doc).encode()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.saved = []

    def read(self, key):
        assert key == f"ocr/sha256/{self.sha[:2]}/{self.sha}"
        return self.data

    def archive_extraction_result(self, result):
        self.saved.append(result)
        data = json.dumps(result, sort_keys=True).encode()
        sha = hashlib.sha256(data).hexdigest()
        return StoredObject(
            f"extractions/sha256/{sha[:2]}/{sha}",
            sha,
            len(data),
            "application/json",
            True,
        )


class Repository:
    def __init__(self, store):
        self.ocr = [
            {
                "bucket": store.bucket,
                "status": "text_extracted",
                "source_sha256": "a" * 64,
                "source_object_key": "originals/sha256/aa/" + "a" * 64,
                "pipeline_version": "ocr-test-v1",
                "result_sha256": store.sha,
                "result_object_key": f"ocr/sha256/{store.sha[:2]}/{store.sha}",
                "processed_at": "2026-10-21T01:00:00+00:00",
            }
        ]
        self.sources = [
            {
                "bucket": store.bucket,
                "sha256": "a" * 64,
                "object_key": "originals/sha256/aa/" + "a" * 64,
            }
        ]
        self.works = [WORK]
        self.writes = []
        self.runs = []
        self.finished = []

    def load_ocr_results(self):
        return self.ocr

    def load_source_archives(self):
        return self.sources

    def load_work_catalog(self):
        return self.works

    def start_ingestion_run(self, provider):
        self.runs.append(provider)
        return "run1"

    def finish_ingestion_run(self, run_id, **kwargs):
        self.finished.append(kwargs)

    def upsert_provider_record(self, **kwargs):
        self.writes.append(kwargs)


def run(repo, store, **kwargs):
    return module().import_response(
        repo,
        store,
        store.sha,
        json.dumps(response(store.sha)).encode(),
        producer="manual-test",
        **kwargs,
    )


def test_prepare_reads_private_ocr_without_calls_or_writes():
    store = Store()
    repo = Repository(store)
    bundle = module().prepare(repo, store, store.sha)
    assert bundle["input"]["document_sha256"] == store.sha
    assert not store.saved and not repo.writes and not repo.runs


def test_import_dry_run_has_no_mutations():
    store = Store()
    repo = Repository(store)
    report = run(repo, store)
    assert report["mode"] == "dry_run"
    assert report["suggestions"] == 1
    assert not store.saved and not repo.writes and not repo.runs


def test_apply_saves_unpublished_evidence_before_private_metadata_and_repeats_safely():
    store = Store()
    repo = Repository(store)
    report = run(repo, store, apply=True)
    assert report["mode"] == "applied"
    assert store.saved[0]["publishable"] is False
    assert store.saved[0]["producer"] == "manual-test"
    saved = repo.writes[0]
    assert saved["provider"] == "music_extraction"
    assert saved["entity_type"] == "extraction_candidate"
    assert saved["payload"]["review_status"] == "unverified"
    assert "items" not in saved["payload"]
    assert "lines" not in saved["payload"]
    assert repo.finished[-1]["status"] == "completed"
    again = run(repo, store, apply=True)
    assert again["candidate_id"] == report["candidate_id"]
    repo.works = []
    changed = run(repo, store, apply=True)
    assert changed["candidate_id"] != report["candidate_id"]


@pytest.mark.parametrize("problem", ["source", "bucket", "metadata", "hash", "old_ocr"])
def test_stale_or_corrupt_input_is_rejected_before_writes(problem):
    store = Store()
    repo = Repository(store)
    if problem == "source":
        repo.sources = []
    elif problem == "bucket":
        repo.ocr[0]["bucket"] = "different-bucket"
    elif problem == "metadata":
        repo.ocr[0]["pipeline_version"] = "not-the-file-version"
    elif problem == "hash":
        store.data += b" "
    else:
        repo.ocr.append(
            {
                **repo.ocr[0],
                "result_sha256": "f" * 64,
                "processed_at": "2026-10-21T02:00:00+00:00",
            }
        )
    with pytest.raises(ValueError):
        run(repo, store, apply=True)
    assert not store.saved and not repo.writes


def test_storage_failure_does_not_create_completion_record():
    store = Store()
    repo = Repository(store)

    def failed(_):
        raise RuntimeError("private provider details")

    store.archive_extraction_result = failed
    with pytest.raises(RuntimeError):
        run(repo, store, apply=True)
    assert not repo.writes
    assert repo.finished[-1]["status"] == "failed"
    assert repo.finished[-1]["error"] == "RuntimeError"


def test_source_changed_after_validation_cannot_be_imported():
    store = Store()
    repo = Repository(store)
    original = repo.start_ingestion_run

    def change(provider):
        repo.sources = []
        return original(provider)

    repo.start_ingestion_run = change
    with pytest.raises(ValueError):
        run(repo, store, apply=True)
    assert not repo.writes and not store.saved


def test_database_failure_remains_retryable_and_does_not_claim_success():
    store = Store()
    repo = Repository(store)
    save = repo.upsert_provider_record

    def failed(**kwargs):
        raise RuntimeError("private database details")

    repo.upsert_provider_record = failed
    with pytest.raises(RuntimeError):
        run(repo, store, apply=True)
    assert len(store.saved) == 1 and not repo.writes
    assert repo.finished[-1]["status"] == "failed"
    repo.upsert_provider_record = save
    assert run(repo, store, apply=True)["mode"] == "applied"
    assert store.saved[0] == store.saved[1]


def test_ocr_timestamp_is_required_even_with_no_older_versions():
    store = Store()
    repo = Repository(store)
    repo.ocr[0]["processed_at"] = "2026-10-21T00:00:00"
    with pytest.raises(ValueError, match="timezone"):
        module().prepare(repo, store, store.sha)


def test_cli_prepare_writes_private_file_without_overwrite(tmp_path):
    store = Store()
    repo = Repository(store)
    output = tmp_path / "request.json"
    stdout, stderr = io.StringIO(), io.StringIO()
    args = ["prepare", "--ocr-sha", store.sha, "--output", str(output)]
    assert (
        module().main(args, repository=repo, store=store, stdout=stdout, stderr=stderr)
        == 0
    )
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_text())["input"]["document_sha256"] == store.sha
    assert (
        module().main(args, repository=repo, store=store, stdout=stdout, stderr=stderr)
        == 1
    )
    assert "Sergei" not in stdout.getvalue()


def test_cli_import_default_dry_run_and_errors_are_redacted(tmp_path):
    store = Store()
    repo = Repository(store)
    path = tmp_path / "response.json"
    path.write_text(json.dumps(response(store.sha)))
    stdout, stderr = io.StringIO(), io.StringIO()
    args = [
        "import",
        "--ocr-sha",
        store.sha,
        "--response",
        str(path),
        "--producer",
        "manual-test",
    ]
    assert (
        module().main(args, repository=repo, store=store, stdout=stdout, stderr=stderr)
        == 0
    )
    assert json.loads(stdout.getvalue())["mode"] == "dry_run"
    assert not repo.writes
    path.write_text("SECRET invalid payload")
    assert (
        module().main(args, repository=repo, store=store, stdout=stdout, stderr=stderr)
        == 1
    )
    assert "SECRET" not in stderr.getvalue()
