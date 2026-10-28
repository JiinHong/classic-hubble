import copy
import hashlib
import importlib
import importlib.util
import json
from dataclasses import replace

import pytest

from classic_hubble_pipeline.music_extraction import digest, json_bytes
from classic_hubble_pipeline.r2 import StoredObject
from test_music_extraction import WORK, document, response


def module():
    name = "classic_hubble_pipeline.paddle_publication"
    assert importlib.util.find_spec(name), "Paddle partial publication is missing"
    return importlib.import_module(name)


class Store:
    bucket = "test"

    def __init__(self, doc):
        self.original = b"original image bytes"
        sha = hashlib.sha256(self.original).hexdigest()
        self.original_key = f"originals/sha256/{sha[:2]}/{sha}"
        doc.update(bucket=self.bucket, source_sha256=sha, source_object_key=self.original_key)
        self.sha = digest(doc)
        self.key = f"ocr/sha256/{self.sha[:2]}/{self.sha}"
        self.objects = {self.key: json_bytes(doc), self.original_key: self.original}

    def read(self, key):
        return self.objects[key]

    def archive_extraction_result(self, value):
        raw, sha = json_bytes(value), digest(value)
        key = f"extractions/sha256/{sha[:2]}/{sha}"
        self.objects[key] = raw
        return StoredObject(key, sha, len(raw), "application/json", True)


class Repo:
    def __init__(self, store):
        doc = json.loads(store.read(store.key))
        self.ocr = [{k: doc[k] for k in ("bucket", "source_sha256", "source_object_key", "pipeline_version", "status")}]
        self.ocr[0].update(result_sha256=store.sha, result_object_key=store.key, processed_at="2026-10-22T00:00:00Z")
        self.source = dict(bucket=store.bucket, sha256=doc["source_sha256"], object_key=store.original_key,
                           source_url="https://www.kopis.or.kr/upload/test.png", content_type="image/png", performance_ids=["p1"])
        self.target = dict(id="p1", title="Test", starts_on="2026-10-22", ends_on="2026-10-22", intro_image_urls=[self.source["source_url"]])
        self.reviews, self.writes = {}, []

    def load_ocr_results(self):
        return copy.deepcopy(self.ocr)

    def load_source_archives(self):
        return [copy.deepcopy(self.source)]

    def load_work_catalog(self):
        return [WORK]

    def load_vision_target(self, _):
        return copy.deepcopy(self.target)

    def load_vision_source(self, _):
        return copy.deepcopy(self.source)

    def upsert_provider_record(self, **kwargs):
        self.reviews[kwargs["provider_id"]] = copy.deepcopy(kwargs["payload"])

    def load_paddle_review(self, key):
        return copy.deepcopy(self.reviews.get(key))

    def publish_paddle_program(self, payload):
        self.writes.append(payload)
        return {"status": "published", "items": len(payload["p_items"])}


def setup(change=None):
    doc = document()
    doc["pipeline_version"] = "paddle-test-v1"
    doc["lines"].append({"text": "2026.10.22 THU 19:30"})
    for line in doc["lines"]:
        line["score"] = .99
    if change:
        change(doc)
    store = Store(doc)
    repo = Repo(store)
    data = response(store.sha)
    return repo, store, data


def save(repo, store, data):
    return module().save_review(repo, store, store.sha, data, notes="Reviewed programme text; not a pixel reading.")


def test_partial_dry_run_recomputes_grounded_matches_not_saved_ids():
    repo, store, data = setup()
    unknown = copy.deepcopy(data["items"][0])
    unknown["composer"] = None
    data["items"].append(unknown)
    key = save(repo, store, data)
    result = module().publish(repo, store, None, "p1", key)
    assert result["status"] == "ready" and result["items"] == 1
    assert result["program_status"] == "partially_confirmed"
    assert not repo.writes
    assert repo.reviews[key]["method"] == "reviewed_paddle_text"


def test_fwv_title_only_identity_is_not_public_without_composer_evidence():
    from test_music_extraction import quote
    title = "Prelude, Choral et Fugue"
    repo, store, data = setup(lambda d: d["lines"][2].update(text=title + ", FWV 21"))
    work = replace(WORK, titles=(title,), composers=("Cesar Franck",), catalogue="FWV 21", aliases=())
    repo.load_work_catalog = lambda: [work]
    data["items"][0].update(composer=None, title=quote(2, title), catalogue=quote(2, "FWV 21"), key=None)
    key = save(repo, store, data)
    result = module().publish(repo, store, None, "p1", key)
    assert result["status"] == "no_eligible_items"
    assert result["items"] == 0 and not repo.writes


def test_apply_retains_ocr_provenance_and_checks_live_bytes(monkeypatch):
    repo, store, data = setup()
    key = save(repo, store, data)
    monkeypatch.setattr(module(), "download_source", lambda *_: (store.original, "image/png"))
    assert module().publish(repo, store, None, "p1", key, apply=True)["status"] == "published"
    payload = repo.writes[0]
    assert payload["p_review"] == repo.reviews[key]
    assert payload["p_ocr"] == repo.ocr[0]
    assert payload["p_evaluation"]["matching"]["items"][0]["evidence"] == data["items"][0]
    assert payload["p_items"][0]["work_id"] == WORK.id
    assert "confidence" not in payload["p_items"][0]


