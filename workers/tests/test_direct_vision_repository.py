import json

import httpx

from classic_hubble_pipeline.supabase import SupabaseRepository, SupabaseSettings


def test_direct_vision_metadata_is_private_provider_scoped_and_insert_only():
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"payload": {"status": "unreadable"}}])
        return httpx.Response(201, json=[{"id": "saved"}] if len(requests) == 2 else [])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "test-secret"), http_client=client)
        assert hasattr(repo, "load_direct_vision_result"), "Direct vision metadata reader is missing"
        assert repo.load_direct_vision_result("hash") == {"status": "unreadable"}
        assert repo.save_direct_vision_result("hash", {"status": "unreadable"}, "run")
        assert not repo.save_direct_vision_result("hash", {"status": "text_extracted"}, "run")
    assert requests[0].url.params["provider"] == "eq.codex_vision"
    assert requests[0].url.params["entity_type"] == "eq.direct_reading"
    assert requests[0].url.params["provider_id"] == "eq.hash"
    for request in requests[1:]:
        assert request.headers["prefer"] == "resolution=ignore-duplicates,return=representation"
        assert request.url.params["on_conflict"] == "provider,entity_type,provider_id"
        payload = json.loads(request.content)
        assert payload["provider"] == "codex_vision"
        assert payload["entity_type"] == "direct_reading"
        assert payload["ingestion_run_id"] == "run"


def test_archive_hash_lookup_filters_in_database_and_keeps_shared_sources():
    requests = []
    def handler(request):
        requests.append(request)
        index = len(requests)
        return httpx.Response(200, json=[{"id": str(index), "payload": {"source_url": f"url{index}"}}] if index < 3 else [])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "test-secret"), http_client=client)
        result = repo.load_source_archives(source_sha256="a" * 64, bucket="bucket", page_size=1)
    assert len(result) == 2
    for request in requests:
        assert request.url.params["payload->>sha256"] == "eq." + "a" * 64
        assert request.url.params["payload->>bucket"] == "eq.bucket"
    assert [r.url.params["offset"] for r in requests] == ["0", "1", "2"]


def test_publication_uses_single_rpc_not_delete_then_insert():
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": "p1"}])
        return httpx.Response(200, json={"status": "published", "items": 2})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "secret"), http_client=client)
        assert hasattr(repo, "load_vision_target"), "Publication snapshot reader missing"
        assert repo.load_vision_target("p1") == {"id": "p1"}
        assert repo.publish_direct_vision({"p_performance_id": "p1"})["items"] == 2
    assert requests[1].url.path == "/rest/v1/rpc/publish_direct_vision_program"
    assert len(requests) == 2


def test_publication_fetches_only_its_source_url():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[{"payload": {"source_url": "url"}}])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "secret"), http_client=client)
        assert hasattr(repo, "load_vision_source"), "Targeted source lookup missing"
        assert repo.load_vision_source("url") == {"source_url": "url"}
    assert requests[0].url.params["provider"] == "eq.r2"
    assert requests[0].url.params["entity_type"] == "eq.source_archive"
    assert requests[0].url.params["limit"] == "1"
