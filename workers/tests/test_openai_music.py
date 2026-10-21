import importlib
import importlib.util
import json

import httpx
import pytest
from classic_hubble_pipeline.music_extraction import prepare_request
from test_music_extraction import document, response


def module():
    name = "classic_hubble_pipeline.openai_music"
    assert importlib.util.find_spec(name), "GPT-6 Luna adapter is missing"
    return importlib.import_module(name)


def api_response(**overrides):
    return {
        "id": "resp_test",
        "model": "gpt-6-luna",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps(response())}],
            }
        ],
        "usage": {"input_tokens": 3000, "output_tokens": 1000},
        **overrides,
    }


def test_luna_sends_only_grounded_text_with_strict_schema_and_no_storage():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=api_response())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        adapter = module().OpenAIMusicClient("secret-test", http_client=client)
        bundle = prepare_request(document(), "b" * 64)
        result = adapter.extract(bundle)
        assert result.payload == response()
        assert result.cost_usd == pytest.approx(0.0008)
        assert adapter.maximum_cost(bundle) >= result.cost_usd
    request = requests[0]
    body = json.loads(request.content)
    assert str(request.url) == "https://api.openai.com/v1/responses"
    assert body["model"] == "gpt-6-luna"
    assert body["store"] is False
    assert body["reasoning"] == {"effort": "low"}
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
    reference_schema = body["text"]["format"]["schema"]["$defs"]["MusicReference"]
    assert "title" in reference_schema["properties"]
    assert set(reference_schema["required"]) == set(reference_schema["properties"])
    assert "tools" not in body
    assert json.loads(body["input"][0]["content"]) == bundle["input"]
    assert "source_object_key" not in request.content.decode()
    assert "secret-test" not in request.content.decode()


@pytest.mark.parametrize(
    "change",
    [
        {"status": "incomplete"},
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "refusal", "refusal": "private"}],
                }
            ]
        },
        {"output": []},
        {"usage": {"input_tokens": -1, "output_tokens": 1}},
        {"model": "different-model"},
    ],
)
def test_non_completed_or_invalid_responses_are_never_accepted(change):
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=api_response(**change))
            )
        ) as client,
        pytest.raises(module().ModelResponseError) as caught,
    ):
        module().OpenAIMusicClient("secret-test", http_client=client).extract(
            prepare_request(document(), "b" * 64)
        )
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_errors_are_redacted_and_not_retried(status):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(status, json={"error": "secret-test private OCR"})

    with (
        httpx.Client(transport=httpx.MockTransport(handle)) as client,
        pytest.raises(module().ModelResponseError) as caught,
    ):
        module().OpenAIMusicClient("secret-test", http_client=client).extract(
            prepare_request(document(), "b" * 64)
        )
    assert len(requests) == 1
    assert str(status) in str(caught.value)
    assert "secret-test" not in str(caught.value)


def test_missing_credentials_and_oversized_request_stop_before_network():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        module().OpenAIMusicClient("")
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("must not call"))
    ) as client:
        adapter = module().OpenAIMusicClient("secret-test", http_client=client)
        doc = document()
        doc["lines"] = [{"text": "a" * 150_000}]
        with pytest.raises(ValueError, match="limit"):
            adapter.extract(prepare_request(doc, "b" * 64))


@pytest.mark.parametrize(
    ("details", "cost"),
    [
        ({"cached_tokens": 1000, "cache_write_tokens": 1500}, 0.0007475),
        (
            {
                "cached_tokens": 1000,
                "cache_write_tokens": 1500,
                "cache_write_tokens_details": {
                    "ttl_30m_tokens": 500,
                    "ttl_12h_tokens": 1000,
                },
            },
            0.0008725,
        ),
    ],
)
def test_cache_reads_and_each_write_lifetime_are_billed_once(details, cost):
    data = api_response(
        usage={
            "input_tokens": 3000,
            "output_tokens": 1000,
            "input_tokens_details": details,
            "output_tokens_details": {"reasoning_tokens": 400},
        }
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        result = (
            module()
            .OpenAIMusicClient("secret-test", http_client=client)
            .extract(prepare_request(document(), "b" * 64))
        )
    assert result.cost_usd == pytest.approx(cost)


@pytest.mark.parametrize(
    "details",
    [
        {"cached_tokens": 3001},
        {"cache_write_tokens": -1},
        {"cache_write_tokens": True},
        {
            "cache_write_tokens": 100,
            "cache_write_tokens_details": {"ttl_30m_tokens": 101, "ttl_12h_tokens": 0},
        },
        {"cached_tokens": 2000, "cache_write_tokens": 2000},
    ],
)
def test_invalid_usage_details_cannot_understate_cost(details):
    data = api_response(
        usage={
            "input_tokens": 3000,
            "output_tokens": 1000,
            "input_tokens_details": details,
        }
    )
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
        ) as client,
        pytest.raises(module().ModelResponseError),
    ):
        module().OpenAIMusicClient("secret-test", http_client=client).extract(
            prepare_request(document(), "b" * 64)
        )


def test_budget_bound_includes_default_cache_write_surcharge():
    from classic_hubble_pipeline.music_extraction import json_bytes

    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("no calls"))
    ) as client:
        adapter = module().OpenAIMusicClient("secret-test", http_client=client)
        bundle = prepare_request(document(), "b" * 64)
        expected = (
            len(json_bytes(adapter.body(bundle))) + 2048
        ) * 0.125 / 1e6 + 8192 * 0.5 / 1e6
        assert adapter.maximum_cost(bundle) >= expected


def test_invalid_extraction_retains_billable_usage_on_error():
    data = api_response(
        output=[
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "not JSON"}],
            }
        ]
    )
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
        ) as client,
        pytest.raises(module().ModelResponseError) as error,
    ):
        module().OpenAIMusicClient("secret-test", http_client=client).extract(
            prepare_request(document(), "b" * 64)
        )
    assert error.value.cost_usd == pytest.approx(0.0008)
    assert error.value.response_id == "resp_test"
