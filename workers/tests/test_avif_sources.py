"""Synthetic AVIF transport/view tests, not OCR accuracy claims."""

import hashlib
import io
import json
import struct

import httpx
import pytest
from PIL import Image, features

from classic_hubble_pipeline import direct_vision, source_archive
from classic_hubble_pipeline.ocr import extract_image
from test_bitmap_sources import source as bitmap_source


def avif(*, alpha=False, sequence=False):
    buffer = io.BytesIO()
    mode, color = ("RGBA", (240, 30, 50, 0)) if alpha else ("RGB", (240, 30, 50))
    image = Image.new(mode, (4, 3), color)
    extra = {"save_all": True, "append_images": [Image.new(mode, (4, 3), "blue")]} if sequence else {}
    image.save(buffer, format="AVIF", max_threads=1, **extra)
    return buffer.getvalue()


def download(raw, **kwargs):
    with httpx.Client(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, content=raw, headers={"Content-Type": "image/jpeg"})
    )) as client:
        return source_archive.download_source(client, "http://www.kopis.or.kr/upload/fixture.JPG", **kwargs)


def source(raw):
    repo, store = bitmap_source(raw)
    repo.sources[0]["content_type"] = "image/avif"
    return repo, store


def test_mislabeled_jpeg_still_avif_keeps_original_bytes():
    raw = avif()
    assert raw[4:12] == b"ftypavif"
    assert download(raw) == (raw, "image/avif")


@pytest.mark.parametrize("raw", [
    b"", b"\x00\x00\x00\x20ftypavif", b"<html>avif</html>",
    bytes.fromhex("00000020667479706176696600000000617669666d6966316d6961664d413142"),
])
def test_header_without_decodable_pixels_is_not_archived(raw):
    with pytest.raises(source_archive.SourceDownloadError):
        download(raw)


@pytest.mark.parametrize("brand", [b"heic", b"mif1", b"avis", b"mp42"])
def test_other_major_brands_are_not_reclassified_as_still_avif(brand):
    raw = bytearray(avif())
    raw[8:12] = brand
    with pytest.raises(source_archive.SourceDownloadError):
        download(bytes(raw))


@pytest.mark.parametrize("size", [0, 1, 8, 17, 2**32 - 1])
def test_invalid_file_type_box_lengths_are_rejected(size):
    raw = bytearray(avif())
    struct.pack_into(">I", raw, 0, size)
    with pytest.raises(source_archive.SourceDownloadError):
        download(bytes(raw))


def test_avif_truncated_pixel_payload_is_not_archived():
    with pytest.raises(source_archive.SourceDownloadError):
        download(avif()[:-10])


def test_avif_sequence_remains_unsupported():
    with pytest.raises(source_archive.SourceDownloadError):
        download(avif(sequence=True))


def test_avif_download_cap_still_applies():
    with pytest.raises(source_archive.SourceDownloadError, match="size"):
        download(avif(), max_bytes=16)


def test_avif_decoder_bomb_warning_is_a_source_failure(monkeypatch):
    raw = avif()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(source_archive.SourceDownloadError, match="AVIF"):
        download(raw)


def test_avif_explicit_pixel_cap_is_independent_of_pillow_default(monkeypatch):
    from classic_hubble_pipeline import avif as module

    raw = avif()
    monkeypatch.setattr(module, "MAX_AVIF_PIXELS", 10)
    with pytest.raises(source_archive.SourceDownloadError, match="AVIF"):
        download(raw)


def test_avif_missing_pillow_is_a_source_failure(monkeypatch):
    import builtins

    raw = avif()
    original = builtins.__import__

    def without_pillow(name, *args, **kwargs):
        if name == "PIL":
            raise ModuleNotFoundError("Pillow absent")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pillow)
    with pytest.raises(source_archive.SourceDownloadError, match="AVIF.*unavailable"):
        download(raw)


def test_missing_avif_codec_is_reported_without_installation(monkeypatch, tmp_path):
    raw = avif()
    original = features.check
    monkeypatch.setattr(features, "check", lambda name: False if name == "avif" else original(name))
    with pytest.raises(source_archive.SourceDownloadError, match="AVIF.*unavailable"):
        download(raw)
    repo, store = source(raw)
    with pytest.raises(ValueError, match="AVIF.*unavailable"):
        direct_vision.prepare(repo, store, store.sha, tmp_path / "view")
    assert not (tmp_path / "view").exists()