@pytest.mark.parametrize("number,score,published", [(18, .99, True), (19, .99, False), (18, .5, False)])
def test_untyped_number_publication_preserves_literal_evidence_and_quality(number, score, published, monkeypatch):
    from test_music_extraction import quote

    title = "Piano Concerto No. 2 in C minor"
    code = f"작품 {number}"
    repo, store, data = setup(lambda d: d["lines"][2].update(text=title + ", " + code, score=score))
    data["items"][0]["catalogue"] = quote(2, code)
    key = save(repo, store, data)
    monkeypatch.setattr(module(), "download_source", lambda *_: (store.original, "image/png"))
    result = module().publish(repo, store, None, "p1", key, apply=True)
    assert (result["status"] == "published") is published
    assert len(repo.writes) == int(published)
    if published:
        payload = repo.writes[0]
        assert payload["p_items"][0]["work_id"] == WORK.id
        matched = payload["p_evaluation"]["matching"]["items"][0]
        assert matched["reason"] == "composer_and_alias"
        assert matched["fields"]["catalogue"] == code
        assert matched["evidence"] == data["items"][0]


@pytest.mark.parametrize("scope", ["movement", "excerpt", "arrangement", "unknown"])
def test_scopes_do_not_become_full_works(scope):
    repo, store, data = setup()
    data["items"][0]["scope"] = scope
    key = save(repo, store, data)
    assert module().publish(repo, store, None, "p1", key)["status"] == "no_eligible_items"


@pytest.mark.parametrize("context", ["biography", "unknown"])
def test_nonprogramme_is_private(context):
    repo, store, data = setup()
    data["items"][0]["context"] = context
    key = save(repo, store, data)
    assert module().publish(repo, store, None, "p1", key)["items"] == 0


@pytest.mark.parametrize("score", [.89, None])
def test_unreliable_cited_lines_stay_private(score):
    repo, store, data = setup(lambda d: d["lines"][2].update(score=score))
    key = save(repo, store, data)
    result = module().publish(repo, store, None, "p1", key)
    assert result["status"] == "no_eligible_items"
    assert result["withheld_reasons"] == {"low_ocr_evidence_score": 1}


@pytest.mark.parametrize("date_text", ["2026.10.23 FRI 19:30", "2026.10.22 FRI 19:30", "Biography debuted in 2026"])
def test_date_binding_blocks_wrong_missing_or_conflicting_weekday(date_text):
    repo, store, data = setup(lambda d: d["lines"][-1].update(text=date_text))
    key = save(repo, store, data)
    assert module().publish(repo, store, None, "p1", key)["status"] == "date_binding_required"


def test_low_score_date_does_not_bind():
    repo, store, data = setup(lambda d: d["lines"][-1].update(score=.5))
    key = save(repo, store, data)
    assert module().publish(repo, store, None, "p1", key)["status"] == "date_binding_required"


@pytest.mark.parametrize("score,expected", [(.99, "published"), (.89, "date_binding_required"), (None, "date_binding_required")])
@pytest.mark.parametrize("heading", [
    "2026.10.22.19:30", "2026.10.22THU7:30PM", "2026.10.22 7PM", "2026.10.22 7:30PM",
    "일시 | 2026.10.22.(목)19:30",
])
def test_date_clock_retains_quality_and_version_contract(score, expected, heading, monkeypatch):
    repo, store, data = setup(lambda d: d["lines"][-1].update(text=heading, score=score))
    key = save(repo, store, data)
    monkeypatch.setattr(module(), "download_source", lambda *_: (store.original, "image/png"))
    assert module().publish(repo, store, None, "p1", key, apply=True)["status"] == expected
    if repo.writes:
        assert repo.writes[0]["p_evaluation"]["date_binding_version"] == "concert-date-headings-v11"
        assert repo.writes[0]["p_evaluation"]["performance_date"] == "2026-10-22"
    else:
        assert expected == "date_binding_required"


def test_fabricated_quote_is_rejected_before_review_storage():
    repo, store, data = setup()
    data["items"][0]["catalogue"][0]["quote"] = "Op. 99"
    with pytest.raises(ValueError):
        save(repo, store, data)
    assert not repo.reviews


@pytest.mark.parametrize("problem", ["multiple_images", "range", "wrong_source", "live_changed", "ocr_superseded", "tampered_review"])
def test_stale_or_unsupported_sources_never_write(problem, monkeypatch):
    repo, store, data = setup()
    key = save(repo, store, data)
    if problem == "multiple_images":
        repo.target["intro_image_urls"].append("other")
    elif problem == "range":
        repo.target["ends_on"] = "2026-10-23"
    elif problem == "wrong_source":
        repo.source["performance_ids"] = []
    elif problem == "ocr_superseded":
        repo.ocr.append({**repo.ocr[0], "result_sha256": "e" * 64, "processed_at": "2026-10-23T00:00:00Z"})
    elif problem == "tampered_review":
        repo.reviews[key]["response"]["items"][0]["scope"] = "excerpt"
    monkeypatch.setattr(module(), "download_source", lambda *_: (b"changed", "image/png"))
    try:
        result = module().publish(repo, store, None, "p1", key, apply=True)
        assert result["status"] != "published"
    except ValueError:
        assert problem in {"ocr_superseded", "tampered_review"}
    assert not repo.writes
