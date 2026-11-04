from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import phonenumbers

from .constants import MESSAGES_AR, SYNONYMS
from .errors import ImportIssue

ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
EXTENDED_ARABIC_INDIC = "۰۱۲۳۴۵۶۷۸۹"
_ASCII_DIGITS = "0123456789" * 2
_DIGIT_TABLE = str.maketrans(
    ARABIC_INDIC + EXTENDED_ARABIC_INDIC, _ASCII_DIGITS
)

_TATWEEL_AND_DIACRITICS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)
_PRESENTATION_FORMS = re.compile("[\ufb50-\ufdff\ufe70-\ufeff]")

_CURRENCY_TOKEN = re.compile(
    r"(?:ل\s*\.?\s*س|س\s*\.?\s*ل|د\s*\.?\s*س|س\s*\.?\s*د|"
    r"ر\s*\.?\s*س|س\s*\.?\s*ر|SYP|USD|EUR|SAR|AED|"
    r"ليرة|ليره|دولار|ريال|درهم|\$|€)",
    re.IGNORECASE,
)

# Free-text detection needs word boundaries; otherwise the "رس" inside words
# such as "مدرسة" or "الرسوم" is mistaken for the SAR symbol.
_CURRENCY_DETECT_TOKEN = re.compile(
    r"(?<![A-Za-z\u0600-\u06FF])(?:"
    r"ل\s*\.?\s*س|س\s*\.?\s*ل|د\s*\.?\s*س|س\s*\.?\s*د|"
    r"ر\s*\.?\s*س|SYP|USD|EUR|SAR|AED|"
    r"ليرة|ليره|دولار|ريال|درهم|\$|€"
    r")(?![A-Za-z\u0600-\u06FF])",
    re.IGNORECASE,
)

# Arabic currency words can carry prefixes such as "بالدولار" or "لليرة", so
# match these multi-letter words even when they are not standalone tokens.
_CURRENCY_WORD_TOKEN = re.compile(
    r"(?:ليرة|ليره|دولار|ريال|درهم)", re.IGNORECASE
)

_CURRENCY_MAP: dict[str, str] = {
    "syp": "SYP",
    "ل.س": "SYP",
    "ل.س.": "SYP",
    "س.ل": "SYP",
    "س.ل.": "SYP",
    "ليره": "SYP",
    "ليرة": "SYP",
    "د.س": "SYP",
    "س.د": "SYP",
    "usd": "USD",
    "$": "USD",
    "us$": "USD",
    "دولار": "USD",
    "eur": "EUR",
    "€": "EUR",
    "sar": "SAR",
    "ر.س": "SAR",
    "aed": "AED",
    "درهم": "AED",
}

# Only real ISO currency codes are accepted as bare three-letter tokens.  Any
# three letters used to pass, which turned OCR noise such as ``Uso`` into a
# fake currency code.
_ISO_CURRENCIES: frozenset[str] = frozenset(
    {
        "SYP",
        "USD",
        "EUR",
        "SAR",
        "AED",
        "GBP",
        "TRY",
        "JOD",
        "LBP",
        "IQD",
        "KWD",
        "QAR",
        "OMR",
        "BHD",
        "EGP",
        "CAD",
        "AUD",
        "JPY",
        "CNY",
        "INR",
        "RUB",
    }
)

_ZERO = Decimal("0")
_CENT = Decimal("0.01")
_MAX_MONEY_DIGITS = 15


def convert_digits(value: str) -> str:
    """Convert Arabic-Indic and Extended Arabic-Indic digits to ASCII."""
    return value.translate(_DIGIT_TABLE)


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def strip_arabic_marks(value: str) -> str:
    return _TATWEEL_AND_DIACRITICS.sub("", value)


def unify_arabic_letters(value: str) -> str:
    for source, target in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ٱ", "ا"),
        ("ى", "ي"),
        ("ئ", "ي"),
        ("ؤ", "و"),
        ("ة", "ه"),
        ("ی", "ي"),
        ("ک", "ك"),
        ("ھ", "ه"),
        ("ۀ", "ه"),
        ("ہ", "ه"),
    ):
        value = value.replace(source, target)
    return value


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = normalize_unicode(str(value))
    text = convert_digits(text)
    return re.sub(r"\s+", " ", text).strip()


