from __future__ import annotations

import json

import httpx
import pytest

from classic_hubble_pipeline.supabase import (
    SupabaseConfigurationError,
    SupabaseRepository,
    SupabaseSettings,
)


def test_source_image_scan_covers_all_pages_in_collection_window():
    from datetime import date
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[{"id": "p1", "intro_image_urls": ["url"]}] if len(requests) == 1 else [])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "sb_secret_test"), http_client=client)
        assert len(repo.load_source_performances(start=date(2026, 7, 21), end=date(2027, 4, 21), page_size=1)) == 1
    assert [r.url.params["offset"] for r in requests] == ["0", "1"]
    assert requests[0].url.params["starts_on"] == "lte.2027-04-21"
    assert requests[0].url.params["ends_on"] == "gte.2026-07-21"
    assert requests[0].url.params["kopis_performance_id"] == "not.is.null"


def test_source_archive_states_are_read_only_from_private_r2_metadata():
    def handler(request):
        assert request.url.params["provider"] == "eq.r2"
        assert request.url.params["entity_type"] == "eq.source_archive"
        return httpx.Response(200, json=[{"id": "a", "payload": {"source_url": "url"}}])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(SupabaseSettings("https://example.supabase.co", "sb_secret_test"), http_client=client)
        assert repo.load_source_archives() == [{"source_url": "url"}]


def test_collection_checkpoint_is_private_provider_metadata():
    requests = []
    checkpoint = {"completed_ids": ["PF1"], "complete": False}

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"payload": checkpoint}])
        return httpx.Response(201)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings("https://example.supabase.co", "sb_secret_test"),
            http_client=client,
        )
        assert repo.load_collection_checkpoint("2026-10-21") == checkpoint
        repo.save_collection_checkpoint("2026-10-21", checkpoint)
    assert requests[0].url.params["entity_type"] == "eq.collection_checkpoint"
    assert requests[0].url.params["provider_id"] == "eq.2026-10-21"
    assert requests[0].url.params["provider"] == "eq.kopis"
    assert requests[1].url.params["on_conflict"] == "provider,entity_type,provider_id"
    assert json.loads(requests[1].content)["payload"] == checkpoint
    assert requests[1].headers["prefer"] == "resolution=merge-duplicates,return=minimal"


def test_load_work_catalog_uses_database_ids_and_stable_pagination():
    requests = []
    row = {
        "id": "w1",
        "slug": "a",
        "title": "Concerto",
        "title_ko": None,
        "catalogue": "Op. 18",
        "composers": {"name": "Composer", "name_ko": None},
        "work_aliases": [{"alias": "Alias"}],
    }

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[row] if len(requests) == 1 else [])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings("https://example.supabase.co", "sb_secret_test"),
            http_client=client,
        )
        works = repo.load_work_catalog(page_size=1)
    assert works[0].id == "w1"
    assert works[0].aliases == ("Alias",)
    assert [request.url.params["offset"] for request in requests] == ["0", "1"]
    assert all(request.url.params["order"] == "id.asc" for request in requests)


def test_link_program_item_is_conditional_and_cannot_overwrite_a_reviewed_match():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings("https://example.supabase.co", "sb_secret_test"),
            http_client=client,
        )
        changed = repo.link_program_item(
            {"id": "item", "display_title": "Concerto", "composer_name": "Composer"},
            "work",
        )
    assert changed is False
    assert requests[0].url.params["work_id"] == "is.null"
    assert requests[0].url.params["display_title"] == "eq.Concerto"
    assert requests[0].url.params["composer_name"] == "eq.Composer"
    assert requests[0].url.params["source_provider"] == "eq.nol"
    assert json.loads(requests[0].content) == {"work_id": "work"}


def test_unlinked_program_scan_reads_all_pages_before_mutating():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url.params["work_id"] == "is.null"
        assert request.url.params["source_provider"] == "eq.nol"
        return httpx.Response(200, json=[{"id": "a"}] if len(requests) == 1 else [])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings("https://example.supabase.co", "sb_secret_test"),
            http_client=client,
        )
        assert repo.load_unlinked_program_items(page_size=1) == [{"id": "a"}]
    assert len(requests) == 2


def test_settings_prefer_a_modern_secret_key():
    settings = SupabaseSettings.from_env(
        {
            "SUPABASE_URL": "https://project-ref.supabase.co",
            "SUPABASE_SECRET_KEY": "sb_secret_modern",
            "SUPABASE_SERVICE_ROLE_KEY": "legacy.jwt.value",
        }
    )

    assert settings.api_key == "sb_secret_modern"


def test_settings_reject_a_publishable_key_for_the_worker():
    with pytest.raises(SupabaseConfigurationError, match="secret"):
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_publishable_public",
        )


def test_modern_secret_key_is_sent_only_as_an_apikey_header():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=[{"id": "run-1"}])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    run_id = repository.start_ingestion_run("kopis")

    assert run_id == "run-1"
    assert requests[0].headers["apikey"] == "sb_secret_modern"
    assert "authorization" not in requests[0].headers
    assert requests[0].url.path == "/rest/v1/ingestion_runs"
    assert requests[0].headers["prefer"] == "return=representation"
    http_client.close()


