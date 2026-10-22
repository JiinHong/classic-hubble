import copy
import importlib
import importlib.util
import json
from types import SimpleNamespace

import httpx
import pytest
from classic_hubble_pipeline.music_extraction import digest, json_bytes, prepare_request
from classic_hubble_pipeline.openai_music import OpenAIMusicClient
from test_music_extraction import document, response
from test_openai_music import api_response


def module():
    name = "classic_hubble_pipeline.music_cache"
    assert importlib.util.find_spec(name), "Durable paid-response cache is missing"
    return importlib.import_module(name)


class Repository:
    def __init__(self):
        self.rows = {}
        self.fail_finish = False

    def load_music_request(self, key):
        return copy.deepcopy(self.rows.get(key))

    def claim_music_request(self, key, payload):
        if key in self.rows:
            return False
        self.rows[key] = copy.deepcopy(payload)
        return True

    def finish_music_request(self, key, owner, payload):
        row = self.rows[key]
        if self.fail_finish or row["owner"] != owner or row["status"] != "claimed":
            return False
        self.rows[key] = copy.deepcopy(payload)
        return True


class Store:
    bucket = "private-evidence"

    def __init__(self):
        self.objects = {}
        self.fail_archive = False

    def archive_extraction_result(self, value):
        if self.fail_archive:
            raise RuntimeError("storage unavailable")
        sha = digest(value)
        key = f"extractions/sha256/{sha[:2]}/{sha}"
        self.objects[key] = json_bytes(value)
        return SimpleNamespace(key=key, sha256=sha)

    def read(self, key):
        return self.objects[key]


@pytest.fixture
def setup():
    repo, store, calls = Repository(), Store(), []
    bundle = prepare_request(document(), "b" * 64)

    def handle(request):
        calls.append(request)
        row = repo.rows[digest(json.loads(request.content))]
        assert row["status"] == "claimed"
        assert row["maximum_cost_usd"] > 0
        return httpx.Response(200, json=api_response())

    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        client = OpenAIMusicClient("secret-test", http_client=http)
        yield repo, store, calls, bundle, client


def test_claim_precedes_payment_and_restart_reuses_verified_result(setup):
    repo, store, calls, bundle, client = setup
    result = module().MusicResponseCache(repo, store).extract(client, bundle)
    replay = module().MusicResponseCache(repo, store).extract(client, bundle)
    assert result == replay
    assert result.payload == response()
    assert len(calls) == 1
    row = repo.rows[client.cache_key(bundle)]
    assert row["status"] == "succeeded"
    assert row["cost_usd"] == pytest.approx(0.0008)
    assert row["unknown_charge_usd"] == 0
    assert row["usage"]["input_tokens"] == 3000
    assert "secret-test" not in json.dumps(repo.rows)
    assert "items" not in row  # Full evidence is private R2, not duplicated in metadata.


@pytest.mark.parametrize("status", ["claimed", "failed"])
def test_unfinished_or_failed_attempts_never_trigger_another_paid_request(setup, status):
    repo, store, calls, bundle, client = setup
    repo.rows[client.cache_key(bundle)] = {"status": status}
    with pytest.raises(module().CachedRequestUnavailable):
        module().MusicResponseCache(repo, store).extract(client, bundle)
    assert calls == []


def test_lost_claim_race_never_pays(setup):
    repo, store, calls, bundle, client = setup
    repo.claim_music_request = lambda *args: False
    with pytest.raises(module().CachedRequestUnavailable):
        module().MusicResponseCache(repo, store).extract(client, bundle)
    assert calls == []


@pytest.mark.parametrize("known_usage", [False, True])
def test_api_failure_keeps_known_or_unknown_charge_without_retry(setup, known_usage):
    repo, store, calls, bundle, _ = setup

    def handle(request):
        calls.append(request)
        if known_usage:
            return httpx.Response(200, json=api_response(status="incomplete"))
        raise httpx.ReadTimeout("private OCR secret", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        client = OpenAIMusicClient("secret-test", http_client=http)
        cache = module().MusicResponseCache(repo, store)
        with pytest.raises(module().CachedRequestUnavailable):
            cache.extract(client, bundle)
        with pytest.raises(module().CachedRequestUnavailable):
            cache.extract(client, bundle)
        row = repo.rows[client.cache_key(bundle)]
        assert row["status"] == "failed"
        assert row["cost_usd"] == (pytest.approx(0.0008) if known_usage else None)
        assert row["unknown_charge_usd"] == (0 if known_usage else client.maximum_cost(bundle))
        assert "private OCR secret" not in json.dumps(row)
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["storage", "metadata"])
def test_persistence_failure_does_not_repay_and_keeps_usage_when_possible(setup, failure):
    repo, store, calls, bundle, client = setup
    store.fail_archive = failure == "storage"
    repo.fail_finish = failure == "metadata"
    cache = module().MusicResponseCache(repo, store)
    with pytest.raises(module().CachedRequestUnavailable):
        cache.extract(client, bundle)
    with pytest.raises(module().CachedRequestUnavailable):
        cache.extract(client, bundle)
    assert len(calls) == 1
    row = repo.rows[client.cache_key(bundle)]
    if failure == "storage":
        assert row["cost_usd"] == pytest.approx(0.0008)
        assert row["unknown_charge_usd"] == 0
    else:
        assert row["status"] == "claimed"
        assert row["unknown_charge_usd"] == client.maximum_cost(bundle)


@pytest.mark.parametrize("change", ["bytes", "request", "bucket", "model", "document"])
def test_invalid_cached_evidence_never_falls_back_to_paid_inference(setup, change):
    repo, store, calls, bundle, client = setup
    cache = module().MusicResponseCache(repo, store)
    cache.extract(client, bundle)
    row = repo.rows[client.cache_key(bundle)]
    key = row["result_object_key"]
    if change == "bytes":
        store.objects[key] = b"corrupted"
    elif change == "bucket":
        row["bucket"] = "wrong-bucket"
    else:
        envelope = json.loads(store.objects[key])
        if change == "request":
            envelope["request_key"] = "c" * 64
        elif change == "model":
            envelope["result"]["model"] = "other-model"
        else:
            envelope["result"]["payload"]["document_sha256"] = "c" * 64
        stored = store.archive_extraction_result(envelope)
        row.update(result_object_key=stored.key, result_sha256=stored.sha256)
    with pytest.raises(module().CachedRequestUnavailable):
        cache.extract(client, bundle)
    assert len(calls) == 1


def test_imported_historical_response_is_reusable_without_network(setup):
    repo, store, calls, bundle, client = setup
    from classic_hubble_pipeline.openai_music import InferenceResult, TokenUsage
    result = InferenceResult(response(), 3000, 1000, "resp_previous", usage=TokenUsage(3000, 1000))
    cache = module().MusicResponseCache(repo, store)
    cache.import_result(client, bundle, result)
    assert cache.extract(client, bundle) == result
    assert cache.import_result(client, bundle, result) == result
    assert calls == []
    assert len(repo.rows) == 1
    assert next(iter(repo.rows.values()))["origin"] == "historical_import"


def test_changed_prompt_is_a_different_request(setup):
    repo, store, calls, bundle, client = setup
    cache = module().MusicResponseCache(repo, store)
    cache.extract(client, bundle)
    changed = copy.deepcopy(bundle)
    changed["instructions"] += " Updated instruction."
    cache.extract(client, changed)
    assert len(repo.rows) == 2
    assert len(calls) == 2
