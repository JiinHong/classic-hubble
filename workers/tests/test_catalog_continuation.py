import json
from pathlib import Path

from classic_hubble_pipeline.korean_work_names import validate_manifest
from classic_hubble_pipeline.wikipedia_work_names import public_evidence

ROOT = Path(__file__).resolve().parents[2]


def manifest():
    return json.loads(
        (ROOT / "workers/data/korean-catalog-continuation.json").read_text()
    )


def test_continuation_preserves_existing_names_and_has_traceable_evidence():
    data = manifest()
    validate_manifest(data)
    assert len(data["works"]) == 375
    for entry in data["works"]:
        if entry["previous_title_ko"]:
            assert entry["title_ko"] == entry["previous_title_ko"]
        assert entry["evidence"]
        assert all(e["source"] in data["sources"] for e in entry["evidence"])
    for source in data["sources"].values():
        if source["kind"] == "encyclopedia_worklist_names":
            assert source["revision_id"]
            assert source["license"]


def test_continuation_prefers_observed_programme_names_and_rejects_scope_errors():
    entries = {e["qid"]: e for e in manifest()["works"]}
    assert entries["Q2746359"]["title_ko"] == "엘레지"
    assert entries["Q946777"]["title_ko"] == "핑갈의 동굴"
    assert entries["Q2610891"]["title_ko"] == "불꽃을 향하여"
    for qid in (
        "Q1127388",
        "Q3198808",
        "Q3200500",
        "Q392734",
        "Q3592579",
        "Q4736239",
        "Q19896035",
    ):
        assert qid not in entries
    assert all(
        "Sarabande" not in a["text"] for e in entries.values() for a in e["aliases"]
    )


def test_public_evidence_matches_the_reviewed_manifest_without_private_ids():
    public = json.loads(
        (ROOT / "apps/web/public/reference/korean-work-names.json").read_text()
    )
    expected = public_evidence([manifest()])["datasets"][0]
    assert (
        next(d for d in public["datasets"] if d["version"] == expected["version"])
        == expected
    )
    for entry in expected["works"]:
        assert "previous_title_ko" not in entry
        assert "work_id" not in entry
