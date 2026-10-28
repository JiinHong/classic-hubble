import copy
import hashlib
import json
from io import StringIO

import pytest

from classic_hubble_pipeline import paddle_publication as publication
from classic_hubble_pipeline.music_extraction import digest, json_bytes
from test_music_extraction import WORK, document, response, quote
from test_paddle_publication import Repo, Store


def bundle(scope="full_work", second_date=None, *, movements=False, movement_score=.99, repeated_program=False):
    documents, selections, sources, ocr = [], [], [], []
    store = Store(document())
    repo = Repo(store)
    for index in range(2):
        raw = f"original {index}".encode()
        sha = hashlib.sha256(raw).hexdigest()
        key = f"originals/sha256/{sha[:2]}/{sha}"
        doc = document()
        doc.update(bucket=store.bucket, source_sha256=sha, source_object_key=key, pipeline_version="paddle-test-v1")
        if index == 0 and not repeated_program:
            doc["lines"] = [{"text": "2026.10.22 THU 19:30"}]
        elif index == 0:
            doc["lines"].append({"text": "2026.10.22 THU 19:30"})
        elif second_date:
            doc["lines"].append({"text": second_date})
        for line in doc["lines"]:
            line["score"] = .99
        if index == 1 and movements:
            doc["lines"][3]["score"] = movement_score
        doc_sha = digest(doc)
        doc_key = f"ocr/sha256/{doc_sha[:2]}/{doc_sha}"
        store.objects[key], store.objects[doc_key] = raw, json_bytes(doc)
        sources.append(dict(repo.source, sha256=sha, object_key=key, source_url=f"https://www.kopis.or.kr/upload/{index}.png"))
        ocr.append({**{k: doc[k] for k in ("bucket", "source_sha256", "source_object_key", "pipeline_version", "status")},
                    "result_sha256": doc_sha, "result_object_key": doc_key, "processed_at": "2026-10-22T00:00:00Z"})
        data = response(doc_sha)
        if index == 0 and not repeated_program:
            data.update(status="no_program_identified", items=[])
        else:
            data["items"][0]["scope"] = scope
            if movements:
                data["items"][0]["movements"] = [quote(3, "I. Moderato")]
        documents.append(doc)
        selections.append(data)
    repo.ocr = ocr
    repo.target["intro_image_urls"] = [s["source_url"] for s in sources]
    repo.load_vision_source = lambda url: copy.deepcopy(next((s for s in sources if s["source_url"] == url), None))
    repo.load_source_archives = lambda: copy.deepcopy(sources)
    repo.load_ocr_results_for_sources = lambda hashes, bucket: copy.deepcopy([o for o in repo.ocr if o["source_sha256"] in hashes and o["bucket"] == bucket])
    repo.publish_paddle_program_bundle = repo.publish_paddle_program
    reviews = [publication.save_review(repo, store, d["document_sha256"], d, notes="Reviewed text context and scope") for d in selections]
    return repo, store, reviews, sources


def test_cover_date_binds_program_on_another_current_image(monkeypatch):
    repo, store, reviews, sources = bundle()
    monkeypatch.setattr(publication, "download_source", lambda _, url: (store.read(next(s["object_key"] for s in sources if s["source_url"] == url)), "image/png"))
    result = publication.publish_bundle(repo, store, None, "p1", reviews, apply=True)
    assert result["status"] == "published" and result["items"] == 1
    payload = repo.writes[0]
    assert len(payload["p_documents"]) == 2
    assert payload["p_items"][0]["work_id"] == WORK.id
    assert payload["p_items"][0]["performed_scope"] == "full_work"
    assert payload["p_items"][0]["source_url"] == sources[1]["source_url"]
    assert payload["p_documents"][0]["date_binding"] == "target"
    assert payload["p_documents"][1]["date_binding"] == "absent"


@pytest.mark.parametrize("scope", ["movement", "excerpt", "arrangement", "unknown"])
def test_scoped_known_identity_is_linked_without_claiming_full_work(scope, monkeypatch):
    repo, store, reviews, sources = bundle(scope)
    monkeypatch.setattr(publication, "download_source", lambda _, url: (store.read(next(s["object_key"] for s in sources if s["source_url"] == url)), "image/png"))
    assert publication.publish_bundle(repo, store, None, "p1", reviews, apply=True)["items"] == 1
    assert repo.writes[0]["p_items"][0]["performed_scope"] == scope


@pytest.mark.parametrize("heading", ["2026.10.23 FRI 19:30", "2026.10.22 FRI 19:30", "2026.10.22 ???"])
def test_conflicting_or_invalid_date_on_any_image_blocks_the_bundle(heading):
    repo, store, reviews, _ = bundle(second_date=heading)
    assert publication.publish_bundle(repo, store, None, "p1", reviews)["status"] == "date_binding_required"
    assert not repo.writes


def test_missing_review_does_not_silently_drop_an_image():
    repo, store, reviews, _ = bundle()
    assert publication.publish_bundle(repo, store, None, "p1", reviews[:1])["status"] == "incomplete_source_bundle"


