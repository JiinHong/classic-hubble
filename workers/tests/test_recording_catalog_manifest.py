import json
from pathlib import Path

from classic_hubble_pipeline.korean_work_names import validate_manifest
from classic_hubble_pipeline.recording_names import match_recording_name, observed_name
from classic_hubble_pipeline.wikipedia_work_names import public_evidence

ROOT = Path(__file__).resolve().parents[2]


def manifest():
    return json.loads((ROOT / "workers/data/korean-recording-names.json").read_text())


def test_recording_names_are_traceable_and_preserve_existing_display_names():
    data = manifest()
    validate_manifest(data)
    assert len(data["works"]) == 977
    assert sum(e["previous_title_ko"] is None for e in data["works"]) == 814
    for entry in data["works"]:
        if entry["previous_title_ko"]:
            assert entry["title_ko"] == entry["previous_title_ko"]
        observed = set()
        for evidence in entry["evidence"]:
            assert evidence["source"] in data["sources"]
            assert evidence["english_source"] in data["sources"]
            work = {
                "id": entry["qid"],
                "title": entry["expected_title"],
                "composer": entry["composer"],
                "catalogue": evidence["catalogue"],
            }
            assert match_recording_name(evidence, [work]) == entry["qid"]
            observed.add(("ko", observed_name(evidence["title_ko"])))
            observed.add(("en", observed_name(evidence["title_en"])))
        assert all((a["locale"], a["text"]) in observed for a in entry["aliases"])
    assert all(len(s["sha256"]) == 64 for s in data["sources"].values())


def test_does_not_import_incorrect_notes_variants_or_member_names():
    entries = {e["qid"]: e for e in manifest()["works"]}
    assert entries["Q727987"]["title_ko"] == "론도 다단조, Op. 1"
    assert not any("이별" in a["text"] for a in entries["Q727987"]["aliases"])
    assert "Q137361008" not in entries
    assert "Q67199894" not in entries  # K. 11 source key conflicts with C minor.
    for entry in entries.values():
        assert all("Variant of" not in a["text"] for a in entry["aliases"])
        assert all("Dubious Authorship" not in a["text"] for a in entry["aliases"])


def test_recording_evidence_is_published_without_database_identifiers():
    public = json.loads(
        (ROOT / "apps/web/public/reference/korean-work-names.json").read_text()
    )
    expected = public_evidence([manifest()])["datasets"][0]
    assert (
        next(d for d in public["datasets"] if d["version"] == expected["version"])
        == expected
    )
    assert all(
        "previous_title_ko" not in entry and "work_id" not in entry
        for entry in expected["works"]
    )
