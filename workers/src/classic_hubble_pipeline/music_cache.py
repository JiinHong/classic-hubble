"""Private, durable paid-request ledger. Uncertain attempts are never retried."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from .music_extraction import digest, json_bytes, parse_response
from .openai_music import InferenceResult, ModelResponseError, TokenUsage


class CachedRequestUnavailable(RuntimeError):
    """The request needs operational reconciliation, not another paid attempt."""


def _validated_result(value: dict, bundle: dict, model: str) -> InferenceResult:
    usage = value["usage"]
    validated_usage = TokenUsage.from_api({
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "input_tokens_details": {
            "cached_tokens": usage["cached_tokens"],
            "cache_write_tokens": usage["write_30m_tokens"] + usage["write_12h_tokens"],
            "cache_write_tokens_details": {
                "ttl_30m_tokens": usage["write_30m_tokens"],
                "ttl_12h_tokens": usage["write_12h_tokens"],
            },
        },
    })
    payload = parse_response(json_bytes(value["payload"]))
    if (
        value["model"] != model
        or not isinstance(value["response_id"], str)
        or not value["response_id"]
        or payload["document_sha256"] != bundle["input"]["document_sha256"]
        or value["input_tokens"] != validated_usage.input_tokens
        or value["output_tokens"] != validated_usage.output_tokens
    ):
        raise ValueError("Cached response identity mismatch")
    return InferenceResult(
        payload, validated_usage.input_tokens, validated_usage.output_tokens,
        value["response_id"], model, validated_usage,
    )


class MusicResponseCache:
    def __init__(self, repository, store):
        self.repository = repository
        self.store = store

    def extract(self, client, bundle: dict) -> InferenceResult:
        return self._run(client, bundle)

    def import_result(self, client, bundle: dict, result: InferenceResult) -> InferenceResult:
        """Import an operator-verified historical response without calling OpenAI."""
        return self._run(client, bundle, imported=result)

    def _read(self, row, key, bundle, model):
        if row.get("status") != "succeeded":
            raise CachedRequestUnavailable("Existing request is unfinished or failed")
        try:
            sha = row["result_sha256"]
            object_key = f"extractions/sha256/{sha[:2]}/{sha}"
            if row["bucket"] != self.store.bucket or row["result_object_key"] != object_key:
                raise ValueError
            raw = self.store.read(object_key)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError
            envelope = json.loads(raw)
            if (
                envelope["version"] != "music-response-v1"
                or envelope["request_key"] != key
                or digest(envelope["request"]) != key
            ):
                raise ValueError
            return _validated_result(envelope["result"], bundle, model)
        except Exception:
            raise CachedRequestUnavailable("Cached response cannot be verified") from None

    def _finish(self, key, owner, payload):
        try:
            saved = self.repository.finish_music_request(key, owner, payload)
        except Exception:
            saved = False
        if not saved:
            raise CachedRequestUnavailable("Request ledger update failed; do not retry inference")

    def _run(self, client, bundle, *, imported=None):
        body = client.body(bundle)
        key = digest(body)
        previous = self.repository.load_music_request(key)
        if previous is not None:
            return self._read(previous, key, bundle, body["model"])
        if imported is not None:
            imported = _validated_result(asdict(imported), bundle, body["model"])
        owner = str(uuid4())
        maximum = client.maximum_cost(bundle)
        claim = {
            "status": "claimed", "owner": owner, "request_key": key,
            "model": body["model"], "document_sha256": bundle["input"]["document_sha256"],
            "started_at": datetime.now(UTC).isoformat(), "maximum_cost_usd": maximum,
            "cost_usd": imported.cost_usd if imported else None,
            "unknown_charge_usd": 0 if imported else maximum,
            "origin": "historical_import" if imported else "live",
        }
        # A unique INSERT, not an upsert, wins the right to spend. A crash leaves
        # the claim for reconciliation; it must never expire into a paid retry.
        if not self.repository.claim_music_request(key, claim):
            raise CachedRequestUnavailable("Another execution owns this request")
        result = imported
        try:
            if result is None:
                result = client.extract(bundle)
            result = _validated_result(asdict(result), bundle, body["model"])
            stored = self.store.archive_extraction_result({
                "version": "music-response-v1", "request_key": key,
                "request": body, "result": asdict(result),
            })
        except Exception as error:
            usage = result.usage if result else getattr(error, "usage", None)
            failed = {
                **claim, "status": "failed", "finished_at": datetime.now(UTC).isoformat(),
                "error_stage": "api" if result is None else "persistence_or_validation",
                "usage": asdict(usage) if usage else None,
                "response_id": result.response_id if result else getattr(error, "response_id", None),
                "cost_usd": usage.cost_usd if usage else None,
                "unknown_charge_usd": 0 if usage else maximum,
                "error_type": "model_response" if isinstance(error, ModelResponseError) else "processing_failure",
            }
            self._finish(key, owner, failed)
            raise CachedRequestUnavailable("Request failed; paid retry is disabled") from None
        completed = {
            **claim, "status": "succeeded", "finished_at": datetime.now(UTC).isoformat(),
            "usage": asdict(result.usage), "cost_usd": result.cost_usd,
            "unknown_charge_usd": 0, "response_id": result.response_id,
            "bucket": self.store.bucket, "result_object_key": stored.key,
            "result_sha256": stored.sha256,
        }
        self._finish(key, owner, completed)
        return result
