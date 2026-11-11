import copy
import hashlib

import pytest

from classic_hubble_pipeline import paddle_publication as pub
from test_music_extraction import quote
from test_paddle_publication import save, setup


def fixture():
    texts = ["2026. 10. 21 [수]", "Program", "10월 21일(수)", "Sergei Rachmaninoff",
             "Op. 18", "I. Moderato", "10월 22일(목)", "Sergei Rachmaninoff",
             "Piano Concerto No. 2 in C minor, Op. 18", "I. Moderato", "Artist"]

    def change(doc):
        doc.update(lines=[{"text": t, "score": .99} for t in texts])

    repo, store, data = setup(change)
    repo.load_ocr_results_for_sources = lambda *_: repo.load_ocr_results()
    repo.publish_paddle_program_bundle = repo.publish_paddle_program
    section = dict(version="dated-program-section-v1", performance_date="2026-10-22",
                   program_line=1, anchor_line=0, heading_line=6, end_line=10)

    def lookup(raw, sha, target):
        assert hashlib.sha256(raw.encode()).hexdigest() == sha == store.sha
        assert target == "2026-10-22"
        return section

    repo.load_paddle_program_section = lookup
    item = data["items"][0]
    item.update(composer=quote(7, texts[7]), title=quote(8, texts[8]),
                catalogue=quote(8, "Op. 18"), key=quote(8, "C minor"),
                movements=[quote(9, "I. Moderato")], scope="movement")
    return repo, store, data, section


@pytest.mark.parametrize("field", ["composer", "title", "catalogue", "key", "movements"])
def test_dated_bundle_keeps_only_wholly_bound_references(field, monkeypatch):
    repo, store, data, section = fixture()
    other = copy.deepcopy(data["items"][0])
    if field == "movements":
        other[field] = [quote(5, "I. Moderato")]
    elif field in ("key", "title"):
        other[field] = quote(4, "Op. 18")
    else:
        other[field][0]["line_id"] = "L000003" if field == "composer" else "L000004"
    data["items"].insert(0, other)
    rid = save(repo, store, data)
    monkeypatch.setattr(pub, "download_source", lambda *_: (store.original, "image/png"))
    assert pub.publish_bundle(repo, store, None, "p1", [rid])["items"] == 0
    preview = pub.publish_bundle(repo, store, None, "p1", [rid], dated_program=True)
    assert preview["items"] == 1 and preview["withheld_reasons"] == {"outside_performance_date_section": 1}
    result = pub.publish_bundle(repo, store, None, "p1", [rid], apply=True, dated_program=True)
    assert result == {"status": "published", "items": 1}
    payload, = repo.writes
    doc, = payload["p_documents"]
    assert doc["program_section"] == section and doc["date_binding"] == "dated_section"
    assert doc["matching"]["items"][0]["publication_eligible"] is False
    assert doc["matching"]["items"][1]["evidence"] == data["items"][1]
    assert doc["matching"]["items"][1]["source_index"] == 1
    assert payload["p_items"][0]["scope_details"] == ["I. Moderato"]
    assert payload["p_items"][0]["display_title"] == "Piano Concerto No. 2 in C minor, Op. 18"
    assert payload["p_items"][0]["performed_scope"] == "movement"
    assert hashlib.sha256(payload["p_evaluation"]["section_ocr_utf8"].encode()).hexdigest() == store.sha


def test_missing_date_section_or_changed_live_source_never_writes(monkeypatch):
    repo, store, data, _ = fixture()
    rid = save(repo, store, data)
    monkeypatch.setattr(pub, "download_source", lambda *_: (b"changed", "image/png"))
    assert pub.publish_bundle(repo, store, None, "p1", [rid], dated_program=True, apply=True)["status"] == "source_changed"
    repo.load_paddle_program_section = lambda *_: None
    assert pub.publish_bundle(repo, store, None, "p1", [rid], dated_program=True, apply=True)["items"] == 0
    assert not repo.writes
