"""Private, content-addressed source storage using the R2 S3 API."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

MAX_SOURCE_BYTES = 32 * 1024 * 1024


class R2Error(RuntimeError):
    """Storage failure with no credentials or raw provider response attached."""


@dataclass(frozen=True)
class R2Settings:
    endpoint: str
    bucket: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    region: str = "auto"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> R2Settings:
        values = os.environ if environ is None else environ
        required = (
            "S3_ENDPOINT_URL",
            "S3_BUCKET",
            "S3_ACCESS_KEY_ID",
            "S3_SECRET_ACCESS_KEY",
        )
        fields = {key: (values.get(key) or "").strip() for key in required}
        for key, value in fields.items():
            if not value:
                raise ValueError(f"{key} is required")
        endpoint = fields["S3_ENDPOINT_URL"].rstrip("/")
        if not re.fullmatch(
            r"https://[a-f0-9]{32}(?:\.(?:eu|us|fedramp))?\.r2\.cloudflarestorage\.com",
            endpoint,
        ):
            raise ValueError(
                "S3_ENDPOINT_URL must be the R2 HTTPS endpoint without a bucket path"
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", fields["S3_BUCKET"]):
            raise ValueError("S3_BUCKET must be a valid R2 bucket name")
        region = values.get("S3_REGION", "auto") or "auto"
        if region != "auto":
            raise ValueError("S3_REGION must be auto for R2")
        return cls(
            endpoint,
            fields["S3_BUCKET"],
            fields["S3_ACCESS_KEY_ID"],
            fields["S3_SECRET_ACCESS_KEY"],
            region,
        )


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size_bytes: int
    content_type: str
    created: bool


class R2Store:
    def __init__(self, settings: R2Settings, *, client: Any = None):
        self.bucket = settings.bucket
        self._owns_client = client is None
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.endpoint,
            region_name=settings.region,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=30,
                retries={"mode": "standard", "total_max_attempts": 3},
                s3={"addressing_style": "path"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        if self._owns_client:
            self._client.close()

    def archive(self, content: bytes, content_type: str) -> StoredObject:
        return self._archive(content, content_type, "originals")

    def archive_ocr_result(self, result: Mapping[str, object]) -> StoredObject:
        content = json.dumps(
            result,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return self._archive(content, "application/json", "ocr")

    def _archive(self, content: bytes, content_type: str, prefix: str) -> StoredObject:
        if not content or len(content) > MAX_SOURCE_BYTES:
            raise ValueError("Source size must be between 1 byte and 32 MiB")
        digest = hashlib.sha256(content).hexdigest()
        key = f"{prefix}/sha256/{digest[:2]}/{digest}"
        params = {"Bucket": self.bucket, "Key": key}
        try:
            existing = self._client.head_object(**params)
        except ClientError as error:
            if str(error.response.get("Error", {}).get("Code")) not in {
                "404",
                "NoSuchKey",
                "NotFound",
            }:
                raise R2Error(_safe_error(error)) from None
        except BotoCoreError as error:
            raise R2Error(type(error).__name__) from None
        else:
            if (
                existing.get("ContentLength") != len(content)
                or existing.get("Metadata", {}).get("sha256") != digest
            ):
                raise R2Error(
                    "Stored source integrity mismatch; object was not overwritten"
                )
            return StoredObject(key, digest, len(content), content_type, False)
        self._call(
            "put_object",
            **params,
            Body=content,
            ContentType=content_type,
            Metadata={"sha256": digest},
        )
        return StoredObject(key, digest, len(content), content_type, True)

    def read(self, key: str) -> bytes:
        if not re.fullmatch(r"(?:originals|ocr)/sha256/[a-f0-9]{2}/[a-f0-9]{64}", key):
            raise ValueError("Expected a content-addressed source or OCR object key")
        response = self._call("get_object", Bucket=self.bucket, Key=key)
        body = response["Body"]
        try:
            data = body.read(MAX_SOURCE_BYTES + 1)
        finally:
            body.close()
        if (
            len(data) > MAX_SOURCE_BYTES
            or hashlib.sha256(data).hexdigest() != key.rsplit("/", 1)[1]
        ):
            raise R2Error("Source integrity verification failed")
        return data

    def _call(self, operation: str, **kwargs: Any) -> Any:
        try:
            return getattr(self._client, operation)(**kwargs)
        except ClientError as error:
            raise R2Error(_safe_error(error)) from None
        except BotoCoreError as error:
            raise R2Error(type(error).__name__) from None


def _safe_error(error: ClientError) -> str:
    code = str(error.response.get("Error", {}).get("Code", "unknown"))
    return "R2 request failed: " + re.sub(r"[^a-zA-Z0-9_-]", "", code)[:80]