@pytest.mark.parametrize("alpha", [False, True])
def test_direct_avif_view_preserves_original_and_records_png_provenance(alpha, tmp_path):
    raw = avif(alpha=alpha)
    repo, store = source(raw)
    folder = tmp_path / "avif"
    result = direct_vision.prepare(repo, store, store.sha, folder)
    assert result["path"] == str(folder / "original.avif")
    assert (folder / "original.avif").read_bytes() == raw
    view = (folder / "view.png").read_bytes()
    with Image.open(io.BytesIO(raw)) as original, Image.open(io.BytesIO(view)) as derived:
        expected = Image.alpha_composite(Image.new("RGBA", original.size, "white"), original.convert("RGBA")).convert("RGB")
        assert derived.size == expected.size == (4, 3)
        assert derived.tobytes() == expected.tobytes()
    request = json.loads((folder / "reading-request.json").read_text())
    assert request["derived_views"] == [{
        "filename": "view.png", "sha256": hashlib.sha256(view).hexdigest(),
        "source_sha256": store.sha, "method": "avif-exif-rgba-white-png-v1", "width": 4, "height": 3,
    }]
    assert folder.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in folder.iterdir())
    assert not repo.writes and not store.saved


def test_invalid_avif_does_not_leave_partial_export(tmp_path):
    repo, store = source(avif()[:-10])
    with pytest.raises(ValueError, match="AVIF"):
        direct_vision.prepare(repo, store, store.sha, tmp_path / "view")
    assert not (tmp_path / "view").exists()


def test_cached_avif_reading_does_not_decode_original_again(tmp_path, monkeypatch):
    from test_direct_vision import run

    repo, store = source(avif())
    run(repo, store, apply=True)
    read = store.read
    store.read = lambda key: pytest.fail("original reread") if key == store.key else read(key)
    monkeypatch.setattr(Image, "open", lambda *_: pytest.fail("AVIF decoded again"))
    result = direct_vision.prepare(repo, store, store.sha, tmp_path / "view")
    assert result["mode"] == "cached" and not (tmp_path / "view").exists()


def test_existing_ocr_reads_original_still_avif_bytes():
    seen = []
    result = extract_image(avif(), lambda tile: seen.append((tile.size, tile.mode)) or [])
    assert seen == [((4, 3), "RGB")]
    assert result["status"] == "no_text"


def test_avif_archive_preserves_hash_history_and_resume_pointer():
    from datetime import date
    from test_source_archive import Repository as ArchiveRepository, Store as ArchiveStore

    raw = avif()
    repo, store = ArchiveRepository(), ArchiveStore()
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as client:
        result = source_archive.archive_sources(repo, store, client, as_of=date(2026, 10, 22))
    assert result["counters"]["archived"] == 1
    pointer = repo.load_source_archives()[0]
    assert pointer["content_type"] == "image/avif" and pointer["sha256"] == hashlib.sha256(raw).hexdigest()
    assert any(kind == "source_version" for kind, _ in repo.records)
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("cached AVIF"))) as client:
        again = source_archive.archive_sources(repo, store, client, as_of=date(2026, 10, 22))
    assert again["counters"]["skipped"] == 1


def test_avif_view_matches_existing_ocr_orientation_and_pixels(tmp_path):
    buffer = io.BytesIO()
    image = Image.new("RGB", (4, 3), "red")
    image.putpixel((0, 0), (0, 0, 255))
    exif = Image.Exif()
    exif[274] = 6
    image.save(buffer, format="AVIF", exif=exif, max_threads=1)
    raw = buffer.getvalue()
    repo, store = source(raw)
    result = direct_vision.prepare(repo, store, store.sha, tmp_path / "view")
    seen = []
    extract_image(raw, lambda tile: seen.append((tile.size, tile.tobytes())) or [])
    with Image.open(result["view_path"]) as view:
        assert seen == [(view.size, view.tobytes())]
