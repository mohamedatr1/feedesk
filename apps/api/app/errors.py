from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message_ar: str,
        message_en: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message_ar = message_ar
        self.message_en = message_en
        self.details = details
        super().__init__(message_en)
