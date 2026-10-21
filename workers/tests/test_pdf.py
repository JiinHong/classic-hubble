import importlib

import pytest
from classic_hubble_pipeline.ocr import OcrInputError, OcrOutputError
from pdf_fixtures import make_pdf


def module():
    return importlib.import_module("classic_hubble_pipeline.pdf")


def recognized(_):
    return [
        {
            "text": "Mozart K. 488",
            "score": 0.9,
            "polygon": [[10, 20], [100, 20], [100, 40], [10, 40]],
        }
    ]


def test_text_pdf_uses_native_text_without_ocr():
    result = module().extract_pdf(make_pdf(), lambda _: pytest.fail("no OCR needed"))
    assert result["status"] == "text_extracted"
    assert result["review_status"] == "unverified"
    assert result["page_count"] == 1
    assert result["coordinate_space"] == "pdf_canvas_units"
    assert result["pages"][0]["method"] == "native"
    line = result["lines"][0]
    assert line["text"] == "Bach BWV 1001"
    assert line["method"] == "native" and line["score"] is None
    assert line["page_index"] == 0
    assert line["bbox"][0] == pytest.approx(20, abs=2)
    assert line["bbox"][1] == pytest.approx(150, abs=4)


def test_scan_is_rendered_and_ocr_coordinates_return_to_pdf_space():
    result = module().extract_pdf(make_pdf([{"image": True}]), recognized)
    assert result["pages"][0]["method"] == "ocr"
    line = result["lines"][0]
    assert line["text"] == "Mozart K. 488"
    assert line["method"] == "ocr" and line["page_index"] == 0
    assert line["polygon"][0] == pytest.approx([10 * 300 / 834, 200 - 20 * 200 / 556])
    assert 0 <= line["bbox"][1] < line["bbox"][3] <= 200


@pytest.mark.parametrize("nontext", ["image", "path"])
def test_mixed_pdf_keeps_native_heading_and_reads_visual_program(nontext):
    result = module().extract_pdf(
        make_pdf([{"text": "PROGRAM", nontext: True}]), recognized
    )
    assert {line["text"] for line in result["lines"]} == {"PROGRAM", "Mozart K. 488"}
    assert result["pages"][0]["method"] == "native_and_ocr"


def test_same_text_on_separate_pages_is_retained():
    result = module().extract_pdf(make_pdf([{"text": "Bach"}] * 2), recognized)
    assert [line["page_index"] for line in result["lines"]] == [0, 1]


def test_rotated_scan_records_page_rotation_and_valid_page_coordinates():
    result = module().extract_pdf(make_pdf([{"image": True}], rotation=90), recognized)
    assert result["pages"][0]["rotation"] == 90
    line = result["lines"][0]
    assert all(0 <= x <= 300 and 0 <= y <= 200 for x, y in line["polygon"])


def test_empty_page_is_no_text_not_an_unpublished_program():
    result = module().extract_pdf(make_pdf([{}]), lambda _: [])
    assert result["status"] == "no_text"
    assert result["review_status"] == "unverified"


@pytest.mark.parametrize("data", [b"not a pdf", b"%PDF-1.7\nbroken"])
def test_corrupt_pdf_is_explicit_manual_handling(data):
    with pytest.raises(OcrInputError, match="invalid_pdf"):
        module().extract_pdf(data, recognized)


def test_page_limit_does_not_silently_truncate(monkeypatch):
    monkeypatch.setattr(module(), "MAX_PDF_PAGES", 1)
    with pytest.raises(OcrInputError, match="pdf_page_limit"):
        module().extract_pdf(make_pdf([{}, {}]), lambda _: pytest.fail())


def test_oversized_render_is_rejected_before_ocr():
    with pytest.raises(OcrInputError, match="pdf_pixel_limit"):
        module().extract_pdf(
            make_pdf([{}], box=(0, 0, 10000, 10000)), lambda _: pytest.fail()
        )


def test_timeout_from_ocr_is_retryable_not_manual():
    def stop(_):
        raise TimeoutError("terminated")

    with pytest.raises(TimeoutError):
        module().extract_pdf(make_pdf([{"image": True}]), stop)


def test_subpixel_polygon_cannot_be_saved_as_zero_area_pdf_evidence():
    def tiny(_):
        return [
            {
                "text": "Bach",
                "score": 0.9,
                "polygon": [[10.1, 20], [10.2, 20], [10.2, 40], [10.1, 40]],
            }
        ]

    with pytest.raises(OcrOutputError):
        module().extract_pdf(make_pdf([{"image": True}]), tiny)


def test_pdf_password_failure_has_distinct_manual_reason(monkeypatch):
    pdf = module()

    def encrypted(_):
        raise pdf.pdfium.PdfiumError(
            "password", err_code=pdf.pdfium.raw.FPDF_ERR_PASSWORD
        )

    monkeypatch.setattr(pdf.pdfium, "PdfDocument", encrypted)
    with pytest.raises(OcrInputError, match="encrypted_pdf"):
        pdf.extract_pdf(b"locked", recognized)


def test_native_text_and_document_line_limits_are_explicit(monkeypatch):
    monkeypatch.setattr(module(), "MAX_PAGE_CHARS", 1)
    with pytest.raises(OcrInputError, match="pdf_text_limit"):
        module().extract_pdf(make_pdf(), lambda _: pytest.fail())
    monkeypatch.setattr(module(), "MAX_PAGE_CHARS", 1000)
    monkeypatch.setattr(module(), "MAX_DOCUMENT_LINES", 1)
    with pytest.raises(OcrInputError, match="pdf_text_limit"):
        module().extract_pdf(make_pdf([{"text": "Bach"}] * 2), lambda _: pytest.fail())


def test_native_and_ocr_exact_duplicates_keep_native_provenance():
    from contextlib import closing

    import pypdfium2 as pdfium

    data = make_pdf([{"text": "Bach", "image": True}])
    with pdfium.PdfDocument(data) as doc, closing(doc[0]) as page:
        with closing(page.get_textpage()) as textpage:
            textpage.count_rects()
            left, bottom, right, top = textpage.get_rect(0)
        convert = pdfium.PdfPosConv(page, (0, 0, 834, 556, 0))
        polygon = [
            list(convert.to_bitmap(x, y))
            for x, y in [(left, top), (right, top), (right, bottom), (left, bottom)]
        ]

    def read(_):
        return [{"text": "Bach", "score": 0.9, "polygon": polygon}]

    result = module().extract_pdf(data, read)
    assert len(result["lines"]) == 1
    assert result["lines"][0]["method"] == "native"
