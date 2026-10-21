"""Extract private PDF evidence, preserving page coordinates and provenance."""

from __future__ import annotations

import io
import math
from contextlib import closing

import pypdfium2 as pdfium

from .ocr import (
    PIPELINE_VERSION,
    OcrInputError,
    OcrOutputError,
    _overlap,
    extract_image,
)

PDF_PIPELINE_VERSION = f"pdfium-5.14.0-dpi200-v1+{PIPELINE_VERSION}"
MAX_PDF_PAGES = 100
MAX_RENDER_PIXELS = 16_000_000
MAX_PAGE_CHARS = 100_000
MAX_DOCUMENT_LINES = 10_000
RENDER_SCALE = 200 / 72


def _native_lines(page):
    with closing(page.get_textpage()) as textpage:
        if textpage.count_chars() > MAX_PAGE_CHARS:
            raise OcrInputError("pdf_text_limit")
        count = textpage.count_rects()
        if count > MAX_DOCUMENT_LINES:
            raise OcrInputError("pdf_text_limit")
        lines = []
        for i in range(count):
            left, bottom, right, top = textpage.get_rect(i)
            if not all(math.isfinite(v) for v in (left, bottom, right, top)):
                raise OcrInputError("invalid_pdf_coordinates")
            if left >= right or bottom >= top:
                continue
            text = textpage.get_text_bounded(
                left, bottom, right, top, errors="replace"
            ).strip()
            if text:
                lines.append(
                    {
                        "text": text,
                        "score": None,
                        "method": "native",
                        "polygon": [
                            [left, top],
                            [right, top],
                            [right, bottom],
                            [left, bottom],
                        ],
                        "bbox": [left, bottom, right, top],
                    }
                )
        return lines


def _ocr_lines(page, read):
    width, height = page.get_size()
    if (
        math.ceil(width * RENDER_SCALE) * math.ceil(height * RENDER_SCALE)
        > MAX_RENDER_PIXELS
    ):
        raise OcrInputError("pdf_pixel_limit")
    with closing(page.render(scale=RENDER_SCALE)) as bitmap:
        with bitmap.to_pil() as image, io.BytesIO() as buffer:
            image.save(buffer, format="PNG")
            result = extract_image(buffer.getvalue(), read)
        convert = bitmap.get_posconv(page)
        lines = []
        for line in result["lines"]:
            polygon = [
                list(convert.to_page(round(x), round(y))) for x, y in line["polygon"]
            ]
            bbox = [
                min(x for x, _ in polygon),
                min(y for _, y in polygon),
                max(x for x, _ in polygon),
                max(y for _, y in polygon),
            ]
            if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                raise OcrOutputError(
                    "Empty PDF text polygon after coordinate conversion"
                )
            lines.append(
                {
                    **line,
                    "method": "ocr",
                    "polygon": polygon,
                    "bbox": bbox,
                }
            )
        return lines, result["tile_count"]


def extract_pdf(content: bytes, read) -> dict:
    try:
        document = pdfium.PdfDocument(content)
    except pdfium.PdfiumError as error:
        reason = (
            "encrypted_pdf"
            if error.err_code == pdfium.raw.FPDF_ERR_PASSWORD
            else "invalid_pdf"
        )
        raise OcrInputError(reason) from None
    with document:
        if not 0 < len(document) <= MAX_PDF_PAGES:
            raise OcrInputError("pdf_page_limit")
        if document.get_formtype() != pdfium.raw.FORMTYPE_NONE:
            raise OcrInputError("unsupported_pdf_forms")
        lines, pages = [], []
        for page_index in range(len(document)):
            with closing(document[page_index]) as page:
                width, height = page.get_size()
                if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                    raise OcrInputError("invalid_pdf_dimensions")
                native = _native_lines(page)
                # A native heading does not imply that an embedded program is text.
                needs_ocr = (
                    not native
                    or any("\ufffd" in line["text"] for line in native)
                    or any(
                        obj.type != pdfium.raw.FPDF_PAGEOBJ_TEXT
                        for obj in page.get_objects(max_depth=1)
                    )
                    or pdfium.raw.FPDFPage_GetAnnotCount(page) > 0
                )
                recognized, tiles = _ocr_lines(page, read) if needs_ocr else ([], 0)
                page_lines = list(native)
                for line in recognized:
                    if not any(
                        " ".join(prior["text"].split())
                        == " ".join(line["text"].split())
                        and _overlap(prior["bbox"], line["bbox"]) >= 0.7
                        for prior in native
                    ):
                        page_lines.append(line)
                # Sort in displayed order, including rotated pages and offset boxes.
                convert = pdfium.PdfPosConv(
                    page, (0, 0, math.ceil(width), math.ceil(height), 0)
                )
                page_lines.sort(
                    key=lambda line: (
                        min(convert.to_bitmap(x, y)[1] for x, y in line["polygon"]),
                        min(convert.to_bitmap(x, y)[0] for x, y in line["polygon"]),
                    )
                )
                lines.extend({**line, "page_index": page_index} for line in page_lines)
                if len(lines) > MAX_DOCUMENT_LINES:
                    raise OcrInputError("pdf_text_limit")
                pages.append(
                    {
                        "page_index": page_index,
                        "width": width,
                        "height": height,
                        "bbox": list(page.get_bbox()),
                        "rotation": page.get_rotation(),
                        "method": ("native_and_ocr" if native else "ocr")
                        if needs_ocr
                        else "native",
                        "line_count": len(page_lines),
                        "tile_count": tiles,
                    }
                )
    return {
        "pipeline_version": PDF_PIPELINE_VERSION,
        "status": "text_extracted" if lines else "no_text",
        "review_status": "unverified",
        "coordinate_space": "pdf_canvas_units",
        "page_count": len(pages),
        "pages": pages,
        "lines": lines,
    }
