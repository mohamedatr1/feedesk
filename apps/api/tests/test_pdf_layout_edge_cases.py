from __future__ import annotations

from app.imports.normalization import normalize_pdf_cell, normalize_phone, parse_money
from app.imports.parsing import (
    _is_currency_value,
    _is_data_candidate,
    _is_summary_row,
    _looks_like_header_row,
)


def test_visual_order_phone_groups_are_repaired() -> None:
    assert normalize_pdf_cell("100 301 944 963+") == "+963 944 301 100"
    result = normalize_phone(normalize_pdf_cell("100 301 944 963+"))
    assert result.status == "ok"
    assert result.normalized == "+963944301100"


def test_logical_phone_is_not_reordered() -> None:
    assert normalize_pdf_cell("+963 944 301 100") == "+963 944 301 100"
    assert normalize_phone("+963 944 301 100").status == "ok"


def test_money_cell_with_currency_token_is_money_not_currency() -> None:
    assert parse_money("س.ل 620,000").status == "ok"
    assert _is_currency_value("س.ل 620,000") is False
    assert _is_currency_value("SYP") is True


def test_data_row_is_not_mistaken_for_a_header() -> None:
    row = ["س.ل 620,000", "140 301 944 963+", "عماد النعيمي"]
    assert _looks_like_header_row(row) is False


def test_arabic_and_english_summary_rows_are_detected() -> None:
    assert _is_summary_row(["SYP", "7,665,000", "", "", "", "اإلجمالي"])
    assert _is_summary_row(["Total", "", "", "", "3405.50", "USD"])
    assert _is_summary_row(["اإلجمالي / latoT"])
    assert _is_summary_row(["SYP", "2,090,000", "الإجمالي"]) is True
    assert _is_summary_row(["ريم النعيمي", "+963 944 301 100", "750,000", "SYP"]) is False
    # A real surname can end with the same letters as "إجمالي"; the phone
    # keeps the row from being mistaken for a total.
    assert (
        _is_summary_row(
            ["أحمد الجمالي", "+963 944 301 100", "750,000", "SYP"]
        )
        is False
    )


def test_titles_and_summary_rows_are_not_data_candidates() -> None:
    assert _is_data_candidate(["كشف أقساط الفصل الأول"]) is False
    assert _is_data_candidate(["SYP", "7,665,000", "", "", "", "اإلجمالي"]) is False
    assert (
        _is_data_candidate(
            ["ريم النعيمي", "+963 944 301 100", "750,000", "SYP"]
        )
        is True
    )
