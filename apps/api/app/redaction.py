from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"
PHONE_REDACTED = "[PHONE_REDACTED]"

_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|csrf|authorization|api[_-]?key|access[_-]?key|"
    r"phone|mobile|message[_-]?body|template[_-]?body)",
    re.IGNORECASE,
)
_HEADER_SECRET = re.compile(
    r"(?i)\b(authorization|proxy-authorization|x-api-key|x-csrf-token|cookie|set-cookie)"
    r"\b[\"']?\s*[:=]\s*(?:[a-z]+\s+)?[^\s,;]+"
)
_KEY_VALUE_SECRET = re.compile(
    r"(?i)\b(password|passwd|secret|token|csrf(?:[_-]?token)?|api[_-]?key|access[_-]?key|"
    r"phone|mobile|message[_-]?body|template[_-]?body)\b"
    r"[\"']?\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_MESSAGE_BODY = re.compile(
    r"(?im)^(.*\b(?:message[_-]?body|template[_-]?body)\b[\"']?\s*[:=]).*$"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_PHONE_CANDIDATE = re.compile(r"(?<![\d+])\+?\d[\d\s()-]{7,}\d(?![\d:])")


def _mask_phone(match: re.Match[str]) -> str:
    candidate = match.group(0)
    digits = re.sub(r"\D", "", candidate)
    if not 9 <= len(digits) <= 15:
        return candidate

    groups = [group for group in re.split(r"[\s()-]+", candidate.strip()) if group]
    if len(groups) > 1:
        # Avoid swallowing log fields such as a UUID tail, status, and duration.
        if not 3 <= len(groups[-1]) <= 4:
            return candidate
        if any(not 2 <= len(group) <= 4 for group in groups):
            return candidate
    return PHONE_REDACTED


def redact_text(value: str) -> str:
    """Mask credentials, contact numbers, and message bodies before logging."""
    redacted = _BEARER.sub(r"\1 [REDACTED]", value)
    redacted = _HEADER_SECRET.sub(r"\1: [REDACTED]", redacted)
    redacted = _KEY_VALUE_SECRET.sub(r"\1=[REDACTED]", redacted)
    redacted = _MESSAGE_BODY.sub(r"\1[REDACTED]", redacted)
    return _PHONE_CANDIDATE.sub(_mask_phone, redacted)


def redact_mapping(value: Any) -> Any:
    """Recursively redact sensitive keys in structured log payloads."""
    if isinstance(value, dict):
        return {
            key: REDACTED if _SENSITIVE_KEY.search(str(key)) else redact_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