def _repair_visual_phone(text: str) -> str:
    """Restore RTL visual-order phone groups such as ``140 301 944 963+``.

    Arabic statement cells are commonly emitted right-to-left, so the country
    prefix and digit groups arrive mirrored.  Only all-numeric multi-group
    cells are touched; names, money and already-logical numbers are unchanged.
    """
    tokens = text.split()
    if len(tokens) < 3:
        return text
    if not all(re.fullmatch(r"\d{1,5}\+?", token) for token in tokens):
        return text
    if tokens[-1].endswith("+"):
        groups = [token.rstrip("+") for token in reversed(tokens)]
        return "+" + " ".join(groups)
    reversed_text = " ".join(reversed(tokens))
    if (
        normalize_phone(text).status != "ok"
        and normalize_phone(reversed_text).status == "ok"
    ):
        return reversed_text
    return text


def normalize_pdf_cell(value: object) -> str:
    """Normalize a pdfplumber text cell.

    Chromium-generated Arabic PDFs expose Arabic presentation forms in visual
    order.  NFKC maps the forms back to base letters, then the string is
    reversed to restore logical reading order.  Numeric cells have no
    presentation forms, so their mirrored phone groups are repaired
    separately.
    """
    if value is None:
        return ""
    raw = str(value)
    reversed_visual = bool(_PRESENTATION_FORMS.search(raw))
    text = normalize_unicode(raw)
    if reversed_visual:
        text = text[::-1]
    text = convert_digits(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not reversed_visual:
        text = _repair_visual_phone(text)
    return text


def header_key(value: object) -> str:
    text = normalize_unicode(clean_text(value))
    text = strip_arabic_marks(text)
    text = unify_arabic_letters(text)
    tokens = []
    for token in re.split(r"[\s_\-/.:،,()\[\]{}]+", text):
        token = token.strip()
        if not token:
            continue
        if token.startswith("ال") and len(token) > 3:
            token = token[2:]
        tokens.append(token)
    text = "".join(tokens).casefold()
    return re.sub(r"[^0-9a-z\u0621-\u064a]", "", text)


_SYNONYM_KEYS: dict[str, tuple[str, ...]] = {
    canonical: tuple(header_key(item) for item in values)
    for canonical, values in SYNONYMS.items()
}


def normalize_name_key(value: object) -> str:
    text = normalize_unicode(clean_text(value))
    text = strip_arabic_marks(text)
    text = unify_arabic_letters(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def auto_suggest_mapping(headers: list[str]) -> dict[str, str]:
    """Suggest canonical field -> source header using Arabic/English synonyms."""
    resolved: dict[str, str] = {}
    used: set[int] = set()
    keys = [(index, header_key(header)) for index, header in enumerate(headers)]

    for canonical, synonyms in _SYNONYM_KEYS.items():
        for index, key in keys:
            if index in used or not key:
                continue
            if key in synonyms:
                resolved[canonical] = headers[index]
                used.add(index)
                break

    for canonical, synonyms in _SYNONYM_KEYS.items():
        if canonical in resolved:
            continue
        for index, key in keys:
            if index in used or len(key) < 5:
                continue
            if any(
                (len(synonym) >= 5 and synonym in key) or (len(key) >= 5 and key in synonym)
                for synonym in synonyms
            ):
                resolved[canonical] = headers[index]
                used.add(index)
                break
    return resolved


def resolve_mapping(
    headers: list[str],
    provided: dict[str, str] | None,
) -> dict[str, str]:
    """Merge manual mapping over auto suggestions, validating each header."""
    resolved = auto_suggest_mapping(headers)
    if not provided:
        return resolved

    header_by_key: dict[str, str] = {}
    for header in headers:
        header_by_key.setdefault(header_key(header), header)

    for canonical, source in provided.items():
        if canonical not in SYNONYMS:
            raise InvalidMappingError(str(source))
        if not source:
            resolved.pop(canonical, None)
            continue
        matched = header_by_key.get(header_key(source))
        if matched is None:
            raise InvalidMappingError(source)
        resolved[canonical] = matched
    return {field: header for field, header in resolved.items() if header}


class InvalidMappingError(Exception):
    def __init__(self, header: str) -> None:
        self.header = header
        super().__init__(MESSAGES_AR["INVALID_MAPPING"])


@dataclass
class MoneyResult:
    value: Decimal | None
    status: str  # "ok" | "empty" | "ambiguous"


def _grouped_integer(text: str) -> str | None:
    parts = text.split(",")
    if len(parts) < 2:
        return None
    if not all(part.isdigit() and len(part) == 3 for part in parts[1:]):
        return None
    if not (1 <= len(parts[0]) <= 3 and parts[0].isdigit()):
        return None
    return "".join(parts)


def parse_money(raw: object) -> MoneyResult:
    """Parse a money value into Decimal without ever using binary floats."""
    if raw is None:
        return MoneyResult(None, "empty")
    if isinstance(raw, Decimal):
        return MoneyResult(raw.quantize(_CENT, rounding=ROUND_HALF_UP), "ok")
    if isinstance(raw, bool):
        return MoneyResult(None, "ambiguous")
    if isinstance(raw, int):
        return MoneyResult(Decimal(raw), "ok")
    if isinstance(raw, float):
        return MoneyResult(
            Decimal(str(raw)).quantize(_CENT, rounding=ROUND_HALF_UP), "ok"
        )

    text = convert_digits(normalize_unicode(str(raw))).strip()
    if not text:
        return MoneyResult(None, "empty")

    text = text.replace("\u066b", ".").replace("\u066c", ",")
    text = re.sub(r"\s+", "", text)
    text = _CURRENCY_TOKEN.sub("", text)
    if not text:
        return MoneyResult(None, "empty")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.endswith("-"):
        negative = not negative
        text = text[:-1]
    if text.startswith("-"):
        negative = not negative
        text = text[1:]
    if text.startswith("+"):
        text = text[1:]
    text = text.strip()
    if not text:
        return MoneyResult(None, "ambiguous")
    if not re.fullmatch(r"[0-9.,]+", text):
        return MoneyResult(None, "ambiguous")

    if "," in text and "." in text:
        if text.rfind(".") > text.rfind(","):
            text = text.replace(",", "")
        else:
            text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        grouped = _grouped_integer(text)
        if grouped is not None:
            text = grouped
        else:
            whole, _, fraction = text.partition(",")
            if not whole.isdigit() or not fraction.isdigit() or len(fraction) > 2:
                return MoneyResult(None, "ambiguous")
            text = f"{whole}.{fraction}"
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 2:
            if not all(part.isdigit() and len(part) == 3 for part in parts[1:]):
                return MoneyResult(None, "ambiguous")
            if not (1 <= len(parts[0]) <= 3 and parts[0].isdigit()):
                return MoneyResult(None, "ambiguous")
            text = "".join(parts)
        else:
            whole, _, fraction = text.partition(".")
            if not whole.isdigit() or not fraction.isdigit():
                return MoneyResult(None, "ambiguous")
            if len(fraction) > 2:
                # A single three-digit group after a dot is ambiguous: 1.250
                # could mean one thousand two hundred fifty or 1.25.
                return MoneyResult(None, "ambiguous")
            text = f"{whole}.{fraction}"

    if not text.isdigit() and not re.fullmatch(r"[0-9]+\.[0-9]+", text):
        return MoneyResult(None, "ambiguous")
    digits_only = text.replace(".", "")
    if len(digits_only) > _MAX_MONEY_DIGITS:
        return MoneyResult(None, "ambiguous")

    try:
        value = Decimal(text)
    except InvalidOperation:
        return MoneyResult(None, "ambiguous")
    if negative:
        value = -value
    return MoneyResult(value.quantize(_CENT, rounding=ROUND_HALF_UP), "ok")


def money_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.quantize(_CENT, rounding=ROUND_HALF_UP), "f")


def parse_currency(raw: object) -> str | None:
    text = clean_text(raw).strip().rstrip(".")
    if not text:
        return None
    key = text.casefold()
    if key in _CURRENCY_MAP:
        return _CURRENCY_MAP[key]
    if text.upper() in _ISO_CURRENCIES:
        return text.upper()
    return None


# Currency tokens are matched inside free text (titles, notes, headers).  The
# key is the token with spaces and dots removed so "ل.س", "ل س" and "ل.س."
# all collapse to the same entry.
_CURRENCY_SCAN_TOKENS: dict[str, str] = {
    "syp": "SYP",
    "لس": "SYP",
    "ل.س": "SYP",
    "ليره": "SYP",
    "ليرة": "SYP",
    "دس": "SYP",
    "د.س": "SYP",
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "دولار": "USD",
    "eur": "EUR",
    "€": "EUR",
    "sar": "SAR",
    "رس": "SAR",
    "ر.س": "SAR",
    "ريال": "SAR",
    "aed": "AED",
    "درهم": "AED",
}


def detect_currency(value: object) -> str | None:
    """Best-effort currency detection from a free-text value.

    Returns the first canonical currency token found, so document titles such
    as ``... | العملة: ليرة سورية (ل.س)`` infer ``SYP`` even when no currency
    column exists.
    """
    if value is None:
        return None
    text = clean_text(value)
    if not text:
        return None
    direct = parse_currency(text)
    if direct is not None:
        return direct
    for match in _CURRENCY_DETECT_TOKEN.finditer(text):
        token = re.sub(r"[\s.]+", "", match.group(0)).casefold()
        mapped = _CURRENCY_SCAN_TOKENS.get(token)
        if mapped is not None:
            return mapped
    for match in _CURRENCY_WORD_TOKEN.finditer(text):
        mapped = _CURRENCY_SCAN_TOKENS.get(match.group(0).casefold())
        if mapped is not None:
            return mapped
    return None


@dataclass
class PhoneResult:
    original: str
    normalized: str | None
    status: str  # "ok" | "missing" | "invalid"


def normalize_phone(raw: object) -> PhoneResult:
    original = normalize_unicode(str(raw)).strip() if raw is not None else ""
    if not original:
        return PhoneResult("", None, "missing")

    text = convert_digits(original)
    # OCR sometimes emits the international prefix after the digits
    # (``963900000101+``). Move a single trailing plus to the front so the
    # number still parses instead of being rejected.
    stripped = text.strip()
    if (
        stripped.endswith("+")
        and "+" not in stripped[:-1]
        and any(character.isdigit() for character in stripped[:-1])
    ):
        text = "+" + stripped[:-1]
    cleaned = re.sub(r"[^\d+]", "", text)
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned or cleaned == "+":
        return PhoneResult(original, None, "invalid")
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")):
        return PhoneResult(original, None, "invalid")

    try:
        number = phonenumbers.parse(cleaned, "SY")
    except phonenumbers.NumberParseException:
        return PhoneResult(original, None, "invalid")

    if phonenumbers.is_valid_number(number):
        return PhoneResult(
            original,
            phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
            "ok",
        )
    if phonenumbers.is_possible_number(number):
        # Keep a normalized representation for matching/provenance but never
        # mark the row eligible: invalid numbers must stay unmailable.
        return PhoneResult(
            original,
            phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
            "invalid",
        )
    return PhoneResult(original, None, "invalid")


def issue(code: str, *, severity: str | None = None, field: str | None = None) -> ImportIssue:
    if severity is None:
        severity = "error" if code in {
            "MISSING_GUARDIAN",
            "MISSING_BALANCE",
            "NEGATIVE_BALANCE",
            "MISSING_CURRENCY",
            "AMBIGUOUS_MONEY",
            "DUPLICATE_ROW",
        } else "warning"
    if field is None:
        from .constants import ERROR_FIELDS, WARNING_FIELDS

        field = ERROR_FIELDS.get(code) or WARNING_FIELDS.get(code) or "row"
    return ImportIssue(
        code=code,
        field=field,
        message_ar=MESSAGES_AR.get(code, code),
        severity=severity,
    )


def is_zero(value: Decimal | None) -> bool:
    return value is not None and value == _ZERO
