from __future__ import annotations

from pathlib import Path

import pytest

from app.imports import parsing as parsing_module
from app.imports.normalization import normalize_phone, parse_currency
from app.imports.ocr import (
    OcrPage,
    clean_ocr_text,
    is_available,
    ocr_page,
    parse_tsv,
    reconstruct_rows,
)
from app.imports.parsing import parse_pdf
from app.imports.validation import inputs_from_raw, normalize_row

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF_SAMPLES = FIXTURES / "pdf"
SCANNED_SAMPLE = PDF_SAMPLES / "sample-02-scanned-image.pdf"

_TSV_HEADER = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
    "left\ttop\twidth\theight\tconf\ttext"
)


def _tsv(*rows: str) -> str:
    return "\n".join((_TSV_HEADER, *rows))


def _word(
    block: int,
    paragraph: int,
    line: int,
    word: int,
    left: int,
    text: str,
    *,
    width: int = 50,
    top: int = 100,
    conf: float = 90,
) -> str:
    return (
        f"5\t1\t{block}\t{paragraph}\t{line}\t{word}\t"
        f"{left}\t{top}\t{width}\t20\t{conf}\t{text}"
    )


def test_parse_tsv_reads_level_five_words_only() -> None:
    output = _tsv(
        "4\t1\t1\t1\t1\t0\t0\t0\t0\t0\t-1\t",
        _word(1, 1, 1, 1, 800, "الاسم"),
        _word(1, 1, 1, 2, 700, "الهاتف"),
        _word(1, 1, 2, 1, 700, "0990000001"),
    )

    words = parse_tsv(output)

    assert len(words) == 3
    assert [word.text for word in words] == ["الاسم", "الهاتف", "0990000001"]
    assert words[0].confidence == 90


def test_reconstruct_rows_merges_cells_on_gaps_and_reverses_rtl() -> None:
    words = parse_tsv(
        _tsv(
            _word(1, 1, 1, 2, 800, "الاسم"),
            _word(1, 1, 1, 1, 700, "الهاتف"),
            _word(1, 1, 2, 1, 700, "0990000001", width=90),
            _word(1, 1, 2, 2, 850, "أحمد", width=40),
            _word(1, 1, 2, 3, 895, "خالد", width=40),
        )
    )

    rows = reconstruct_rows(words)

    assert rows[0] == ["الاسم", "الهاتف"]
    assert rows[1][1] == "0990000001"
    assert "أحمد" in rows[1][0]
    assert "خالد" in rows[1][0]
    # Words inside a merged RTL cell are stored in logical reading order too.
    assert rows[1][0] == "خالد أحمد"


def test_reconstruct_rows_keeps_ltr_order_for_english_headers() -> None:
    words = parse_tsv(
        _tsv(
            _word(1, 1, 1, 1, 100, "Phone"),
            _word(1, 1, 1, 2, 250, "Name"),
            _word(1, 1, 2, 1, 100, "0990000001", width=90),
            _word(1, 1, 2, 2, 250, "Ahmad", width=60),
        )
    )

    rows = reconstruct_rows(words)

    assert rows[0] == ["Phone", "Name"]
    assert rows[1] == ["0990000001", "Ahmad"]


def test_clean_ocr_text_moves_trailing_plus_and_strips_bidi_marks() -> None:
    assert clean_ocr_text("\u200f963900000101+\u200f") == "+963900000101"
    # Regression: the normalizer must accept the same OCR token shape.
    phone = normalize_phone("963944000101+")
    assert phone.status == "ok"
    assert phone.normalized == "+963944000101"


def test_reconstruct_rows_cleans_trailing_plus_phone_cells() -> None:
    words = parse_tsv(
        _tsv(
            _word(1, 1, 1, 1, 100, "963900000101+", width=120),
        )
    )

    rows = reconstruct_rows(words)

    assert rows == [["+963900000101"]]


def test_ocr_unavailable_engine_degrades_to_scanned_warning(monkeypatch) -> None:
    monkeypatch.setattr(parsing_module, "ocr_is_available", lambda: False)

    document = parse_pdf(SCANNED_SAMPLE, mapping=None, max_pages=200)

    assert document.rows == []
    codes = [warning["code"] for warning in document.warnings]
    assert "SCANNED_PDF" in codes
    assert "OCR_USED" not in codes


def test_ocr_page_returns_none_when_tesseract_is_missing(monkeypatch) -> None:
    import app.imports.ocr as ocr_module

    monkeypatch.setattr(
        ocr_module.settings, "ocr_tesseract_cmd", "definitely-not-installed"
    )

    assert ocr_module.tesseract_path() is None
    assert ocr_module.is_available() is False
    assert ocr_page(object()) is None


def test_low_confidence_ocr_adds_warning(monkeypatch) -> None:
    fake_rows = [
        [
            "اسم ولي الأمر",
            "رقم الهاتف",
            "إجمالي القسط",
            "المدفوع",
            "المتبقي",
            "العملة",
        ],
        ["أحمد خالد", "+963944000101", "1000", "400", "600", "SYP"],
    ]
    monkeypatch.setattr(parsing_module, "ocr_is_available", lambda: True)
    monkeypatch.setattr(
        parsing_module,
        "ocr_page",
        lambda page: OcrPage(
            rows=fake_rows, text="SYP", mean_confidence=12.5
        ),
    )

    document = parse_pdf(SCANNED_SAMPLE, mapping=None, max_pages=200)

    assert len(document.rows) == 1
    codes = [warning["code"] for warning in document.warnings]
    assert "OCR_USED" in codes
    assert "LOW_CONFIDENCE_EXTRACTION" in codes
    assert "SCANNED_PDF" not in codes


@pytest.mark.skipif(
    not is_available(), reason="tesseract or ara/eng traineddata is not available"
)
def test_scanned_sample_stages_ocr_rows_for_review() -> None:
    document = parse_pdf(
        SCANNED_SAMPLE, mapping=None, max_pages=200, default_currency="SYP"
    )

    assert len(document.rows) > 0
    codes = [warning["code"] for warning in document.warnings]
    assert "OCR_USED" in codes
    assert "SCANNED_PDF" not in codes
    assert "guardian_phone" in document.mapping
    currency_header = document.mapping.get("currency")
    assert currency_header
    currencies = {
        parse_currency(row.raw_data.get(currency_header))
        for row in document.rows
    }
    assert "SYP" in currencies
    results = [
        normalize_row(inputs_from_raw(row.raw_data, document.mapping))
        for row in document.rows
    ]
    assert not all(
        any(issue.code == "MISSING_CURRENCY" for issue in result.issues)
        for result in results
    )
    # OCR is imperfect; rows must still be reviewed rather than auto-accepted.
    assert all(row.raw_data for row in document.rows)
