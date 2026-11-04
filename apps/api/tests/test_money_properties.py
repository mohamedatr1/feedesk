from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.imports.normalization import money_to_string, parse_money

_LATIN_DIGITS = "0123456789"
_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_DIGIT_TRANSLATION = str.maketrans(_LATIN_DIGITS, _ARABIC_INDIC_DIGITS)
_CENT = Decimal("0.01")


def _to_arabic_indic(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION)


def _group_thousands(whole: int) -> str:
    """Render a non-negative integer with conventional comma grouping."""
    digits = str(whole)
    head = len(digits) % 3 or 3
    parts = [digits[:head]]
    parts.extend(digits[index : index + 3] for index in range(head, len(digits), 3))
    return ",".join(parts)


@st.composite
def _money_cases(draw: st.DrawFn, *, include_arabic: bool = True) -> tuple[str, Decimal]:
    """Yield (source text, exact mathematical value) for accepted formats.

    All generated values stay within the 15-digit limit enforced by parse_money.
    """
    style = draw(st.integers(min_value=0, max_value=5 if include_arabic else 4))
    if style == 0:
        whole = draw(st.integers(min_value=0, max_value=10**15 - 1))
        text = str(whole)
        fraction = 0
    elif style == 1:
        whole = draw(st.integers(min_value=0, max_value=10**15 - 1))
        text = _group_thousands(whole)
        fraction = 0
    else:
        # 13 whole digits + 2 fraction digits keeps the total at most 15.
        whole = draw(st.integers(min_value=0, max_value=10**13 - 1))
        fraction = draw(st.integers(min_value=0, max_value=99))
        if style == 2:
            text = f"{whole}.{fraction:02d}"
        elif style == 3:
            text = f"{_group_thousands(whole)}.{fraction:02d}"
        elif style == 4:
            # Comma as the decimal separator; the fraction is always 2 digits,
            # so this is never mistaken for a thousands group.
            text = f"{whole},{fraction:02d}"
        else:
            text = _to_arabic_indic(f"{_group_thousands(whole)}.{fraction:02d}")
            text = text.replace(",", "\u066c").replace(".", "\u066b")
    expected = Decimal(f"{whole}.{fraction:02d}")
    return text, expected


@st.composite
def _ambiguous_money(draw: st.DrawFn) -> str:
    """Generate inputs that must not silently turn into a numeric amount."""
    kind = draw(st.integers(min_value=0, max_value=5))
    if kind == 0:
        # A single 3-digit group after a dot could be a thousands group or a
        # fraction with more than two digits: 1.250 is deliberately ambiguous.
        return f"{draw(st.integers(0, 10**12))}.{draw(st.integers(100, 999)):03d}"
    if kind == 1:
        # More than two digits after a comma that is not a valid group.
        return f"{draw(st.integers(0, 10**12))},{draw(st.integers(1000, 9999))}"
    if kind == 2:
        # Several dot-separated groups where the middle group is not 3 digits.
        return (
            f"{draw(st.integers(0, 10**3))}."
            f"{draw(st.integers(1000, 9999))}."
            f"{draw(st.integers(0, 10**3))}"
        )
    if kind == 3:
        noise = draw(st.sampled_from(["x", "abc", "؟", "!", "/", "+"]))
        return f"{draw(st.integers(0, 10**6))}{noise}{draw(st.integers(0, 10**3))}"
    if kind == 4:
        # Currency-only cells have no numeric amount at all.
        return draw(st.sampled_from(["", "   ", "ل.س", "SYP", "$", "€"]))
    # Exceeds the documented 15-digit limit instead of being truncated.
    return "9" * draw(st.integers(min_value=16, max_value=30))


@settings(max_examples=100, deadline=None)
@given(case=_money_cases())
def test_parse_money_is_exact_and_never_uses_binary_float(
    case: tuple[str, Decimal],
) -> None:
    text, expected = case

    result = parse_money(text)

    assert result.status == "ok"
    assert isinstance(result.value, Decimal)
    assert result.value == expected
    # Same exponent and digits: the value is the exact cent amount, not a
    # float-rounded approximation.
    assert result.value.as_tuple() == expected.as_tuple()
    assert money_to_string(result.value) == format(expected, "f")

    binary_expansion = Decimal(float(expected))
    if binary_expansion != expected:
        # The binary-float representation of the same value differs; the
        # parser must keep the exact decimal rather than round-tripping it.
        assert result.value != binary_expansion


@settings(max_examples=100, deadline=None)
@given(case=_money_cases())
def test_money_to_string_preserves_the_mathematical_value(
    case: tuple[str, Decimal],
) -> None:
    text, expected = case

    parsed = parse_money(text)
    serialized = money_to_string(parsed.value)

    assert serialized is not None
    assert Decimal(serialized) == expected
    assert Decimal(serialized).quantize(_CENT) == expected
    # Re-parsing is only possible while the two-decimal rendering stays inside
    # the documented 15-digit cap; larger accepted integers exceed it once the
    # ".00" suffix is added.
    if len(expected.as_tuple().digits) <= 15:
        assert money_to_string(parse_money(serialized).value) == serialized


@settings(max_examples=100, deadline=None)
@given(case=_money_cases(include_arabic=False))
def test_arabic_indic_and_latin_digits_produce_the_same_amount(
    case: tuple[str, Decimal],
) -> None:
    latin, expected = case
    arabic = _to_arabic_indic(latin)

    latin_result = parse_money(latin)
    arabic_result = parse_money(arabic)

    assert latin_result.status == "ok"
    assert arabic_result.status == "ok"
    assert latin_result.value == expected
    assert arabic_result.value == expected
    assert latin_result.value == arabic_result.value


@settings(max_examples=100, deadline=None)
@given(text=_ambiguous_money())
def test_invalid_or_ambiguous_input_never_becomes_a_numeric_amount(text: str) -> None:
    result = parse_money(text)

    assert result.value is None
    assert result.status in {"ambiguous", "empty"}


@settings(max_examples=100, deadline=None)
@given(case=_money_cases(include_arabic=False))
def test_negative_forms_negate_the_amount(case: tuple[str, Decimal]) -> None:
    text, expected = case

    assert parse_money(f"-{text}").value == -expected
    assert parse_money(f"({text})").value == -expected
    assert parse_money(f"{text}-").value == -expected
    # Two negative markers cancel out, matching the existing contract.
    assert parse_money(f"-{text}-").value == expected


@settings(max_examples=100, deadline=None)
@given(raw=st.sampled_from(["0", "00", "+0", "0.0", "0.00", "0,0", "0,00", "(0)", "-0"]))
def test_zero_forms_are_ok_and_serialize_to_zero(raw: str) -> None:
    result = parse_money(raw)

    assert result.status == "ok"
    assert result.value == Decimal("0.00")
    assert money_to_string(result.value) == "0.00"
