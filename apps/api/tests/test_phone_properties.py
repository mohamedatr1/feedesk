from __future__ import annotations

import unicodedata

import phonenumbers
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.imports.normalization import normalize_phone

_LATIN_DIGITS = "0123456789"
_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_DIGIT_TRANSLATION = str.maketrans(_LATIN_DIGITS, _ARABIC_INDIC_DIGITS)
_VALID_MOBILE_PREFIXES = ("91", "93", "94", "95", "96", "98", "99")


def _to_arabic_indic(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION)


def _is_valid(number: str) -> bool:
    try:
        return phonenumbers.is_valid_number(phonenumbers.parse(number, "SY"))
    except phonenumbers.NumberParseException:
        return False


@st.composite
def _valid_syrian_e164(draw: st.DrawFn) -> str:
    prefix = draw(st.sampled_from(_VALID_MOBILE_PREFIXES))
    suffix = draw(st.integers(min_value=0, max_value=9_999_999))
    number = f"+963{prefix}{suffix:07d}"
    assume(_is_valid(number))
    return number


@st.composite
def _truncated_number(draw: st.DrawFn) -> str:
    number = draw(_valid_syrian_e164())
    dropped = draw(st.integers(min_value=1, max_value=5))
    truncated = number[:-dropped]
    assume(not _is_valid(truncated))
    return truncated


@st.composite
def _short_or_garbage_number(draw: st.DrawFn) -> str:
    kind = draw(st.integers(min_value=0, max_value=3))
    if kind == 0:
        return draw(st.text(alphabet=_LATIN_DIGITS, min_size=1, max_size=5))
    if kind == 1:
        return "+963" + draw(st.text(alphabet=_LATIN_DIGITS, min_size=0, max_size=4))
    if kind == 2:
        return draw(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz ABC-؟!",
                min_size=1,
                max_size=12,
            )
        )
    return draw(st.sampled_from(["", "  ", "+", "++963990000011", "00963"]))


@settings(max_examples=100, deadline=None)
@given(number=_valid_syrian_e164())
def test_valid_syrian_e164_round_trips(number: str) -> None:
    result = normalize_phone(number)

    assert result.status == "ok"
    assert result.normalized == number
    assert result.original == number


@settings(max_examples=100, deadline=None)
@given(number=_valid_syrian_e164())
def test_arabic_indic_digits_normalize_equivalently(number: str) -> None:
    arabic = _to_arabic_indic(number)

    latin_result = normalize_phone(number)
    arabic_result = normalize_phone(arabic)

    assert latin_result.status == "ok"
    assert arabic_result.status == "ok"
    assert latin_result.normalized == number
    assert arabic_result.normalized == number
    assert arabic_result.original == arabic


@settings(max_examples=100, deadline=None)
@given(number=_valid_syrian_e164())
def test_spacing_and_dashes_do_not_change_the_e164_value(number: str) -> None:
    formatted = f"{number[:4]} {number[4:6]}-{number[6:]}"

    result = normalize_phone(formatted)

    assert result.status == "ok"
    assert result.normalized == number
    assert result.original == formatted


@settings(max_examples=100, deadline=None)
@given(truncated=_truncated_number())
def test_truncated_numbers_stay_invalid_and_never_become_another_valid_number(
    truncated: str,
) -> None:
    result = normalize_phone(truncated)

    assert result.status == "invalid"
    assert result.original == truncated
    assert result.normalized is None or not _is_valid(result.normalized)


@settings(max_examples=100, deadline=None)
@given(value=_short_or_garbage_number())
def test_short_and_garbage_inputs_stay_invalid(value: str) -> None:
    result = normalize_phone(value)

    assert result.status in {"invalid", "missing"}
    assert result.normalized is None or not _is_valid(result.normalized)


@settings(max_examples=100, deadline=None)
@given(
    value=st.one_of(
        st.none(),
        _valid_syrian_e164(),
        _valid_syrian_e164().map(_to_arabic_indic),
        _short_or_garbage_number(),
    )
)
def test_original_phone_is_preserved_for_every_non_none_input(
    value: str | None,
) -> None:
    result = normalize_phone(value)

    if value is None:
        assert result.status == "missing"
        assert result.original == ""
    else:
        assert result.original == unicodedata.normalize("NFKC", str(value)).strip()
