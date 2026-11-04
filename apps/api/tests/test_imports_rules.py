from __future__ import annotations

from decimal import Decimal

from app.imports.normalization import (
    auto_suggest_mapping,
    detect_currency,
    normalize_phone,
    parse_currency,
    parse_money,
)
from app.imports.validation import normalize_row


def test_parse_money_arabic_indic_and_suffixes() -> None:
    result = parse_money("٧٥٠٬٠٠٠ ل.س")
    assert result.status == "ok"
    assert result.value == Decimal("750000.00")

    arabic_digits = parse_money("١٢٣٤٥٦")
    assert arabic_digits.value == Decimal("123456.00")


def test_parse_money_separator_conventions() -> None:
    assert parse_money("1,250,000.50").value == Decimal("1250000.50")
    assert parse_money("1.250.000,50").value == Decimal("1250000.50")
    assert parse_money("100,000-").value == Decimal("-100000.00")
    assert parse_money("-100000").value == Decimal("-100000.00")
    assert parse_money("(500.00)").value == Decimal("-500.00")
    assert parse_money("1,250").value == Decimal("1250.00")


def test_parse_money_ambiguous_separator_is_not_guessed() -> None:
    ambiguous = parse_money("1.250")
    assert ambiguous.status == "ambiguous"
    assert ambiguous.value is None

    assert parse_money("").status == "empty"
    assert parse_money("abc").status == "ambiguous"


def test_parse_currency_aliases() -> None:
    assert parse_currency("ل.س") == "SYP"
    assert parse_currency("د.س") == "SYP"
    assert parse_currency("usd") == "USD"
    assert parse_currency("$") == "USD"
    assert parse_currency("") is None
    assert parse_currency("gbp") == "GBP"
    # Arbitrary three-letter tokens are OCR noise, not currency codes.
    assert parse_currency("xyz") is None
    assert parse_currency("Uso") is None


def test_detect_currency_from_free_text() -> None:
    assert (
        detect_currency("العام الدراسي 2026–2027 | العملة: ليرة سورية (ل.س)")
        == "SYP"
    )
    assert detect_currency("Remaining total in USD") == "USD"
    assert detect_currency("المبلغ بالدولار") == "USD"
    assert detect_currency("كشف أقساط مدرسة") is None


def test_phone_normalization_preserves_original() -> None:
    valid = normalize_phone("٠٩٩٠٠٠٠٠١١")
    assert valid.status == "ok"
    assert valid.original == "٠٩٩٠٠٠٠٠١١"
    assert valid.normalized == "+963990000011"

    international = normalize_phone("00963990000011")
    assert international.normalized == "+963990000011"

    invalid = normalize_phone("+963900000001")
    assert invalid.status == "invalid"
    assert invalid.normalized == "+963900000001"

    missing = normalize_phone(None)
    assert missing.status == "missing"
    assert missing.original == ""


def test_auto_mapping_matches_arabic_and_english_headers() -> None:
    headers = [
        "اسم ولي الأمر",
        "الجوال",
        "اسم الطالب",
        "المطلوب",
        "الواصل",
        "الباقي",
        "العملة",
        "الفصل",
    ]
    mapping = auto_suggest_mapping(headers)
    assert mapping["guardian_name"] == "اسم ولي الأمر"
    assert mapping["guardian_phone"] == "الجوال"
    assert mapping["student_name"] == "اسم الطالب"
    assert mapping["total_fee"] == "المطلوب"
    assert mapping["amount_paid"] == "الواصل"
    assert mapping["remaining_balance"] == "الباقي"
    assert mapping["currency"] == "العملة"
    assert mapping["fee_period"] == "الفصل"

    english = auto_suggest_mapping(["Guardian", "Phone", "Remaining", "Currency"])
    assert english["guardian_name"] == "Guardian"
    assert english["guardian_phone"] == "Phone"
    assert english["remaining_balance"] == "Remaining"


def test_normalize_row_blocks_missing_required_fields() -> None:
    result = normalize_row({})
    codes = {item.code for item in result.issues}
    assert {"MISSING_GUARDIAN", "MISSING_BALANCE", "MISSING_CURRENCY"} <= codes
    assert result.data["is_eligible"] is False


def test_normalize_row_zero_balance_warns_and_blocks_eligibility() -> None:
    result = normalize_row(
        {
            "guardian_name": "ولي أمر",
            "guardian_phone": "0990000011",
            "remaining_balance": "0",
            "currency": "SYP",
        }
    )
    codes = {item.code for item in result.issues}
    assert "ZERO_BALANCE" in codes
    assert result.data["remaining_balance"] == "0.00"
    assert result.data["is_eligible"] is False


def test_normalize_row_negative_balance_is_error() -> None:
    result = normalize_row(
        {
            "guardian_name": "ولي أمر",
            "guardian_phone": "0990000011",
            "remaining_balance": "-100",
            "currency": "SYP",
        }
    )
    assert any(
        item.code == "NEGATIVE_BALANCE" and item.severity == "error"
        for item in result.issues
    )


def test_normalize_row_total_discrepancy_keeps_source_balance() -> None:
    result = normalize_row(
        {
            "guardian_name": "ولي أمر",
            "guardian_phone": "0990000011",
            "total_fee": "1000",
            "amount_paid": "400",
            "remaining_balance": "550",
            "currency": "SYP",
        }
    )
    assert result.data["remaining_balance"] == "550.00"
    assert result.data["remaining_balance_calculated"] == "600.00"
    assert any(item.code == "TOTAL_DISCREPANCY" for item in result.issues)
    assert result.data["is_eligible"] is True


def test_normalize_row_invalid_phone_is_warning_but_record_retained() -> None:
    result = normalize_row(
        {
            "guardian_name": "ولي أمر",
            "guardian_phone": "+963900000001",
            "remaining_balance": "100",
            "currency": "SYP",
        }
    )
    assert any(item.code == "INVALID_PHONE" for item in result.issues)
    assert result.data["remaining_balance"] == "100.00"
    assert result.data["is_eligible"] is False
