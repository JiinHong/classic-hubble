import copy
import importlib
import importlib.util
import json

import pytest
from classic_hubble_pipeline.work_matching import CanonicalWork


def module():
    name = "classic_hubble_pipeline.music_extraction"
    assert importlib.util.find_spec(name) is not None, "Grounded extraction is missing"
    return importlib.import_module(name)


WORK = CanonicalWork(
    "rach-2",
    "rach-2",
    ("Piano Concerto No. 2 in C minor",),
    ("Sergei Rachmaninoff",),
    "Op. 18",
    ("Rach 2",),
)


def document():
    return {
        "status": "text_extracted",
        "pipeline_version": "ocr-test-v1",
        "source_sha256": "a" * 64,
        "lines": [
            {"text": "PROGRAM", "page_index": 0},
            {"text": "Sergei Rachmaninoff", "page_index": 0},
            {"text": "Piano Concerto No. 2 in C minor, Op. 18", "page_index": 0},
            {"text": "I. Moderato", "page_index": 1},
            {"text": "Biography: performed Rach 2 in 2010", "page_index": 1},
        ],
    }


def quote(line, text):
    return [{"line_id": f"L{line:06}", "quote": text}]


def response(sha="b" * 64):
    return {
        "document_sha256": sha,
        "status": "items_extracted",
        "items": [
            {
                "context": "program",
                "scope": "full_work",
                "composer": quote(1, "Sergei Rachmaninoff"),
                "title": quote(2, "Piano Concerto No. 2 in C minor"),
                "catalogue": quote(2, "Op. 18"),
                "key": quote(2, "C minor"),
                "movements": [],
            }
        ],
    }


def test_request_has_schema_and_text_only_with_stable_page_aware_line_ids():
    request = module().prepare_request(document(), "b" * 64)
    assert request["input"]["lines"][3] == {
        "line_id": "L000003",
        "page_index": 1,
        "text": "I. Moderato",
    }
    assert request["response_schema"]["additionalProperties"] is False
    assert "untrusted" in request["instructions"]
    assert "source_sha256" not in request["input"]


def test_grounded_program_is_only_a_private_suggestion():
    report = module().validate_response(response(), document(), "b" * 64, [WORK])
    item = report["items"][0]
    assert item["suggested_work_id"] == "rach-2"
    assert item["reason"] == "composer_and_catalogue"
    assert item["fields"]["composer"] == "Sergei Rachmaninoff"
    assert item["evidence"]["composer"] == quote(1, "Sergei Rachmaninoff")
    assert report["review_status"] == "unverified"
    assert report["publishable"] is False


@pytest.mark.parametrize("field", ["composer", "title", "catalogue", "key"])
def test_invented_field_is_rejected(field):
    data = response()
    data["items"][0][field] = quote(2, "invented value")
    with pytest.raises(ValueError, match="evidence"):
        module().validate_response(data, document(), "b" * 64, [WORK])


@pytest.mark.parametrize("mutation", ["line", "id", "extra", "type", "empty", "status"])
def test_invalid_response_is_rejected_without_echoing_untrusted_text(mutation):
    data = response()
    if mutation == "line":
        data["items"][0]["title"][0]["line_id"] = "L999999"
    elif mutation == "id":
        data["document_sha256"] = "c" * 64
    elif mutation == "extra":
        data["items"][0]["work_id"] = "private injected value"
    elif mutation == "type":
        data["items"][0]["title"][0]["quote"] = 123
    elif mutation == "empty":
        data["items"][0]["title"][0]["quote"] = " "
    else:
        data["status"] = "no_program_identified"
    with pytest.raises(ValueError) as error:
        module().validate_response(data, document(), "b" * 64, [WORK])
    assert "private injected value" not in str(error.value)


@pytest.mark.parametrize("context", ["biography", "unknown"])
def test_non_program_text_never_suggests_a_performance(context):
    data = response()
    data["items"][0]["context"] = context
    item = module().validate_response(data, document(), "b" * 64, [WORK])["items"][0]
    assert item["suggested_work_id"] is None
    assert item["candidate_ids"] == []
    assert item["reason"] == "not_confirmed_program"


@pytest.mark.parametrize("scope", ["movement", "excerpt", "arrangement", "unknown"])
def test_partial_or_uncertain_work_is_not_suggested_as_a_full_work(scope):
    data = response()
    data["items"][0]["scope"] = scope
    data["items"][0]["movements"] = [quote(3, "I. Moderato")]
    item = module().validate_response(data, document(), "b" * 64, [WORK])["items"][0]
    assert item["suggested_work_id"] is None
    assert item["reason"] == "scope_requires_review"


def test_unknown_work_stays_unmatched_and_catalogue_changes_invalidate_fingerprint():
    empty = module().validate_response(response(), document(), "b" * 64, [])
    known = module().validate_response(response(), document(), "b" * 64, [WORK])
    assert empty["items"][0]["reason"] == "no_candidate"
    assert empty["catalogue_sha256"] != known["catalogue_sha256"]


def test_explicit_conflicting_key_abstains():
    doc = document()
    doc["lines"].append({"text": "D major"})
    data = response()
    data["items"][0]["key"] = quote(5, "D major")
    item = module().validate_response(data, doc, "b" * 64, [WORK])["items"][0]
    assert item["suggested_work_id"] is None


@pytest.mark.parametrize("title", ["Piano Concerto No. 2 in C minor", "Rach 2"])
def test_separate_key_does_not_break_exact_title_or_alias_matching(title):
    doc = document()
    doc["lines"].append({"text": title})
    data = response()
    data["items"][0]["catalogue"] = None
    data["items"][0]["title"] = quote(5, title)
    item = module().validate_response(data, doc, "b" * 64, [WORK])["items"][0]
    assert item["suggested_work_id"] == "rach-2"
    assert item["reason"] == "composer_and_alias"


def test_empty_extraction_does_not_claim_program_is_unpublished():
    data = {"document_sha256": "b" * 64, "status": "no_program_identified", "items": []}
    result = module().validate_response(data, document(), "b" * 64, [WORK])
    assert result["status"] == "no_program_identified"
    assert result["review_status"] == "unverified"


def test_repeated_item_and_oversized_document_are_rejected_not_truncated():
    data = response()
    data["items"].append(copy.deepcopy(data["items"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        module().validate_response(data, document(), "b" * 64, [WORK])
    doc = document()
    doc["lines"] = [{"text": "x" * 200_001}]
    with pytest.raises(ValueError, match="limit"):
        module().prepare_request(doc, "b" * 64)


def test_response_json_rejects_duplicate_keys_and_nonfinite_values():
    for raw in [b'{"status":"uncertain","status":"items_extracted"}', b'{"score":NaN}']:
        with pytest.raises(ValueError):
            module().parse_response(raw)


def test_valid_json_response_is_parsed_without_coercion():
    raw = json.dumps(response()).encode()
    parsed = module().parse_response(raw)
    assert parsed == response()


def test_catalogue_quote_cannot_cut_off_a_digit_to_match_a_different_work():
    doc = document()
    doc["lines"][2]["text"] = "Piano Concerto No. 2 in C minor, Op. 180"
    with pytest.raises(ValueError, match="evidence"):
        module().validate_response(response(), doc, "b" * 64, [WORK])
