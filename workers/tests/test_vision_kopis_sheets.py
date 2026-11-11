from types import SimpleNamespace

import pytest

from classic_hubble_pipeline import vision_publication as vp


def setup(monkeypatch):
    import hashlib
    from classic_hubble_pipeline.music_extraction import digest

    docs = {url: url.encode() for url in ("cover", "front", "back")}
    hashes = {u: hashlib.sha256(x).hexdigest() for u, x in docs.items()}
    originals, downloads, calls = [], [], []
    def resolve(pid, detail, packet, expected):
        calls.append(expected)
        assert pid == "concert" and detail == "b"*64 and [p["url"] for p in packet] == list(docs)
        assert all(p["reading_key"] == digest(vp._identity(store, p["sha"])) for p in packet)
        if expected is None:
            return {"status":"ready","items":2,"program":[{"work_id":"first"},{"work_id":"second"}]}
        assert expected == [{"work_id":"first"},{"work_id":"second"}]
        assert all(p["live_sha"] == p["sha"] and p["content_type"]=="image/jpeg" and p["checked_at"] for p in packet)
        return {"status":"published","items":2}
    store = SimpleNamespace(bucket="classic-hubble-sources")
    repo = SimpleNamespace(load_vision_target=lambda _:dict(starts_on="2026-10-22",ends_on="2026-10-22",intro_image_urls=list(docs)),
        load_vision_source=lambda u:dict(source_url=u,sha256=hashes[u],object_key="originals/sha256/"+hashes[u][:2]+"/"+hashes[u],
            bucket=store.bucket,content_type="image/jpeg",performance_ids=["concert"]),
        publish_direct_kopis_sheets=resolve)
    monkeypatch.setattr(vp,"_original",lambda s,ident:originals.append(ident["source_sha256"]))
    monkeypatch.setattr(vp,"_cached",lambda r,s,ident:{"reading":{"source_sha256":ident["source_sha256"],
        "status":"text_extracted","coverage":"complete","lines":[{"text":"text","page_index":0}],"items":[]}})
    def download(client,url):
        downloads.append(url)
        return docs[url],"image/jpeg"
    monkeypatch.setattr(vp,"download_source",download)
    return repo,store,docs,originals,downloads,calls


def test_sheet_preview_reuses_all_verified_originals_and_apply_checks_live_bytes(monkeypatch):
    repo,store,_,originals,downloads,calls=setup(monkeypatch)
    assert vp.publish_kopis_sheets(repo,store,None,"concert","b"*64)["status"]=="ready"
    assert len(originals)==3 and not downloads and calls==[None]
    assert vp.publish_kopis_sheets(repo,store,None,"concert","b"*64,apply=True)=={"status":"published","items":2}
    assert downloads==["cover","front","back"] and len(calls)==3


@pytest.mark.parametrize("why",["missing_reading","missing_source","partial","changed","foreign_date"])
def test_sheet_errors_never_send_a_write(monkeypatch,why):
    repo,store,docs,_,_,calls=setup(monkeypatch)
    if why=="missing_source":repo.load_vision_source=lambda _: None
    elif why=="missing_reading":monkeypatch.setattr(vp,"_cached",lambda *_:None)
    elif why=="partial":monkeypatch.setattr(vp,"_cached",lambda *_:{"reading":{"coverage":"partial"}})
    elif why=="foreign_date":repo.load_vision_target=lambda _: dict(starts_on="2026-10-21",ends_on="2026-10-22",intro_image_urls=list(docs))
    else:monkeypatch.setattr(vp,"download_source",lambda c,u:(b"changed","image/jpeg"))
    result=vp.publish_kopis_sheets(repo,store,None,"concert","b"*64,apply=True)
    assert result["items"]==0 and all(c is None for c in calls)
