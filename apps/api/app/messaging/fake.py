from __future__ import annotations

import hashlib
from typing import Any

from .types import (
    OUTCOME_ACCEPTED,
    OUTCOME_DELIVERED,
    OUTCOME_FAILED,
    OUTCOME_QUEUED,
    OUTCOME_RATE_LIMITED,
    OUTCOME_TEMPORARY_ERROR,
    OUTCOME_UNKNOWN,
    ProviderResult,
)

SCENARIOS = frozenset(
    {
        "delivered",
        "accepted",
        "queued",
        "failed",
        "rate_limited",
        "timeout",
        "temporary_error",
        "insufficient_balance",
        "invalid_recipient",
        "duplicate",
    }
)

_SMS_CHANNELS = frozenset({"sms", "local_sms"})


class FakeProvider:
    """Deterministic in-process provider used by development and tests.

    The adapter never performs network I/O. It deduplicates by idempotency key:
    replaying a key returns the original result and does not increment
    ``send_count``.
    """

    def __init__(self, scenario: str = "delivered") -> None:
        normalized = (scenario or "delivered").strip().lower()
        if normalized not in SCENARIOS:
            raise ValueError(f"Unknown fake provider scenario: {scenario!r}")
        self.scenario = normalized
        self.send_count = 0
        self._results: dict[str, ProviderResult] = {}
        self._by_provider_id: dict[str, ProviderResult] = {}

    @property
    def name(self) -> str:
        return "fake"

    def _build_result(self, idempotency_key: str, channel: str) -> ProviderResult:
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:12]
        provider_message_id = f"fake-msg-{digest}"
        request_id = f"fake-req-{digest}"
        base_payload: dict[str, Any] = {
            "provider": "fake",
            "scenario": self.scenario,
            "channel": channel,
        }
        common = {
            "request_id": request_id,
            "provider_message_id": provider_message_id,
            "payload_redacted": base_payload,
        }

        if self.scenario == "delivered":
            return ProviderResult(
                outcome=OUTCOME_DELIVERED,
                provider_status="delivered",
                **common,
            )
        if self.scenario == "accepted":
            return ProviderResult(
                outcome=OUTCOME_ACCEPTED,
                provider_status="accepted",
                **common,
            )
        if self.scenario == "queued":
            return ProviderResult(
                outcome=OUTCOME_QUEUED,
                provider_status="queued",
                **common,
            )
        if self.scenario == "duplicate":
            return ProviderResult(
                outcome=OUTCOME_ACCEPTED,
                provider_status="duplicate",
                **common,
            )
        if self.scenario == "failed":
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                provider_status="failed",
                error_code="FAKE_FAILED",
                error_summary="Provider rejected the message.",
                **common,
            )
        if self.scenario == "rate_limited":
            return ProviderResult(
                outcome=OUTCOME_RATE_LIMITED,
                provider_status="rate_limited",
                error_code="RATE_LIMITED",
                error_summary="Provider rate limit exceeded.",
                retry_after_seconds=2,
                **common,
            )
        if self.scenario == "timeout":
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                provider_status=None,
                error_code="TIMEOUT",
                error_summary="Provider response timed out; outcome unknown.",
                **common,
            )
        if self.scenario == "temporary_error":
            return ProviderResult(
                outcome=OUTCOME_TEMPORARY_ERROR,
                provider_status="error",
                error_code="TEMPORARY_ERROR",
                error_summary="Provider temporary failure.",
                **common,
            )
        if self.scenario == "insufficient_balance":
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                provider_status="insufficient_balance",
                error_code="INSUFFICIENT_BALANCE",
                error_summary="Provider balance is insufficient.",
                **common,
            )
        # invalid_recipient
        return ProviderResult(
            outcome=OUTCOME_FAILED,
            provider_status="invalid_recipient",
            error_code="INVALID_RECIPIENT",
            error_summary="Provider rejected the recipient.",
            **common,
        )

    def send(
        self,
        *,
        to: str,
        text: str,
        idempotency_key: str,
        channel: str,
    ) -> ProviderResult:
        existing = self._results.get(idempotency_key)
        if existing is not None:
            return existing

        if channel not in _SMS_CHANNELS:
            result = ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code="UNSUPPORTED_CHANNEL",
                error_summary="Only SMS channels are enabled.",
                payload_redacted={"provider": "fake", "channel": channel},
            )
            self._results[idempotency_key] = result
            return result

        result = self._build_result(idempotency_key, channel)
        self.send_count += 1
        self._results[idempotency_key] = result
        if result.provider_message_id:
            self._by_provider_id[result.provider_message_id] = result
        return result

    def get_status(self, *, provider_message_id: str) -> ProviderResult:
        return self._by_provider_id.get(
            provider_message_id,
            ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="STATUS_UNAVAILABLE",
                error_summary="Status is not available for this provider id.",
                payload_redacted={"provider": "fake"},
            ),
        )

    def get_balance(self) -> dict[str, Any]:
        return {
            "provider": "fake",
            "available": True,
            "currency": "SYP",
            "balance": "1000000.00",
        }

    def health(self) -> bool:
        return True


FakeAdapter = FakeProvider
