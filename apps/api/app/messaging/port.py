from __future__ import annotations

from typing import Any, Protocol

from .types import ProviderResult


class ProviderPort(Protocol):
    def send(
        self,
        *,
        to: str,
        text: str,
        idempotency_key: str,
        channel: str,
    ) -> ProviderResult: ...

    def get_status(self, *, provider_message_id: str) -> ProviderResult: ...

    def get_balance(self) -> dict[str, Any]: ...

    def health(self) -> bool: ...
