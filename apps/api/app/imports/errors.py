from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import MESSAGES_AR


@dataclass(slots=True)
class ImportIssue:
    code: str
    field: str
    message_ar: str
    severity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "message_ar": self.message_ar,
            "severity": self.severity,
        }


class ImportParseError(Exception):
    """Raised when a stored file cannot be turned into staged rows."""

    def __init__(
        self,
        code: str,
        *,
        message_ar: str | None = None,
        details: Any = None,
    ) -> None:
        self.code = code
        self.message_ar = message_ar or MESSAGES_AR.get(code, code)
        self.details = details
        super().__init__(self.message_ar)
