from copy import deepcopy

import httpx
import pytest
from classic_hubble_pipeline import wikipedia_work_names as module


def catalog():
    return (
        [
            {
                "id": "w",
                "composer_id": "c",
                "title": "Piano Sonata No. 23",
                "title_ko": None,
            }
        ],
        [{"id": "c", "name": "Ludwig van Beethoven", "name_ko": "루트비히 판 베토벤"}],
        [{"provider_id": "Q189046", "payload": {"work_id": "w"}}],
    )


def page():
    return {
        "pageid": 82892,
        "ns": 0,
        "title": "피아노 소나타 23번 (베토벤)",
        "pageprops": {"wikibase_item": "Q189046"},
        "revisions": [{"revid": 123}],
        "redirects": [
            {"ns": 0, "pageid": 2, "title": "열정 소나타"},
            {"ns": 0, "pageid": 3, "title": "열정 3악장", "fragment": "제3악장"},
            {"ns": 1, "pageid": 4, "title": "토론:열정"},
            {"ns": 0, "pageid": 5, "title": "Appassionata"},
        ],
    }


def test_exact_qid_names_have_evidence_and_composer_suffix_is_not_displayed():
    args = catalog()
    original = deepcopy(args)
    result = module.build_manifest([page()], *args)
    assert args == original
    entry = result["works"][0]
    assert entry["title_ko"] == "피아노 소나타 23번"
    assert entry["previous_title_ko"] is None
    assert {a["text"] for a in entry["aliases"]} == {
        "피아노 소나타 23번 (베토벤)",
        "피아노 소나타 23번",
        "열정 소나타",
    }
    source = result["sources"][entry["sources"][0]]
    assert source["revision_id"] == 123
    assert source["qid"] == "Q189046"
    assert "creativecommons.org" in source["license"]


def test_existing_reviewed_display_name_is_preserved():
    args = catalog()
    args[0][0]["title_ko"] = "피아노 소나타 23번 '열정'"
    assert (
        module.build_manifest([page()], *args)["works"][0]["title_ko"]
        == args[0][0]["title_ko"]
    )


def test_english_article_names_are_aliases_without_inventing_korean_names():
    p = page()
    p["title"] = "Piano Sonata No. 23 (Beethoven)"
    p["redirects"] = [
        {"ns": 0, "pageid": 9, "title": "Appassionata"},
        {"ns": 0, "pageid": 10, "title": "Appassionata finale", "fragment": "Finale"},
    ]
    manifest = module.build_manifest([p], *catalog(), language="en")
    entry = manifest["works"][0]
    assert entry["title_ko"] is None
    assert manifest["language"] == "en"
    assert {a["text"] for a in entry["aliases"]} == {
        "Piano Sonata No. 23 (Beethoven)",
        "Piano Sonata No. 23",
        "Appassionata",
    }
    assert all(a["locale"] == "en" for a in entry["aliases"])
    assert all(
        s["url"].startswith("https://en.wikipedia.org/")
        for s in manifest["sources"].values()
    )


def test_english_fetch_uses_english_endpoint_and_separate_cache(tmp_path):
    urls = []

    def respond(request):
        urls.append(request.url.host)
        return httpx.Response(200, json={"query": {"pages": {"1": page()}}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        module.fetch_pages(client, ["same"], tmp_path, delay=0)
        module.fetch_pages(client, ["same"], tmp_path, delay=0, language="en")
    assert urls == ["ko.wikipedia.org", "en.wikipedia.org"]


@pytest.mark.parametrize(
    "change", ["unknown_qid", "missing", "disambiguation", "namespace", "no_revision"]
)
def test_unbound_or_non_work_pages_cannot_supply_names(change):
    p = page()
    if change == "unknown_qid":
        p["pageprops"]["wikibase_item"] = "Q123456"
    elif change == "missing":
        p["missing"] = ""
    elif change == "disambiguation":
        p["pageprops"]["disambiguation"] = ""
    elif change == "namespace":
        p["ns"] = 14
    else:
        p["revisions"] = []
    assert module.build_manifest([p], *catalog())["works"] == []


def test_duplicate_work_crosswalk_is_rejected():
    args = catalog()
    args[2].append({"provider_id": "Q999", "payload": {"work_id": "w"}})
    with pytest.raises(ValueError, match="crosswalk"):
        module.build_manifest([page()], *args)


def test_fetch_continuation_keeps_all_redirects_and_resumes_from_cache(tmp_path):
    requests = []

    def respond(request):
        requests.append(request)
        assert "rvlimit" not in request.url.params
        p = page()
        if "rdcontinue" not in request.url.params:
            p["redirects"] = [{"ns": 0, "pageid": 1, "title": "열정"}]
            return httpx.Response(
                200,
                json={
                    "query": {"pages": {"82892": p}},
                    "continue": {"continue": "||", "rdcontinue": "next"},
                },
            )
        p.pop("revisions")
        p["redirects"] = [{"ns": 0, "pageid": 2, "title": "열정 소나타"}]
        return httpx.Response(200, json={"query": {"pages": {"82892": p}}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        pages = module.fetch_pages(client, [page()["title"]], tmp_path, delay=0)
        assert len(requests) == 2
        assert pages[0]["revisions"] == [{"revid": 123}]
        assert [r["title"] for r in pages[0]["redirects"]] == ["열정", "열정 소나타"]
        assert module.fetch_pages(client, [page()["title"]], tmp_path, delay=0) == pages
        assert len(requests) == 2


def test_api_errors_are_not_cached_as_empty_success(tmp_path):
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"error": {"code": "maxlag"}})
            )
        ) as client,
        pytest.raises(ValueError, match="maxlag"),
    ):
        module.fetch_pages(client, ["test"], tmp_path, delay=0)
    assert list(tmp_path.glob("*.json")) == []


def test_public_evidence_distinguishes_derivation_and_excludes_operational_fields():
    manifest = module.build_manifest([page()], *catalog())
    result = module.public_evidence([manifest])
    entry = result["datasets"][0]["works"][0]
    assert entry["qid"] == "Q189046"
    assert "previous_title_ko" not in entry
    assert "expected_title" not in entry
    assert result["datasets"][0]["origin"] == "wikipedia-names"
    assert result["datasets"][0]["sources"] == manifest["sources"]
    assert "한국어·영어 위키백과" in result["attribution"]