def test_changed_cover_is_checked_even_when_only_program_image_has_items(monkeypatch):
    repo, store, reviews, _ = bundle()
    monkeypatch.setattr(publication, "download_source", lambda *_: (b"changed", "image/png"))
    assert publication.publish_bundle(repo, store, None, "p1", reviews, apply=True)["status"] == "source_changed"
    assert not repo.writes


def test_bundle_loads_catalog_once_and_never_scans_global_ocr_or_archive_tables():
    repo, store, reviews, _ = bundle()
    def forbidden():
        raise AssertionError("Global evidence scan")
    repo.load_ocr_results = repo.load_source_archives = forbidden
    calls = []
    repo.load_work_catalog = lambda: calls.append(1) or [WORK]
    assert publication.publish_bundle(repo, store, None, "p1", reviews)["status"] == "ready"
    assert calls == [1]


def test_uncertain_supporting_image_is_not_treated_as_reviewed_absence():
    repo, store, reviews, _ = bundle()
    data = dict(repo.reviews[reviews[0]]["response"], status="uncertain")
    reviews[0] = publication.save_review(repo, store, data["document_sha256"], data, notes="Cannot determine context")
    assert publication.publish_bundle(repo, store, None, "p1", reviews)["status"] == "incomplete_source_bundle"


def test_composerless_identity_remains_private():
    repo, store, reviews, _ = bundle("excerpt")
    data = copy.deepcopy(repo.reviews[reviews[1]]["response"])
    data["items"][0]["composer"] = None
    reviews[1] = publication.save_review(repo, store, data["document_sha256"], data, notes="Composer absent")
    assert publication.publish_bundle(repo, store, None, "p1", reviews)["items"] == 0


def test_wrong_current_source_is_not_published():
    repo, store, reviews, _ = bundle()
    changed = dict(repo.source, sha256="a" * 64)
    repo.load_vision_source = lambda url: changed
    assert publication.publish_bundle(repo, store, None, "p1", reviews)["items"] == 0


def test_low_quality_movement_evidence_remains_private():
    repo, store, reviews, _ = bundle("movement", movements=True, movement_score=.5)
    result = publication.publish_bundle(repo, store, None, "p1", reviews)
    assert result["items"] == 0
    assert result["withheld_reasons"] == {"low_ocr_evidence_score": 1}


def test_literal_movement_text_survives_publication(monkeypatch):
    repo, store, reviews, sources = bundle("movement", movements=True)
    monkeypatch.setattr(publication, "download_source", lambda _, url: (store.read(next(s["object_key"] for s in sources if s["source_url"] == url)), "image/png"))
    publication.publish_bundle(repo, store, None, "p1", reviews, apply=True)
    assert repo.writes[0]["p_items"][0]["scope_details"] == ["I. Moderato"]


def test_repeated_work_across_images_has_one_public_item():
    repo, store, reviews, _ = bundle(repeated_program=True)
    result = publication.publish_bundle(repo, store, None, "p1", reviews)
    assert result["items"] == 1
    assert result["withheld_reasons"] == {"duplicate_evidence": 1}


def test_competing_reviews_for_same_source_require_explicit_selection():
    repo, store, reviews, _ = bundle()
    data = repo.reviews[reviews[1]]["response"]
    other = publication.save_review(repo, store, data["document_sha256"], data, notes="Alternative review")
    result = publication.publish_bundle(repo, store, None, "p1", reviews + [other])
    assert result["status"] == "ambiguous_source_review"
    assert not repo.writes


@pytest.mark.parametrize("apply", [False, True])
def test_cli_uses_saved_reviews_and_requires_explicit_apply(apply, monkeypatch):
    repo, store, reviews, sources = bundle()
    downloads = []
    def download(_, url):
        downloads.append(url)
        return store.read(next(s["object_key"] for s in sources if s["source_url"] == url)), "image/png"
    monkeypatch.setattr(publication, "download_source", download)
    args = ["--performance-id", "p1"]
    for review in reviews:
        args += ["--review-id", review]
    if apply:
        args += ["--apply"]
    output = StringIO()
    assert publication.main(args, repository=repo, store=store, stdout=output) == 0
    result = json.loads(output.getvalue())
    assert result["status"] == ("published" if apply else "ready")
    assert len(repo.writes) == int(apply)
    assert len(downloads) == (2 if apply else 0)


def test_cli_failure_does_not_log_source_text_or_credentials(monkeypatch):
    repo, store, reviews, _ = bundle()
    def fail(*args, **kwargs):
        raise RuntimeError("secret credentials")
    monkeypatch.setattr(publication, "publish_bundle", fail)
    errors = StringIO()
    assert publication.main(["--performance-id", "p1", "--review-id", reviews[0]], repository=repo, store=store, stderr=errors) == 1
    assert errors.getvalue() == "Paddle publication failed: RuntimeError\n"
