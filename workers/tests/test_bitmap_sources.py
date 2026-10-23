"""Synthetic format tests, not OCR or direct-reading accuracy measurements."""

import hashlib
import io
import json
import struct

import httpx
import pytest
from PIL import Image

from classic_hubble_pipeline import direct_vision, source_archive
from classic_hubble_pipeline.ocr import extract_image
from test_direct_vision import Repository, Store


def bitmap(*, height=2):
    pixels = b"\x00\x00\xff\x00\xff\x00\x00\x00" * abs(height)
    return struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54) + struct.pack(
        "<IiiHHIIiiII", 40, 2, height, 1, 24, 0, len(pixels), 0, 0, 0, 0
    ) + pixels


def download(data):
    with httpx.Client(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, content=data, headers={"Content-Type": "image/jpeg"})
    )) as client:
        return source_archive.download_source(client, "http://www.kopis.or.kr/upload/fixture.bmp")


@pytest.mark.parametrize("height", [2, -2])
def test_archive_recognizes_valid_24bit_bitmap_and_preserves_original(height):
    raw = bitmap(height=height)
    content, kind = download(raw)
    assert content == raw and kind == "image/bmp"


@pytest.mark.parametrize("offset,format,value", [
    (2, "I", 0), (6, "H", 1), (8, "H", 1), (10, "I", 53),
    (14, "I", 12), (18, "i", 0), (18, "i", -2), (22, "i", 0),
    (26, "H", 2), (28, "H", 32), (30, "I", 1), (34, "I", 15),
    (46, "I", 1), (50, "I", 1), (18, "i", 2_000_000_000),
])
def test_malformed_or_unimplemented_bitmap_is_not_archived(offset, format, value):
    raw = bytearray(bitmap())
    struct.pack_into("<" + format, raw, offset, value)
    with pytest.raises(source_archive.SourceDownloadError):
        download(bytes(raw))


@pytest.mark.parametrize("raw", [b"BM", bitmap()[:53], bitmap()[:-1], bitmap() + b"trailer"])
def test_truncated_or_size_inconsistent_bitmap_is_not_archived(raw):
    with pytest.raises(source_archive.SourceDownloadError):
        download(raw)


def test_zero_optional_bitmap_image_size_is_supported():
    raw = bytearray(bitmap())
    struct.pack_into("<I", raw, 34, 0)
    assert download(bytes(raw)) == (bytes(raw), "image/bmp")


def test_observed_kopis_bitmap_header_with_synthetic_complete_payload():
    header = bytes.fromhex(
        "424d2617b7000000000036000000280000009d0600003a0900000100180000000000"
        "f016b700610f0000610f00000000000000"
    )
    raw = header + bytes(11_999_014 - len(header))
    assert download(raw) == (raw, "image/bmp")


def test_bitmap_does_not_bypass_download_byte_cap():
    with httpx.Client(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, content=bitmap())
    )) as client, pytest.raises(source_archive.SourceDownloadError, match="size"):
        source_archive.download_source(client, "https://kopis.or.kr/upload/test.bmp", max_bytes=16)


def test_bitmap_archive_keeps_original_hash_version_and_resume_pointer():
    from datetime import date
    from test_source_archive import Repository as ArchiveRepository, Store as ArchiveStore

    raw = bitmap()
    repo, store = ArchiveRepository(), ArchiveStore()
    with httpx.Client(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, content=raw)
    )) as client:
        result = source_archive.archive_sources(repo, store, client, as_of=date(2026, 10, 22))
    assert result["counters"]["archived"] == 1
    pointers = repo.load_source_archives()
    assert len(pointers) == 1 and pointers[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert pointers[0]["content_type"] == "image/bmp"
    assert any(kind == "source_version" for kind, _ in repo.records)
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("cached bitmap"))) as client:
        resumed = source_archive.archive_sources(repo, store, client, as_of=date(2026, 10, 22))
    assert resumed["counters"]["skipped"] == 1


def source(raw):
    store = Store()
    store.source = raw
    store.sha = hashlib.sha256(raw).hexdigest()
    store.key = f"originals/sha256/{store.sha[:2]}/{store.sha}"
    store.objects = {store.key: raw}
    repo = Repository(store)
    repo.sources[0].update(content_type="image/bmp", source_url="https://kopis.or.kr/upload/fixture.bmp")
    return repo, store


@pytest.mark.parametrize("height", [2, -2])
def test_direct_prepare_preserves_bitmap_and_records_lossless_view(height, tmp_path):
    raw = bitmap(height=height)
    repo, store = source(raw)
    folder = tmp_path / "bmp"
    result = direct_vision.prepare(repo, store, store.sha, folder)
    assert result["path"] == str(folder / "original.bmp")
    assert result["view_path"] == str(folder / "view.png")
    assert (folder / "original.bmp").read_bytes() == raw
    view = (folder / "view.png").read_bytes()
    with Image.open(io.BytesIO(raw)) as original, Image.open(io.BytesIO(view)) as derived:
        assert original.size == derived.size == (2, 2)
        assert original.convert("RGB").tobytes() == derived.convert("RGB").tobytes()
    request = json.loads((folder / "reading-request.json").read_text())
    assert request["derived_views"] == [{
        "filename": "view.png", "sha256": hashlib.sha256(view).hexdigest(),
        "source_sha256": store.sha, "method": "bmp-rgb-to-png-v1", "width": 2, "height": 2,
    }]
    assert folder.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in folder.iterdir())
    assert not repo.writes and not store.saved


def test_direct_prepare_rejects_malformed_bitmap_before_local_export(tmp_path):
    repo, store = source(bitmap()[:-1])
    with pytest.raises(ValueError, match="bitmap"):
        direct_vision.prepare(repo, store, store.sha, tmp_path / "bmp")
    assert not (tmp_path / "bmp").exists() and not repo.writes


def test_missing_view_dependency_does_not_leave_partial_export(tmp_path, monkeypatch):
    import builtins

    original_import = builtins.__import__

    def without_pillow(name, *args, **kwargs):
        if name == "PIL":
            raise ModuleNotFoundError("Pillow is unavailable")
        return original_import(name, *args, **kwargs)

    repo, store = source(bitmap())
    monkeypatch.setattr(builtins, "__import__", without_pillow)
    with pytest.raises(ModuleNotFoundError, match="Pillow"):
        direct_vision.prepare(repo, store, store.sha, tmp_path / "bmp")
    assert not (tmp_path / "bmp").exists() and not repo.writes


def test_cached_bitmap_reading_does_not_decode_or_export_again(tmp_path, monkeypatch):
    from test_direct_vision import run

    repo, store = source(bitmap())
    run(repo, store, apply=True)
    read = store.read
    store.read = lambda key: pytest.fail("original reread") if key == store.key else read(key)
    monkeypatch.setattr(Image, "open", lambda *_: pytest.fail("bitmap decoded again"))
    result = direct_vision.prepare(repo, store, store.sha, tmp_path / "bmp")
    assert result["mode"] == "cached" and not (tmp_path / "bmp").exists()


def test_original_bitmap_bytes_are_accepted_by_existing_ocr():
    observed = []
    result = extract_image(bitmap(), lambda tile: observed.append((tile.size, tile.mode)) or [])
    assert observed == [((2, 2), "RGB")]
    assert result["status"] == "no_text"
