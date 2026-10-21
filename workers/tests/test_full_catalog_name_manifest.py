import json
from pathlib import Path

from classic_hubble_pipeline.catalog_import import digest
from classic_hubble_pipeline.catalog_name_audit import build_audit
from classic_hubble_pipeline.korean_work_names import validate_manifest
from classic_hubble_pipeline.recording_names import observed_name
from classic_hubble_pipeline.wikipedia_work_names import public_evidence

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_every_original_target_has_one_outcome_and_source_evidence():
    audit = load("apps/web/public/reference/work-name-audit.json")
    assert audit["summary"]["total"] == len(audit["works"]) == 8442
    assert len({r["qid"] for r in audit["works"]}) == 8442
    assert audit == build_audit(
        [r["qid"] for r in audit["works"]],
        audit["works"],
        audit["sources"],
        audit["version"],
    )
    assert all(f"wikidata-{r['qid']}" in r["sources"] for r in audit["works"])
    assert all(
        "work_id" not in r and "previous_title_ko" not in r for r in audit["works"]
    )


def test_applied_names_equal_the_audit_named_outcomes_and_observed_terms():
    manifest = load("workers/data/korean-full-audit-names.json")
    validate_manifest(manifest)
    audit = load("apps/web/public/reference/work-name-audit.json")
    named = {r["qid"]: r for r in audit["works"] if r["status"] == "named"}
    assert set(named) == {e["qid"] for e in manifest["works"]}
    assert manifest["origin"] == "worklist-names"
    for entry in manifest["works"]:
        assert entry["previous_title_ko"] is None
        assert named[entry["qid"]]["title_ko"] == entry["title_ko"]
        assert named[entry["qid"]]["dictionary_sha256"] == digest(manifest)
        observed = {
            (locale, observed_name(e[f"title_{locale}"]))
            for e in entry["evidence"]
            for locale in ("ko", "en")
        }
        if "reviewed_usage" in entry:
            observed.add(("ko", entry["reviewed_usage"]["observed_title"]))
        assert all((a["locale"], a["text"]) in observed for a in entry["aliases"])
        assert ("ko", entry["title_ko"]) in observed
    public = load("apps/web/public/reference/korean-work-names.json")
    assert public_evidence([manifest])["datasets"][0] in public["datasets"]


def test_publisher_errors_and_uncertain_scopes_are_not_published_as_names():
    entries = {
        e["qid"]: e for e in load("workers/data/korean-full-audit-names.json")["works"]
    }
    review = load("workers/data/work-name-audit-review.json")
    assert not set(review["held"]) & entries.keys()
    for qid, rule in review["preferred_names"].items():
        assert entries[qid]["title_ko"] == rule["title_ko"]
        assert not set(rule["exclude_aliases"]) & {
            a["text"] for a in entries[qid]["aliases"]
        }
    if "Q3479100" in entries:
        assert not any(
            a["text"] == "세쿠엔차 12" for a in entries["Q3479100"]["aliases"]
        )
