from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Provider outcomes. These are deliberately conservative: acceptance is not
# delivery and an ambiguous transport result is never treated as success.
OUTCOME_ACCEPTED = "accepted"
OUTCOME_QUEUED = "queued"
OUTCOME_DELIVERED = "delivered"
OUTCOME_FAILED = "failed"
OUTCOME_RATE_LIMITED = "rate_limited"
OUTCOME_TEMPORARY_ERROR = "temporary_error"
OUTCOME_UNKNOWN = "unknown"

PROVIDER_OUTCOMES = frozenset(
    {
        OUTCOME_ACCEPTED,
        OUTCOME_QUEUED,
        OUTCOME_DELIVERED,
        OUTCOME_FAILED,
        OUTCOME_RATE_LIMITED,
        OUTCOME_TEMPORARY_ERROR,
        OUTCOME_UNKNOWN,
    }
)

# Outcomes that are safe to retry automatically.
RETRYABLE_OUTCOMES = frozenset({OUTCOME_RATE_LIMITED, OUTCOME_TEMPORARY_ERROR})

# Outcomes that mean the provider may have received the request.
SUBMITTED_OUTCOMES = frozenset(
    {OUTCOME_ACCEPTED, OUTCOME_QUEUED, OUTCOME_DELIVERED}
)


@dataclass
class ProviderResult:
    outcome: str
    provider_status: str | None = None
    request_id: str | None = None
    provider_message_id: str | None = None
    error_code: str | None = None
    error_summary: str | None = None
    retry_after_seconds: int | None = None
    payload_redacted: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in PROVIDER_OUTCOMES:
            raise ValueError(f"Unsupported provider outcome: {self.outcome!r}")
