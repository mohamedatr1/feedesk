from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from app.imports import parsing as parsing_module
from app.imports.ocr import is_available as ocr_is_available
from app.imports.parsing import _pdf_word_rows, parse_pdf, parse_xlsx
from app.imports.validation import inputs_from_raw, normalize_row

FIXTURES = Path(__file__).resolve().parent / "fixtures"
XLSX_SAMPLES = FIXTURES / "xlsx"
PDF_SAMPLES = FIXTURES / "pdf"

REAL_SAMPLES = Path(__file__).resolve().parents[3] / ".local" / "samples" / "real"
REAL_XLSX = REAL_SAMPLES / "xlsx" / "FeeDesk_Sample_Fee_Statement.xlsx"
REAL_PDF = REAL_SAMPLES / "pdf" / "FeeDesk_Sample_Fee_Statement.pdf"
_NEEDS_REAL_SAMPLES = pytest.mark.skipif(
    not (REAL_XLSX.is_file() and REAL_PDF.is_file()),
    reason="real sample statements are not available",
)


def test_xlsx_multi_sheet_auto_selects_statement_sheet() -> None:
    document = parse_xlsx(
        XLSX_SAMPLES / "sample-01-multi-sheet.xlsx",
        worksheet_name=None,
        mapping=None,
        max_rows=5000,
    )

    assert document.available_sheets == ["الفصل الأول", "الفصل الثاني"]
    assert document.worksheet_name == "الفصل الأول"
    assert len(document.rows) == 7
    assert any(
        warning["code"] == "SHEET_AUTO_SELECTED"
        and warning["details"]["worksheet_name"] == "الفصل الأول"
        for warning in document.warnings
    )


def test_xlsx_arabic_digits_and_header_detection() -> None:
    document = parse_xlsx(
        XLSX_SAMPLES / "sample-02-arabic-digits.xlsx",
        worksheet_name=None,
        mapping=None,
        max_rows=5000,
    )

    assert document.worksheet_name == "بيانات"
    assert document.mapping["guardian_name"] == "الاسم"
    assert document.mapping["guardian_phone"] == "الموبايل"
    assert document.mapping["remaining_balance"] == "الباقي"
    assert len(document.rows) == 4
    assert document.rows[0].source_row_number == 5
    assert document.rows[0].raw_data["الاسم"] == "ولي أمر تجريبي 011"
    assert document.rows[0].raw_data["الموبايل"] == "٠٩٩٠٠٠٠٠١١"
    assert document.rows[0].raw_data["الباقي"] == "٧٣٤٥٦"


def test_xlsx_messy_headers_skip_blank_rows_and_detect_header() -> None:
    document = parse_xlsx(
        XLSX_SAMPLES / "sample-03-messy-headers.xlsx",
        worksheet_name="كشف ملخبط",
        mapping=None,
        max_rows=5000,
    )

    assert document.mapping["guardian_name"] == "اسم الولي"
    assert document.mapping["guardian_phone"] == "الجوال"
    assert document.mapping["remaining_balance"] == "الرصيد"
    assert len(document.rows) == 4
    assert [row.source_row_number for row in document.rows] == [7, 8, 9, 10]
    assert document.rows[0].raw_data["المسدد"] == "1,250,000.50"
    assert document.rows[1].raw_data["المسدد"] == "1.250.000,50"


def test_xlsx_empty_sheet_returns_warning_not_rows() -> None:
    document = parse_xlsx(
        XLSX_SAMPLES / "sample-03-messy-headers.xlsx",
        worksheet_name="ورقة فارغة",
        mapping=None,
        max_rows=5000,
    )

    assert document.rows == []
    assert any(warning["code"] == "SHEET_EMPTY" for warning in document.warnings)