def test_legacy_service_role_key_is_also_sent_as_a_bearer_token():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=[{"id": "run-1"}])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="legacy.service.role.jwt",
        ),
        http_client=http_client,
    )

    repository.start_ingestion_run("kopis")

    assert requests[0].headers["apikey"] == "legacy.service.role.jwt"
    assert requests[0].headers["authorization"] == ("Bearer legacy.service.role.jwt")
    http_client.close()


def test_provider_record_upsert_uses_its_natural_key():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=[{"id": "raw-1"}])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    repository.upsert_provider_record(
        entity_type="performance_detail",
        provider_id="PF300001",
        payload={"mt20id": "PF300001"},
        ingestion_run_id="run-1",
    )

    request = requests[0]
    assert request.url.path == "/rest/v1/provider_records"
    assert request.url.params["on_conflict"] == "provider,entity_type,provider_id"
    assert request.headers["prefer"] == (
        "resolution=merge-duplicates,return=representation"
    )
    assert request.read().decode("utf-8").count("sb_secret_modern") == 0
    http_client.close()


def test_provider_record_upsert_accepts_a_nol_provider():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=[{"id": "raw-1"}])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    repository.upsert_provider_record(
        provider="nol",
        entity_type="performance_detail",
        provider_id="26007299",
        payload={"data": {"goodsCode": "26007299"}},
        ingestion_run_id="run-1",
    )

    assert json.loads(requests[0].content)["provider"] == "nol"
    http_client.close()


def test_program_source_update_sets_a_fresh_timestamp():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    repository.update_performance_program_source(
        "performance-1",
        {
            "program_status": "image_only",
            "program_source_url": "https://tickets.interpark.com/goods/26007299",
            "program_image_urls": ["https://ticketimage.interpark.com/program.jpg"],
        },
    )

    request = requests[0]
    body = json.loads(request.content)
    assert request.method == "PATCH"
    assert request.url.path == "/rest/v1/performances"
    assert request.url.params["id"] == "eq.performance-1"
    assert request.headers["prefer"] == "return=minimal"
    assert body["program_status"] == "image_only"
    assert body["program_source_updated_at"].endswith("+00:00")
    http_client.close()


def test_program_item_replacement_upserts_before_deleting_stale_nol_rows():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    repository.replace_program_items(
        "performance-1",
        "nol",
        [
            {
                "display_title": "La mer",
                "composer_name": "Claude Debussy",
                "source_type": "verified",
                "confidence": 0.98,
                "position": 0,
                "source_url": "https://tickets.interpark.com/goods/26007299",
            },
            {
                "display_title": "Bolero",
                "composer_name": "Maurice Ravel",
                "source_type": "verified",
                "confidence": 0.98,
                "position": 1,
                "source_url": "https://tickets.interpark.com/goods/26007299",
            },
        ],
    )

    upsert, delete = requests
    rows = json.loads(upsert.content)
    assert upsert.method == "POST"
    assert upsert.url.path == "/rest/v1/program_items"
    assert upsert.url.params["on_conflict"] == (
        "performance_id,source_provider,position"
    )
    assert upsert.headers["prefer"] == ("resolution=merge-duplicates,return=minimal")
    assert rows[0]["performance_id"] == "performance-1"
    assert rows[0]["source_provider"] == "nol"
    assert delete.method == "DELETE"
    assert delete.url.params["performance_id"] == "eq.performance-1"
    assert delete.url.params["source_provider"] == "eq.nol"
    assert delete.url.params["position"] == "not.in.(0,1)"
    http_client.close()


def test_empty_program_replacement_deletes_only_the_requested_provider_rows():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    repository.replace_program_items("performance-1", "nol", [])

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert request.url.params["performance_id"] == "eq.performance-1"
    assert request.url.params["source_provider"] == "eq.nol"
    assert "position" not in request.url.params
    http_client.close()


@pytest.mark.parametrize("position", [None, -1, True, "0"])
def test_program_item_replacement_rejects_invalid_positions(position: object):
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: None))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    with pytest.raises(ValueError, match="position"):
        repository.replace_program_items(
            "performance-1",
            "nol",
            [{"display_title": "La mer", "position": position}],
        )

    http_client.close()


def test_program_item_replacement_rejects_duplicate_positions():
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: None))
    repository = SupabaseRepository(
        SupabaseSettings(
            url="https://project-ref.supabase.co",
            api_key="sb_secret_modern",
        ),
        http_client=http_client,
    )

    with pytest.raises(ValueError, match="unique"):
        repository.replace_program_items(
            "performance-1",
            "nol",
            [
                {"display_title": "La mer", "position": 0},
                {"display_title": "Bolero", "position": 0},
            ],
        )

    http_client.close()


def test_load_ocr_results_is_private_provider_scoped_and_paginated():
    requests = []
    def handler(request):
        requests.append(request)
        assert request.url.params["provider"] == "eq.paddleocr"
        assert request.url.params["entity_type"] == "eq.ocr_result"
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json=(
            [{"id": "r1", "payload": {"source_sha256": "hash"}}]
            if offset == 0 else []
        ))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings(url="https://project.supabase.co", api_key="test"),
            http_client=client,
        )
        assert repo.load_ocr_results(page_size=1) == [{"source_sha256": "hash"}]
        assert len(requests) == 2
