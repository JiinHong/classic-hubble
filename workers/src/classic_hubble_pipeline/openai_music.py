"""Bounded, text-only GPT-6 Luna extraction through the Responses API."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .music_extraction import digest, json_bytes, parse_response

MODEL = "gpt-6-luna"
MAX_OUTPUT_TOKENS = 8192
MAX_REQUEST_BYTES = 100_000
INPUT_USD_PER_TOKEN = 0.10 / 1_000_000
OUTPUT_USD_PER_TOKEN = 0.50 / 1_000_000


class ModelResponseError(RuntimeError):
    """Safe to log: contains no request, response body, or credential."""

    def __init__(self, message, *, usage=None, response_id=None):
        super().__init__(message)
        self.usage = usage
        self.response_id = response_id
        self.cost_usd = usage.cost_usd if usage is not None else None


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    write_30m_tokens: int = 0
    write_12h_tokens: int = 0

    @classmethod
    def from_api(cls, value: dict):
        details = value.get("input_tokens_details") or {}
        writes = details.get("cache_write_tokens", 0)
        lifetimes = details.get("cache_write_tokens_details")
        short = writes if lifetimes is None else lifetimes["ttl_30m_tokens"]
        long = 0 if lifetimes is None else lifetimes["ttl_12h_tokens"]
        counts = [
            value["input_tokens"],
            value["output_tokens"],
            details.get("cached_tokens", 0),
            short,
            long,
            writes,
        ]
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError("Invalid usage counts")
        if short + long != writes or counts[2] + writes > counts[0]:
            raise ValueError("Inconsistent cache usage")
        return cls(*counts[:5])

    @property
    def cost_usd(self) -> float:
        ordinary = (
            self.input_tokens
            - self.cached_tokens
            - self.write_30m_tokens
            - self.write_12h_tokens
        )
        return (
            ordinary
            + self.cached_tokens * 0.1
            + self.write_30m_tokens * 1.25
            + self.write_12h_tokens * 2.5
        ) * INPUT_USD_PER_TOKEN + self.output_tokens * OUTPUT_USD_PER_TOKEN


@dataclass(frozen=True)
class InferenceResult:
    payload: dict
    input_tokens: int
    output_tokens: int
    response_id: str
    model: str = MODEL
    usage: TokenUsage | None = None

    @property
    def cost_usd(self) -> float:
        return (
            self.usage or TokenUsage(self.input_tokens, self.output_tokens)
        ).cost_usd


def _wire_schema(value):
    if isinstance(value, list):
        return [_wire_schema(item) for item in value]
    if isinstance(value, dict):
        # Local Pydantic validation retains these constraints after generation.
        return {
            key: (
                {name: _wire_schema(schema) for name, schema in item.items()}
                if key in {"properties", "$defs"}
                else _wire_schema(item)
            )
            for key, item in value.items()
            if key not in {"title", "minLength", "maxLength"}
        }
    return value


class OpenAIMusicClient:
    def __init__(self, api_key: str, *, http_client: httpx.Client | None = None):
        if not api_key or not api_key.strip():
            raise ValueError("OPENAI_API_KEY is required")
        self._key = api_key.strip()
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=120, follow_redirects=False)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self._owns_client:
            self._client.close()

    def body(self, bundle: dict) -> dict:
        body = {
            "model": MODEL,
            "store": False,
            "reasoning": {"effort": "low"},
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "instructions": bundle["instructions"],
            "input": [
                {"role": "user", "content": json_bytes(bundle["input"]).decode()}
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "concert_program",
                    "strict": True,
                    "schema": _wire_schema(bundle["response_schema"]),
                }
            },
        }
        if len(json_bytes(body)) > MAX_REQUEST_BYTES:
            raise ValueError("LLM request byte limit exceeded")
        return body

    def cache_key(self, bundle: dict) -> str:
        return digest(self.body(bundle))

    def maximum_cost(self, bundle: dict) -> float:
        # UTF-8 bytes are a deliberately conservative token bound, with framing
        # overhead. Unknown-charge failures consume this allowance, not zero.
        return (
            len(json_bytes(self.body(bundle))) + 2048
        ) * INPUT_USD_PER_TOKEN * 1.25 + MAX_OUTPUT_TOKENS * OUTPUT_USD_PER_TOKEN

    def extract(self, bundle: dict) -> InferenceResult:
        body = self.body(bundle)
        try:
            response = self._client.post(
                "https://api.openai.com/v1/responses",
                json=body,
                headers={"Authorization": f"Bearer {self._key}"},
            )
        except httpx.TransportError:
            raise ModelResponseError("OpenAI transport failure") from None
        if response.status_code != 200:
            raise ModelResponseError(f"OpenAI HTTP {response.status_code}")
        usage = None
        response_id = None
        try:
            data = response.json()
            usage = TokenUsage.from_api(data["usage"])
            if not isinstance(data["id"], str) or not data["id"]:
                raise ValueError
            response_id = data["id"]
            if data["status"] != "completed" or data["model"] != MODEL:
                raise ValueError
            texts = []
            for item in data["output"]:
                if item["type"] == "reasoning":
                    continue
                if item["type"] != "message" or item.get("role") != "assistant":
                    raise ValueError
                for part in item["content"]:
                    if part["type"] != "output_text":
                        raise ValueError
                    texts.append(part["text"])
            if len(texts) != 1:
                raise ValueError
            return InferenceResult(
                parse_response(texts[0].encode()),
                usage.input_tokens,
                usage.output_tokens,
                response_id,
                usage=usage,
            )
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ModelResponseError(
                "OpenAI returned no valid completed extraction",
                usage=usage,
                response_id=response_id,
            ) from None