def test_xlsx_merged_guardian_cells_and_uncached_formulas(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "الطلاب"
    sheet["A1"] = "كشف أقساط"
    sheet.merge_cells("A1:F1")
    headers = [
        "اسم ولي الأمر",
        "رقم الهاتف",
        "إجمالي القسط",
        "المدفوع",
        "المتبقي",
        "العملة",
    ]
    sheet.append(headers)
    sheet.append(["ولي أمر مدمج", "0990000011", 1000, 400, "=C3-D3", "SYP"])
    sheet.append(["ولي أمر مدمج", "0990000012", 1000, 400, 600, "SYP"])
    sheet.merge_cells("A4:A5")
    sheet.append([None, "0990000013", 500, 100, 400, "USD"])
    path = tmp_path / "merged-formula.xlsx"
    workbook.save(path)

    document = parse_xlsx(
        path, worksheet_name="الطلاب", mapping=None, max_rows=5000
    )

    assert len(document.rows) == 3
    assert document.rows[0].warnings[0]["code"] == "FORMULA_WITHOUT_CACHED_VALUE"
    assert document.rows[0].raw_data["المتبقي"] is None
    assert document.rows[1].raw_data["اسم ولي الأمر"] == "ولي أمر مدمج"
    # Merged A4:A5 forwards the top-left guardian value to the sibling row.
    assert document.rows[2].raw_data["اسم ولي الأمر"] == "ولي أمر مدمج"
    assert document.rows[2].raw_data["العملة"] == "USD"


def test_pdf_text_table_extraction_preserves_page_refs() -> None:
    document = parse_pdf(
        PDF_SAMPLES / "sample-01-text-table.pdf", mapping=None, max_pages=200
    )

    assert document.mapping["guardian_name"]
    assert document.mapping["guardian_phone"]
    assert document.mapping["remaining_balance"]
    assert len(document.rows) == 6
    assert {row.source_page_number for row in document.rows} == {1}
    first = document.rows[0].raw_data
    assert "ولي أمر" in first[document.mapping["guardian_name"]]
    assert first[document.mapping["guardian_phone"]] == "+963900000101"
    assert document.rows[4].raw_data[document.mapping["remaining_balance"]] == "100,000-"


class _FakeWordPage:
    def __init__(self, words: list[dict[str, object]]) -> None:
        self._words = words

    def extract_words(self) -> list[dict[str, object]]:
        return self._words


def test_pdf_word_positions_recover_columns_from_single_column_text() -> None:
    page = _FakeWordPage(
        [
            {"text": "أحمد", "x0": 10, "x1": 30, "top": 10, "height": 8},
            {"text": "خالد", "x0": 35, "x1": 60, "top": 10, "height": 8},
            {"text": "الهاتف", "x0": 100, "x1": 135, "top": 10, "height": 8},
            {"text": "+963944000101", "x0": 10, "x1": 90, "top": 25, "height": 8},
            {"text": "0990000102", "x0": 100, "x1": 165, "top": 25, "height": 8},
        ]
    )

    rows = _pdf_word_rows(page)

    assert rows[0] == ["أحمد خالد", "الهاتف"]
    assert rows[1] == ["+963944000101", "0990000102"]


def test_pdf_scanned_page_reports_scanned_when_ocr_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(parsing_module.settings, "ocr_enabled", False)

    document = parse_pdf(
        PDF_SAMPLES / "sample-02-scanned-image.pdf", mapping=None, max_pages=200
    )

    assert document.rows == []
    codes = [warning["code"] for warning in document.warnings]
    assert "SCANNED_PDF" in codes
    assert "OCR_USED" not in codes


@pytest.mark.skipif(
    not ocr_is_available(), reason="tesseract or ara/eng traineddata is not available"
)
def test_pdf_scanned_page_uses_assisted_ocr() -> None:
    document = parse_pdf(
        PDF_SAMPLES / "sample-02-scanned-image.pdf", mapping=None, max_pages=200
    )

    assert document.rows
    codes = [warning["code"] for warning in document.warnings]
    assert "OCR_USED" in codes
    assert "SCANNED_PDF" not in codes


@_NEEDS_REAL_SAMPLES
def test_real_xlsx_auto_selects_statement_sheet_and_infers_currency() -> None:
    document = parse_xlsx(
        REAL_XLSX,
        worksheet_name=None,
        mapping=None,
        max_rows=5000,
        default_currency="SYP",
    )

    assert document.worksheet_name == "كشف الأقساط"
    assert document.available_sheets == [
        "كشف الأقساط",
        "جهات الاتصال",
        "ملاحظات الاستيراد",
    ]
    assert len(document.rows) == 18
    assert document.rows[0].source_row_number == 4
    assert document.mapping["guardian_name"] == "اسم ولي الأمر"
    assert document.mapping["guardian_phone"] == "رقم الهاتف"
    assert document.mapping["remaining_balance"] == "المبلغ المتبقي (ل.س)"
    assert document.mapping["currency"].startswith("العملة")
    assert all(
        row.raw_data[document.mapping["currency"]] == "SYP"
        for row in document.rows
    )
    assert any(
        warning["code"] == "SHEET_AUTO_SELECTED"
        and warning["details"]["worksheet_name"] == "كشف الأقساط"
        for warning in document.warnings
    )


@_NEEDS_REAL_SAMPLES
def test_real_pdf_stages_rows_with_inferred_currency() -> None:
    document = parse_pdf(
        REAL_PDF, mapping=None, max_pages=200, default_currency="SYP"
    )

    assert len(document.rows) == 18
    assert document.mapping["guardian_name"] == "ولي الأمر"
    assert document.mapping["guardian_phone"] == "الهاتف"
    assert document.mapping["remaining_balance"] == "المتبقي"
    assert document.mapping["currency"].startswith("العملة")

    for row in document.rows:
        result = normalize_row(inputs_from_raw(row.raw_data, document.mapping))
        assert result.data["currency"] == "SYP"
        assert not any(
            issue.code == "MISSING_CURRENCY" for issue in result.issues
        )


def test_xlsx_headerless_sheet_uses_value_heuristics(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "بيانات"
    sheet.append(["أحمد خالد الحسن", "+963 944 000 101", 900000])
    sheet.append(["سمر محمود العلي", "+963 944 000 102", 1500000])
    sheet.append(["محمد ناصر الدرويش", "0990000103", 400000])
    path = tmp_path / "headerless.xlsx"
    workbook.save(path)

    document = parse_xlsx(
        path, worksheet_name=None, mapping=None, max_rows=5000
    )

    assert document.worksheet_name == "بيانات"
    assert len(document.rows) == 3
    assert document.mapping["guardian_name"] == "عمود 1"
    assert document.mapping["guardian_phone"] == "عمود 2"
    assert document.mapping["remaining_balance"] == "عمود 3"
    assert any(
        warning["code"] == "HEADER_NOT_FOUND"
        and warning["severity"] == "warning"
        for warning in document.warnings
    )


def test_xlsx_custom_multi_sheet_picks_statement_sheet(tmp_path: Path) -> None:
    workbook = Workbook()
    statement = workbook.active
    statement.title = "الكشف"
    statement.append(["اسم ولي الأمر", "رقم الهاتف", "المتبقي", "العملة"])
    statement.append(["أحمد خالد الحسن", "+963 944 000 101", 900000, "SYP"])
    statement.append(["سمر محمود العلي", "+963 944 000 102", 1500000, "SYP"])
    notes = workbook.create_sheet("ملاحظات")
    notes.append(["ملاحظة"])
    notes.append(["هذه ورقة ملاحظات فقط"])
    path = tmp_path / "custom-multi.xlsx"
    workbook.save(path)

    document = parse_xlsx(
        path, worksheet_name=None, mapping=None, max_rows=5000
    )

    assert document.worksheet_name == "الكشف"
    assert document.available_sheets == ["الكشف", "ملاحظات"]
    assert len(document.rows) == 2
    assert any(
        warning["code"] == "SHEET_AUTO_SELECTED" for warning in document.warnings
    )


def test_xlsx_explicit_sheet_selection_still_works() -> None:
    document = parse_xlsx(
        XLSX_SAMPLES / "sample-01-multi-sheet.xlsx",
        worksheet_name="الفصل الثاني",
        mapping=None,
        max_rows=5000,
    )

    assert document.worksheet_name == "الفصل الثاني"
    assert len(document.rows) == 3
    assert not any(
        warning["code"] == "SHEET_AUTO_SELECTED" for warning in document.warnings
    )


def test_xlsx_currency_column_values_win_over_document_inference(
    tmp_path: Path,
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "الكشف"
    sheet.append(["كشف العملة: ليرة سورية (ل.س)"])
    sheet.append(["اسم ولي الأمر", "رقم الهاتف", "المتبقي", "العملة"])
    sheet.append(["أحمد خالد الحسن", "+963 944 000 101", 900000, "USD"])
    sheet.append(["سمر محمود العلي", "+963 944 000 102", 1500000, None])
    path = tmp_path / "currency-wins.xlsx"
    workbook.save(path)

    document = parse_xlsx(
        path, worksheet_name=None, mapping=None, max_rows=5000
    )

    assert document.mapping["currency"] == "العملة"
    assert document.rows[0].raw_data["العملة"] == "USD"
    # Empty currency cells fall back to the currency detected in the title.
    assert document.rows[1].raw_data["العملة"] == "SYP"


def test_xlsx_default_currency_fallback_warns(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "الكشف"
    sheet.append(["اسم ولي الأمر", "رقم الهاتف", "المتبقي"])
    sheet.append(["أحمد خالد الحسن", "+963 944 000 101", 900000])
    path = tmp_path / "school-currency.xlsx"
    workbook.save(path)

    document = parse_xlsx(
        path,
        worksheet_name=None,
        mapping=None,
        max_rows=5000,
        default_currency="USD",
    )

    currency_header = document.mapping["currency"]
    assert currency_header.startswith("العملة")
    assert document.rows[0].raw_data[currency_header] == "USD"
    assert any(
        warning["code"] == "CURRENCY_FROM_SCHOOL_SETTINGS"
        for warning in document.warnings
    )

    # Re-processing with the previously returned mapping must not reject the
    # synthetic currency header, which is not a real workbook column.
    again = parse_xlsx(
        path,
        worksheet_name=None,
        mapping={"currency": currency_header},
        max_rows=5000,
        default_currency="USD",
    )
    assert again.mapping["currency"].startswith("العملة")
    assert again.rows[0].raw_data[again.mapping["currency"]] == "USD"
