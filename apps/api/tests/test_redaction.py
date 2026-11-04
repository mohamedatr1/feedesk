from __future__ import annotations

import logging
import sys

from app.main import JsonFormatter
from app.redaction import PHONE_REDACTED, redact_mapping, redact_text


def test_redact_text_masks_credentials_and_message_bodies() -> None:
    raw = (
        "login failed Authorization: Bearer abcdefghijklmnop "
        "token=supersecrettoken123 api_key=provider-secret\n"
        "message_body=السلام عليكم"
    )

    cleaned = redact_text(raw)

    assert "abcdefghijklmnop" not in cleaned
    assert "supersecrettoken123" not in cleaned
    assert "provider-secret" not in cleaned
    assert "السلام عليكم" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redact_text_masks_unlabelled_phone_numbers() -> None:
    cleaned = redact_text("guardian contact 0900-000-000 failed")

    assert "0900-000-000" not in cleaned
    assert PHONE_REDACTED in cleaned


def test_redact_mapping_masks_sensitive_keys() -> None:
    redacted = redact_mapping(
        {
            "username": "admin",
            "phone": "+963900000000",
            "message_body": "رسالة",
            "nested": {"api_key": "provider-secret"},
        }
    )

    assert redacted["username"] == "admin"
    assert redacted["phone"] == "[REDACTED]"
    assert redacted["message_body"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"


def test_json_formatter_redacts_messages_and_exceptions() -> None:
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "contact %s",
        ("+963 900 000 000",),
        None,
    )
    formatted = JsonFormatter().format(record)
    assert "+963" not in formatted
    assert PHONE_REDACTED in formatted

    try:
        raise RuntimeError("Authorization: Bearer abcdefghijklmnop")
    except RuntimeError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        "test", logging.ERROR, __file__, 1, "failed", None, exc_info
    )
    formatted = JsonFormatter().format(record)
    assert "abcdefghijklmnop" not in formatted
