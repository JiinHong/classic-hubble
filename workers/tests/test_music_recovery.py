import copy

import pytest
from classic_hubble_pipeline.music_extraction import validate_response
from test_music_extraction import WORK, document, quote, response


def evaluate(data, doc=None):
    return validate_response(data, doc or document(), "b" * 64, [WORK], automatic=True)


def test_korean_attached_particles_are_valid_exact_evidence():
    data, doc = response(), document()
    doc["lines"].append({"text": "쇼팽의작품고향의 봄참좋다"})
    data["items"][0]["composer"] = quote(5, "쇼팽")
    data["items"][0]["title"] = quote(5, "고향의 봄")
    result = evaluate(data, doc)
    assert len(result["items"]) == 1
    assert result["rejected_items"] == []


@pytest.mark.parametrize("bad_field", ["title", "catalogue", "key", "movements"])
def test_one_bad_item_does_not_discard_other_grounded_items(bad_field):
    data = response()
    bad = copy.deepcopy(data["items"][0])
    bad[bad_field] = (
        [quote(2, "invented")] if bad_field == "movements" else quote(2, "invented")
    )
    data["items"].append(bad)
    result = evaluate(data)
    assert len(result["items"]) == 1
    assert result["items"][0]["suggested_work_id"] == WORK.id
    assert result["validation_status"] == "partial"
    assert result["rejected_items"][0]["index"] == 1
    assert result["rejected_items"][0]["reason"] == "invalid_source_evidence"
    assert result["rejected_items"][0]["field"] == bad_field
    assert result["complete"] is False


def test_schema_error_is_isolated_and_not_coerced():
    data = response()
    bad = copy.deepcopy(data["items"][0])
    bad["title"] = quote(2, "")
    data["items"].append(bad)
    result = evaluate(data)
    assert len(result["items"]) == 1
    assert result["rejected_items"][0]["reason"] == "invalid_item_schema"


def test_all_rejected_items_are_not_reported_as_successful_or_unpublished():
    data = response()
    data["items"][0]["title"] = quote(2, "invented")
    result = evaluate(data)
    assert result["validation_status"] == "failed"
    assert result["status"] == "items_extracted"
    assert result["publishable"] is False


def test_wrong_document_hash_still_rejects_whole_response():
    with pytest.raises(ValueError, match="another"):
        evaluate(response("c" * 64))


def test_uncertain_document_retains_valid_candidates_but_never_publishes():
    data = response()
    data["status"] = "uncertain"
    result = evaluate(data)
    assert result["items"][0]["candidate_ids"] == [WORK.id]
    assert result["items"][0]["suggested_work_id"] is None
    assert result["publishable"] is False
    assert result["warnings"] == ["status_items_disagree"]
    assert result["validation_status"] == "partial"


def test_number_truncation_remains_invalid_in_automatic_mode():
    data, doc = response(), document()
    doc["lines"][2]["text"] += "0"
    result = evaluate(data, doc)
    assert result["validation_status"] == "failed"
    assert result["publishable"] is False


def test_duplicate_references_are_deduplicated_with_warning():
    data = response()
    data["items"].append(copy.deepcopy(data["items"][0]))
    result = evaluate(data)
    assert len(result["items"]) == 1
    assert result["warnings"] == ["duplicate_reference:1"]


def test_partial_work_has_separate_parent_link_and_no_full_work_claim():
    data = response()
    data["items"][0]["scope"] = "movement"
    data["items"][0]["movements"] = [quote(3, "I. Moderato")]
    item = evaluate(data)["items"][0]
    assert item["scoped_work_id"] == WORK.id
    assert item["suggested_work_id"] is None
    assert item["scope"] == "movement"


def test_model_full_work_label_cannot_override_explicit_nonfirst_movements():
    data, doc = response(), document()
    doc["lines"][3]["text"] = "II. Adagio"
    data["items"][0]["movements"] = [quote(3, "II. Adagio")]
    item = evaluate(data, doc)["items"][0]
    assert item["model_scope"] == "full_work"
    assert item["scope"] == "movement"
    assert item["scoped_work_id"] == WORK.id
    assert item["suggested_work_id"] is None


def test_biography_has_no_parent_performance_link():
    data = response()
    data["items"][0]["context"] = "biography"
    data["items"][0]["scope"] = "movement"
    assert evaluate(data)["items"][0]["scoped_work_id"] is None


def test_multi_date_series_poster_requires_performance_date_binding():
    data, doc = response(), document()
    doc["lines"].extend(
        {"text": text} for text in ["전곡 시리즈", "2.26(목)", "3.26(목)", "4.23(목)"]
    )
    result = evaluate(data, doc)
    assert result["publishable"] is False
    assert result["items"][0]["suggested_work_id"] is None
    assert result["items"][0]["candidate_ids"] == [WORK.id]
    assert result["items"][0]["reason"] == "performance_date_binding_required"


def test_inline_movement_cannot_be_published_as_full_work_when_model_omits_movements():
    data, doc = response(), document()
    doc["lines"][2]["text"] += ": II. Adagio"
    data["items"][0]["title"] = quote(2, doc["lines"][2]["text"])
    item = evaluate(data, doc)["items"][0]
    assert item["suggested_work_id"] is None
    assert item["scope"] == "movement"


def test_key_quote_can_follow_ocr_joined_in_prefix_without_weakening_numbers():
    data, doc = response(), document()
    doc["lines"].append({"text": "Concerto inc minor"})
    data["items"][0]["key"] = quote(5, "c minor")
    result = evaluate(data, doc)
    assert result["validation_status"] == "complete"
    assert result["items"][0]["suggested_work_id"] == WORK.id


def test_repeated_title_quotes_are_kept_as_evidence_but_not_concatenated_for_search():
    data, doc = response(), document()
    doc["lines"].append({"text": "Rach 2"})
    doc["lines"].append({"text": "Rach 2"})
    data["items"][0]["title"] = quote(5, "Rach 2") + quote(6, "Rach 2")
    data["items"][0]["catalogue"] = None
    result = evaluate(data, doc)
    assert result["items"][0]["fields"]["title"] == "Rach 2"
    assert len(result["items"][0]["evidence"]["title"]) == 2
    assert result["items"][0]["suggested_work_id"] == WORK.id
