import hashlib
import importlib
import importlib.util
import io
import json

import boto3
import pytest
from botocore.stub import Stubber


def module():
    assert importlib.util.find_spec("classic_hubble_pipeline.r2") is not None
    return importlib.import_module("classic_hubble_pipeline.r2")


def settings(**overrides):
    values = {
        "S3_ENDPOINT_URL": "https://" + "a" * 32 + ".r2.cloudflarestorage.com",
        "S3_BUCKET": "classic-hubble-sources",
        "S3_ACCESS_KEY_ID": "private-id",
        "S3_SECRET_ACCESS_KEY": "private-secret",
        **overrides,
    }
    return module().R2Settings.from_env(values)


def client():
    return boto3.client(
        "s3",
        endpoint_url="https://example.r2.cloudflarestorage.com",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="auto",
    )


def test_settings_keep_credentials_out_of_repr():
    config = settings()
    assert config.region == "auto"
    assert "private-id" not in repr(config)
    assert "private-secret" not in repr(config)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://" + "a" * 32 + ".r2.cloudflarestorage.com",
        "https://" + "a" * 32 + ".r2.cloudflarestorage.com/classic-hubble-sources",
        "https://example.com",
        "https://user:pass@" + "a" * 32 + ".r2.cloudflarestorage.com",
    ],
)
def test_rejects_unsafe_or_bucket_scoped_endpoints(endpoint):
    with pytest.raises(ValueError, match="S3_ENDPOINT_URL"):
        settings(S3_ENDPOINT_URL=endpoint)


@pytest.mark.parametrize(
    "name", ["S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"]
)
def test_missing_configuration_fails_before_network(name):
    with pytest.raises(ValueError, match=name):
        settings(**{name: ""})


def test_archive_stores_content_hash_and_reuses_identical_bytes():
    data = b"original image bytes"
    digest = hashlib.sha256(data).hexdigest()
    key = f"originals/sha256/{digest[:2]}/{digest}"
    s3 = client()
    with Stubber(s3) as stub:
        params = {"Bucket": "classic-hubble-sources", "Key": key}
        stub.add_client_error(
            "head_object", "404", http_status_code=404, expected_params=params
        )
        stub.add_response(
            "put_object",
            {},
            {
                **params,
                "Body": data,
                "ContentType": "image/jpeg",
                "Metadata": {"sha256": digest},
            },
        )
        stub.add_response(
            "head_object",
            {
                "ContentLength": len(data),
                "Metadata": {"sha256": digest},
            },
            params,
        )
        store = module().R2Store(settings(), client=s3)
        first = store.archive(data, "image/jpeg")
        second = store.archive(data, "image/jpeg")
        assert first.key == second.key == key
        assert first.sha256 == digest
        assert first.created is True
        assert second.created is False
        stub.assert_no_pending_responses()


def test_access_error_does_not_attempt_an_upload():
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_client_error("head_object", "AccessDenied", http_status_code=403)
        with pytest.raises(module().R2Error, match="AccessDenied"):
            module().R2Store(settings(), client=s3).archive(b"data", "image/png")
        stub.assert_no_pending_responses()


def test_existing_wrong_size_is_not_overwritten():
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_response("head_object", {"ContentLength": 999, "Metadata": {}})
        with pytest.raises(module().R2Error, match="integrity"):
            module().R2Store(settings(), client=s3).archive(b"data", "image/png")


def test_read_verifies_hash_and_closes_body():
    data = b"original bytes"
    digest = hashlib.sha256(data).hexdigest()
    key = f"originals/sha256/{digest[:2]}/{digest}"
    body = io.BytesIO(data)
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_response("get_object", {"Body": body})
        assert module().R2Store(settings(), client=s3).read(key) == data
    assert body.closed


def test_read_rejects_corrupted_bytes():
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_response("get_object", {"Body": io.BytesIO(b"changed")})
        with pytest.raises(module().R2Error, match="integrity"):
            module().R2Store(settings(), client=s3).read(
                "originals/sha256/aa/" + "a" * 64
            )


def test_ocr_json_is_content_addressed_separately_and_readable():
    result = {"lines": [], "status": "no_text"}
    data = json.dumps(
        result,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    digest = hashlib.sha256(data).hexdigest()
    key = f"ocr/sha256/{digest[:2]}/{digest}"
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_client_error("head_object", "404", http_status_code=404)
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "classic-hubble-sources",
                "Key": key,
                "Body": data,
                "ContentType": "application/json",
                "Metadata": {"sha256": digest},
            },
        )
        stub.add_response("get_object", {"Body": io.BytesIO(data)})
        store = module().R2Store(settings(), client=s3)
        saved = store.archive_ocr_result(result)
        assert saved.key == key
        assert json.loads(store.read(key)) == result
