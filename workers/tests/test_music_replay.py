import importlib
import importlib.util
import json
from dataclasses import asdict

import pytest
from test_music_extraction import WORK, document, response
from test_music_v2_regressions import LISTED_WORKS, SEASONS, SPRING, SUMMER


def module():
    name = "classic_hubble_pipeline.music_replay"
    assert importlib.util.find_spec(name), "Offline replay is missing"
    return importlib.import_module(name)


def test_replay_uses_cached_files_only_and_keeps_originals(tmp_path, monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx.Client, "send", lambda *a, **kw: pytest.fail("network forbidden")
    )
    root = tmp_path / "input"
    source = root / ("b" * 64)
    source.mkdir(parents=True)
    (root / "catalogue.json").write_text(json.dumps([asdict(WORK)]))
    (source / "ocr.json").write_text(json.dumps(document()))
    (source / "extraction.json").write_text(json.dumps(response()))
    (source / "result.json").write_text(json.dumps({"validation_error": "old error"}))
    original = (source / "extraction.json").read_bytes()
    output = tmp_path / "results"
    report = module().replay(root, output)
    assert report["documents"] == 1
    assert report["full_work_references"] == 1
    assert report["additional_api_calls"] == 0
    assert report["additional_cost_usd"] == 0
    assert report["public_database_updates"] is False
    assert (source / "extraction.json").read_bytes() == original
    assert (output / "summary.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        module().replay(root, output)


@pytest.mark.parametrize(
    "bad_response",
    ["{broken", "[]", '{"items":null}', '{"items":5}', '{"items":[]}'],
)
def test_replay_records_invalid_documents_and_continues(tmp_path, bad_response):
    root = tmp_path / "input"
    for sha, raw in (("a" * 64, bad_response), ("b" * 64, json.dumps(response()))):
        source = root / sha
        source.mkdir(parents=True)
        (source / "ocr.json").write_text(json.dumps(document()))
        (source / "extraction.json").write_text(raw)
    (root / "catalogue.json").write_text(json.dumps([asdict(WORK)]))

    report = module().replay(root, tmp_path / "results")

    assert report["documents"] == 2
    assert report["full_work_references"] == 1
    assert len(report["document_failures"]) == 1
    assert report["document_failures"][0]["document_sha256"] == "a" * 64
    assert "broken" not in report["document_failures"][0]["error"]


def test_replay_counts_derived_identities_separately_from_model_items(tmp_path):
    root = tmp_path / "input"
    source = root / ("b" * 64)
    source.mkdir(parents=True)
    texts = ["Vivaldi", "The Four Seasons", *LISTED_WORKS]
    q = lambda n: [{"line_id": f"L{n:06}", "quote": texts[n]}]
    data = response()
    data["items"][0].update(
        composer=q(0),
        title=q(1),
        catalogue=None,
        key=None,
        movements=[q(2), q(3)],
    )
    (source / "ocr.json").write_text(
        json.dumps(
            {
                "status": "text_extracted",
                "lines": [{"text": t} for t in texts],
            }
        )
    )
    (source / "extraction.json").write_text(json.dumps(data))
    (root / "catalogue.json").write_text(
        json.dumps([asdict(w) for w in [SEASONS, SPRING, SUMMER]])
    )
    report = module().replay(root, tmp_path / "results")
    assert report["raw_items"] == report["validated_items"] == 1
    assert report["derived_items"] == 2
    assert report["evaluated_items"] == 3
    assert report["unique_document_work_pairs"] == 3
    assert report["full_work_references"] == 0
    assert report["scoped_work_references"] == 3
