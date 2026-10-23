import httpx
import pytest

from classic_hubble_pipeline.supabase import SupabaseRepository, SupabaseSettings


@pytest.mark.parametrize("table", ["performances", "provider_records"])
@pytest.mark.parametrize("pages", [
    [[]],
    [[{"id": "a"}]],
    [[{"id": "a"}, {"id": "b"}], [{"id": "c"}, {"id": "d"}], []],
])
def test_row_scan_uses_page_length_without_requesting_total_counts(table, pages):
    requests = []

    def handler(request):
        requests.append(request)
        assert "count=" not in request.headers.get("prefer", "")
        assert request.url.params["select"] == "id"
        assert request.url.params["provider"] == "eq.r2"
        assert request.url.params["order"] == "id.asc"
        assert request.url.params["limit"] == "2"
        return httpx.Response(200, json=pages[len(requests) - 1])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        repo = SupabaseRepository(
            SupabaseSettings("https://example.supabase.co", "sb_secret_test"),
            http_client=client,
        )
        actual = repo._read_pages(table, {"select": "id", "provider": "eq.r2"}, page_size=2)
    assert actual == [row for page in pages for row in page]
    assert [request.url.params["offset"] for request in requests] == [
        str(sum(len(page) for page in pages[:index])) for index in range(len(pages))
    ]
