import pytest

from classic_hubble_pipeline.performance_dates import date_headings
from classic_hubble_pipeline.vision_publication import _date_matches


@pytest.mark.parametrize("heading, expected", [
    ("일시|2026.9.30(수)오후7시30분", (2026, 9, 30)),
    ("일시 2026.10.09.2 PM", (2026, 10, 9)),
    ("일 시:2026년10월10일(토)18:30", (2026, 10, 10)),
    ("일시 2026.10.15.(목)19:30", (2026, 10, 15)),
    ("일시2026.10.11.(일) 오후7:00", (2026, 10, 11)),
    ("일시|2026.10.11(일)오후5:00", (2026, 10, 11)),
    ("일시 | 2026년10월 5일 월요일 저녁6시", (2026, 10, 5)),
])
def test_explicit_event_date_label_preserves_literal_date(heading, expected):
    assert date_headings([heading]) == ({expected}, False)


def test_labeled_date_can_wrap_before_weekday():
    assert date_headings(["일시: 2026.10.15.", "(목)19:30"]) == (
        {(2026, 10, 15)}, False,
    )


@pytest.mark.parametrize("conflict", [
    "일시:2026.10.16.(금)19:30",
    "일시|2026.10.15.(금)19:30",
    "일시:2026.13.15.(목)",
    "일시:2026.10.15.24:00",
    "일시:2026.3.12.매월마지막수요일19:30",
    "일시:2026.10.15(목) & 10.16(금)",
])
def test_labeled_other_or_invalid_date_cannot_hide_beside_valid_date(conflict):
    doc = {"lines": [{"text": "2026.10.15.(목)19:30"}, {"text": conflict}]}
    assert not _date_matches(doc, "2026-10-15")


def test_labeled_wrapped_weekday_conflict_is_not_ignored():
    doc = {"lines": [
        {"text": "2026.10.15.(목)19:30"},
        {"text": "일시 2026.10.15."}, {"text": "(금)19:30"},
    ]}
    assert not _date_matches(doc, "2026-10-15")


@pytest.mark.parametrize("line", [
    "데뷔 일시 2026.10.15.(목)", "일시불명 2026.10.15.(목)",
    "공연경력: 일시 2026.10.15.(목)", "일시:10.15(목)",
    "일시 2026.10.1I.SUN7:00 PM", "일시 2026.10.15.",
])
def test_no_free_text_prefix_year_inference_or_ocr_digit_correction(line):
    assert not _date_matches({"lines": [{"text": line}]}, "2026-10-15")
