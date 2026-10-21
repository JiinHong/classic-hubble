"""CPU OCR of archived images; output is evidence, never a verified program."""

from __future__ import annotations

import io
import math
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 40_000_000
TILE_SIDE = 1600
TILE_OVERLAP = 192
PIPELINE_VERSION = "paddle-3.7.0-pdx3.7.2-pp3.3.1-v5ko-t1600-o192-v1"
DETECTION_MODEL = "PP-OCRv5_mobile_det"
RECOGNITION_MODEL = "korean_PP-OCRv5_mobile_rec"


class OcrInputError(ValueError):
    """A source needs manual handling rather than a blind retry."""


class OcrOutputError(RuntimeError):
    """The recognition engine returned an unexpected result."""


def tile_boxes(
    width: int, height: int, *, side: int = TILE_SIDE, overlap: int = TILE_OVERLAP
) -> Iterator[tuple[int, int, int, int]]:
    if min(width, height) <= 0 or not 0 <= overlap < side:
        raise ValueError("Invalid tile dimensions")
    for y in range(0, max(1, height - overlap), side - overlap):
        for x in range(0, max(1, width - overlap), side - overlap):
            yield x, y, min(x + side, width), min(y + side, height)


def paddle_lines(response: dict[str, Any]) -> list[dict[str, Any]]:
    values = response.get("res", response)
    try:
        texts, scores, polygons = (
            values[key] for key in ("rec_texts", "rec_scores", "rec_polys")
        )
        return [
            {"text": text, "score": float(score), "polygon": polygon}
            for text, score, polygon in zip(texts, scores, polygons, strict=True)
        ]
    except (KeyError, TypeError, ValueError):
        raise OcrOutputError("Invalid PaddleOCR response") from None


class PaddleEngine:
    def __init__(self, model_dir: str):
        # Heavy dependencies are isolated from catalog collection and unit tests.
        from paddleocr import PaddleOCR

        root = Path(model_dir)
        for name in (DETECTION_MODEL, RECOGNITION_MODEL):
            if not (root / name / "inference.yml").is_file():
                raise ValueError("Bundled OCR model is missing")
        self._engine = PaddleOCR(
            text_detection_model_name=DETECTION_MODEL,
            text_recognition_model_name=RECOGNITION_MODEL,
            text_detection_model_dir=str(root / DETECTION_MODEL),
            text_recognition_model_dir=str(root / RECOGNITION_MODEL),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=TILE_SIDE,
            text_det_limit_type="max",
            text_rec_score_thresh=0.0,
            text_recognition_batch_size=1,
            device="cpu",
            cpu_threads=1,
            enable_mkldnn=False,
        )

    def read(self, tile: Image.Image) -> list[dict[str, Any]]:
        import numpy as np

        # Paddle's ndarray input uses OpenCV's BGR channel order.
        results = list(self._engine.predict(np.asarray(tile)[:, :, ::-1].copy()))
        if len(results) != 1:
            raise OcrOutputError("Expected one OCR result per tile")
        return paddle_lines(results[0].json)


def extract_image(
    content: bytes, read: Callable[[Image.Image], list[dict[str, Any]]]
) -> dict[str, Any]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise OcrInputError("pixel_limit")
                if getattr(source, "n_frames", 1) != 1:
                    raise OcrInputError("animated_image")
                oriented = ImageOps.exif_transpose(source).convert("RGBA")
                background = Image.new("RGBA", oriented.size, "white")
                image = Image.alpha_composite(background, oriented).convert("RGB")
    except TimeoutError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise OcrInputError("invalid_or_unsupported_image") from None

    lines: list[dict[str, Any]] = []
    boxes = list(tile_boxes(*image.size))
    for tile_index, (left, top, right, bottom) in enumerate(boxes):
        for raw in read(image.crop((left, top, right, bottom))):
            try:
                text = raw["text"].strip()
                score = float(raw["score"])
                polygon = [[float(x), float(y)] for x, y in raw["polygon"]]
                if (
                    len(polygon) != 4
                    or not 0 <= score <= 1
                    or not all(math.isfinite(v) for point in polygon for v in point)
                    or any(
                        not (0 <= x <= right - left and 0 <= y <= bottom - top)
                        for x, y in polygon
                    )
                ):
                    raise ValueError
            except (KeyError, TypeError, ValueError, AttributeError):
                raise OcrOutputError("Invalid text, score or coordinates") from None
            if not text:
                continue
            translated = [[x + left, y + top] for x, y in polygon]
            bbox = [
                min(p[0] for p in translated),
                min(p[1] for p in translated),
                max(p[0] for p in translated),
                max(p[1] for p in translated),
            ]
            if bbox[0] == bbox[2] or bbox[1] == bbox[3]:
                raise OcrOutputError("Empty text polygon")
            line = {
                "text": text,
                "score": score,
                "polygon": translated,
                "bbox": bbox,
                "tile_index": tile_index,
            }
            duplicate = next(
                (
                    i
                    for i, prior in enumerate(lines)
                    if prior["tile_index"] != tile_index
                    and prior["text"] == text
                    and _overlap(prior["bbox"], bbox) >= 0.7
                ),
                None,
            )
            if duplicate is None:
                lines.append(line)
            elif lines[duplicate]["score"] < score:
                lines[duplicate] = line
    lines.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return {
        "pipeline_version": PIPELINE_VERSION,
        "status": "text_extracted" if lines else "no_text",
        "review_status": "unverified",
        "coordinate_space": "exif_oriented_pixels",
        "width": image.width,
        "height": image.height,
        "tile_count": len(boxes),
        "lines": lines,
    }


def _overlap(a: list[float], b: list[float]) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    return intersection / min(
        (a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])
    )
