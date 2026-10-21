import io
import math

import pytest
from classic_hubble_pipeline import ocr
from PIL import Image


def image_bytes(size=(100, 100), mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def line(text="Bach BWV 1001", score=0.9, y=10):
    return {
        "text": text,
        "score": score,
        "polygon": [[10, y], [90, y], [90, y + 10], [10, y + 10]],
    }


def test_long_and_wide_images_are_fully_covered_with_overlap():
    boxes = list(ocr.tile_boxes(2300, 5100, side=1600, overlap=192))
    assert len(boxes) == 8
    assert boxes[0] == (0, 0, 1600, 1600)
    assert boxes[-1][2:] == (2300, 5100)
    for y in range(0, 5100, 100):
        for x in range(0, 2300, 100):
            assert any(l <= x < r and t <= y < b for l, t, r, b in boxes)
    assert all(r - l <= 1600 and b - t <= 1600 for l, t, r, b in boxes)


def test_tile_coordinates_are_restored_and_overlap_duplicates_removed():
    responses = iter([[line(y=1450)], [line(y=42, score=0.95), line(y=300)]])
    result = ocr.extract_image(image_bytes((200, 2000)), lambda _: next(responses))
    assert result["status"] == "text_extracted"
    assert result["width"] == 200 and result["height"] == 2000
    assert len(result["lines"]) == 2
    assert result["lines"][0]["score"] == 0.95
    assert result["lines"][0]["polygon"][0] == [10, 1450]
    assert result["lines"][1]["polygon"][0] == [10, 1708]
    assert result["review_status"] == "unverified"


def test_textless_image_is_not_treated_as_unpublished_program():
    result = ocr.extract_image(image_bytes(), lambda _: [])
    assert result["status"] == "no_text"
    assert result["lines"] == []


def test_rgba_is_composited_on_white_before_ocr():
    buf = io.BytesIO()
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(buf, format="PNG")

    def read(tile):
        assert tile.mode == "RGB"
        assert tile.getpixel((0, 0)) == (255, 255, 255)
        return []

    ocr.extract_image(buf.getvalue(), read)


@pytest.mark.parametrize("data", [b"bad", b"%PDF-1.7"])
def test_invalid_or_pdf_input_does_not_silently_become_empty_ocr(data):
    with pytest.raises(ocr.OcrInputError):
        ocr.extract_image(data, lambda _: pytest.fail("must not infer"))


def test_pixel_limit_is_checked_before_decoding(monkeypatch):
    monkeypatch.setattr(ocr, "MAX_IMAGE_PIXELS", 50)
    with pytest.raises(ocr.OcrInputError, match="pixel_limit"):
        ocr.extract_image(image_bytes(), lambda _: pytest.fail("must not infer"))


def test_animated_image_is_explicitly_unsupported():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(
        buf,
        format="GIF",
        save_all=True,
        append_images=[Image.new("RGB", (10, 10), "black")],
        duration=100,
    )
    with pytest.raises(ocr.OcrInputError, match="animated"):
        ocr.extract_image(buf.getvalue(), lambda _: [])


@pytest.mark.parametrize("score", [math.nan, math.inf, -1, 1.5])
def test_invalid_engine_output_is_not_persisted(score):
    with pytest.raises(ocr.OcrOutputError):
        ocr.extract_image(image_bytes(), lambda _: [line(score=score)])


def test_paddle_response_adapter_preserves_text_scores_and_polygons():
    response = {
        "res": {
            "rec_texts": ["Bach"],
            "rec_scores": [0.98],
            "rec_polys": [[[1, 2], [30, 2], [30, 10], [1, 10]]],
        }
    }
    assert ocr.paddle_lines(response) == [
        {"text": "Bach", "score": 0.98, "polygon": [[1, 2], [30, 2], [30, 10], [1, 10]]}
    ]
    response["res"]["rec_scores"] = []
    with pytest.raises(ocr.OcrOutputError):
        ocr.paddle_lines(response)


def test_termination_during_image_decode_remains_retryable(monkeypatch):
    def interrupted(*args, **kwargs):
        raise TimeoutError("termination")

    monkeypatch.setattr(Image, "open", interrupted)
    with pytest.raises(TimeoutError):
        ocr.extract_image(b"image", lambda _: [])
