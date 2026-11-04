"""Display-safe privacy helpers shared by list, campaign and import views.

The full value never leaves this module for masked fields: the country code,
the first national digit and the final three digits are preserved (for example
``+963 9•• ••• 701``) so staff can still recognize a number without the response
containing the complete phone number.
"""

from __future__ import annotations

import re
from typing import Any

import phonenumbers

_MASK_BULLET = "•"
_PHONE_KEY_MARKERS = ("phone", "mobile", "telephone")
_DIGIT_TRANSLATION = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2
)


def _masked_national(national: str) -> str:
    if len(national) <= 4:
        return _MASK_BULLET * len(national)
    hidden = _MASK_BULLET * (len(national) - 4)
    first_block = national[0] + hidden[:-3]
    tail_hidden = hidden[-3:]
    blocks = [first_block]
    if tail_hidden:
        blocks.append(tail_hidden)
    blocks.append(national[-3:])
    return " ".join(blocks)


def _fallback_masked_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        return value
    has_plus = value.strip().startswith("+")
    country_length = 0
    if has_plus and len(digits) >= 12:
        country_length = 3
    elif has_plus and len(digits) >= 11:
        country_length = 2
    country = digits[:country_length]
    national = digits[country_length:]
    masked = _masked_national(national)
    prefix = f"+{country} " if country else ""
    return f"{prefix}{masked}"


def mask_phone(value: str | None, *, region: str = "SY") -> str | None:
    """Return a display-safe phone number.

    The country code, the first national digit, and the last three digits are
    preserved (for example ``+963 9•• ••• 701``).  Anything between them is
    replaced with bullets.  Invalid or unparsable values are masked
    conservatively rather than returned in full.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return text
    # Idempotent: an already-masked value must never be masked a second time.
    if _MASK_BULLET in text:
        return text
    candidate = text.translate(_DIGIT_TRANSLATION)
    try:
        number = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException:
        return _fallback_masked_phone(candidate)
    if not phonenumbers.is_valid_number(number):
        return _fallback_masked_phone(candidate)
    national = str(number.national_number)
    return f"+{number.country_code} {_masked_national(national)}"


def _is_phone_key(key: object) -> bool:
    lowered = str(key).lower()
    return any(marker in lowered for marker in _PHONE_KEY_MARKERS)


def redact_audit_payload(value: Any) -> Any:
    """Recursively mask phone values anywhere in an audit ``before``/``after``.

    Only string values stored under phone-like keys are masked; names, amounts,
    ids, and all other fields are preserved. Lists and nested dictionaries are
    traversed so payload shape cannot bypass the redaction.
    """
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(item, str) and _is_phone_key(key):
                redacted[key] = mask_phone(item)
            else:
                redacted[key] = redact_audit_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_audit_payload(item) for item in value]
    return value
