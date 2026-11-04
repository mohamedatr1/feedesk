from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.messaging.factory import (
    ProviderConfigurationError,
    build_provider,
    provider_configuration_error,
)
from app.messaging.fake import FakeProvider
from app.messaging.rasel import RaselProvider

from .messaging_helpers import messaging_config

FAKE_MATRIX = [
    ("delivered", "delivered", "delivered", None),
    ("accepted", "accepted", "accepted", None),
    ("queued", "queued", "queued", None),
    ("failed", "failed", "failed", "FAKE_FAILED"),
    ("rate_limited", "rate_limited", "rate_limited", "RATE_LIMITED"),
    ("timeout", "unknown", None, "TIMEOUT"),
    ("temporary_error", "temporary_error", "error", "TEMPORARY_ERROR"),
    ("insufficient_balance", "failed", "insufficient_balance", "INSUFFICIENT_BALANCE"),
    ("invalid_recipient", "failed", "invalid_recipient", "INVALID_RECIPIENT"),
    ("duplicate", "accepted", "duplicate", None),
]


@pytest.mark.parametrize(
    ("scenario", "outcome", "provider_status", "error_code"), FAKE_MATRIX
)
def test_fake_provider_scenario_matrix(
    scenario: str, outcome: str, provider_status: str | None, error_code: str | None
) -> None:
    provider = FakeProvider(scenario=scenario)
    result = provider.send(
        to="+963993000701",
        text="رسالة اختبار",
        idempotency_key=f"key-{scenario}",
        channel="local_sms",
    )
    assert result.outcome == outcome
    assert result.provider_status == provider_status
    assert result.error_code == error_code
    assert provider.send_count == 1
    assert "+963" not in json.dumps(result.payload_redacted, ensure_ascii=False)
    assert "رسالة اختبار" not in json.dumps(result.payload_redacted, ensure_ascii=False)


def test_fake_provider_deduplicates_by_idempotency_key_and_counts_sends() -> None:
    provider = FakeProvider(scenario="delivered")
    first = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="stable-key",
        channel="local_sms",
    )
    second = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="stable-key",
        channel="local_sms",
    )
    assert provider.send_count == 1
    assert first == second
    assert provider.get_status(provider_message_id=first.provider_message_id or "").outcome == (
        "delivered"
    )
    assert provider.health() is True
    assert provider.get_balance()["available"] is True


def test_fake_provider_hard_rejects_non_sms_channel() -> None:
    provider = FakeProvider(scenario="delivered")
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="whatsapp-key",
        channel="whatsapp",
    )
    assert result.outcome == "failed"
    assert result.error_code == "UNSUPPORTED_CHANNEL"
    assert provider.send_count == 0


def test_fake_mode_never_constructs_or_calls_rasel(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("fake mode must never perform network I/O")

    monkeypatch.setattr(httpx.Client, "send", explode)
    provider = build_provider(
        messaging_config(messaging_provider="fake", fake_provider_scenario="delivered")
    )
    assert isinstance(provider, FakeProvider)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="fake-only",
        channel="local_sms",
    )
    assert result.outcome == "delivered"


def _rasel_provider(handler: Any) -> tuple[RaselProvider, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(wrapped))
    provider = RaselProvider(
        api_key="test-api-key",
        base_url="https://rasel.invalid",
        sender_id="TEST-SENDER",
        client=client,
    )
    return provider, requests


def test_rasel_send_request_shape_and_redacted_payload() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "queued", "message_id": "msg-1", "request_id": "req-1"},
        )

    provider, requests = _rasel_provider(handler)
    result = provider.send(
        to="+963993000701",
        text="رسالة سرية",
        idempotency_key="idem-123",
        channel="local_sms",
    )

    assert result.outcome == "queued"
    assert result.provider_message_id == "msg-1"
    assert result.request_id == "req-1"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://rasel.invalid/api/v2/messages/send"
    assert request.headers["X-API-Key"] == "test-api-key"
    assert request.headers["Idempotency-Key"] == "idem-123"
    assert request.headers["Content-Type"].startswith("application/json")
    body = json.loads(request.content)
    assert body == {
        "to": "+963993000701",
        "channel": "local_sms",
        "messageType": "free_text",
        "content": {"text": "رسالة سرية"},
    }

    payload = json.dumps(result.payload_redacted, ensure_ascii=False)
    assert "test-api-key" not in payload
    assert "+963993000701" not in payload
    assert "رسالة سرية" not in payload
    assert set(result.payload_redacted).issubset(
        {"provider", "http_status", "status", "code", "provider_message_id", "request_id"}
    )


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("delivered", "delivered"),
        ("sent", "accepted"),
        ("accepted", "accepted"),
        ("queued", "queued"),
        ("failed", "failed"),
        ("rejected", "failed"),
        ("in_progress", "unknown"),
        ("", "unknown"),
    ],
)
def test_rasel_conservative_status_mapping(
    provider_status: str, expected: str
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = {"message_id": "msg-1"}
        if provider_status:
            body["status"] = provider_status
        return httpx.Response(200, json=body)

    provider, _ = _rasel_provider(handler)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key=f"key-{provider_status or 'none'}",
        channel="local_sms",
    )
    assert result.outcome == expected
    if expected == "delivered":
        assert result.provider_status == "delivered"


@pytest.mark.parametrize(
    ("status_code", "expected_outcome", "expected_code"),
    [
        (400, "failed", "INVALID_REQUEST"),
        (401, "failed", "AUTH_FAILED"),
        (403, "failed", "FORBIDDEN"),
        (500, "temporary_error", "TEMPORARY_ERROR"),
        (503, "temporary_error", "TEMPORARY_ERROR"),
    ],
)
def test_rasel_http_error_mapping(
    status_code: int, expected_outcome: str, expected_code: str
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "provider detail"})

    provider, _ = _rasel_provider(handler)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key=f"key-{status_code}",
        channel="local_sms",
    )
    assert result.outcome == expected_outcome
    assert result.error_code == expected_code
    assert "provider detail" not in json.dumps(result.payload_redacted)


def test_rasel_rate_limit_honors_retry_after() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "7"}, json={})

    provider, _ = _rasel_provider(handler)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="key-429",
        channel="local_sms",
    )
    assert result.outcome == "rate_limited"
    assert result.retry_after_seconds == 7


def test_rasel_timeout_and_transport_errors_are_unknown() -> None:
    def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    provider, _ = _rasel_provider(timeout_handler)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="key-timeout",
        channel="local_sms",
    )
    assert result.outcome == "unknown"
    assert result.error_code == "TIMEOUT"

    def transport_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset")

    provider, _ = _rasel_provider(transport_handler)
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="key-transport",
        channel="local_sms",
    )
    assert result.outcome == "unknown"
    assert result.error_code == "TRANSPORT_ERROR"


def test_rasel_missing_credentials_never_calls_network() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not call the provider without credentials")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = RaselProvider(
        api_key="",
        base_url="https://rasel.invalid",
        sender_id="",
        client=client,
    )
    result = provider.send(
        to="+963993000701",
        text="نص",
        idempotency_key="key",
        channel="local_sms",
    )
    assert result.outcome == "failed"
    assert result.error_code == "PROVIDER_CONFIG_INVALID"


def test_provider_configuration_guard() -> None:
    assert provider_configuration_error(messaging_config()) is None
    incomplete = messaging_config(
        messaging_provider="rasel", rasel_api_key="", rasel_sender_id=""
    )
    assert provider_configuration_error(incomplete) == "RASEL_API_KEY is missing."
    missing_sender = messaging_config(
        messaging_provider="rasel", rasel_api_key="key", rasel_sender_id=""
    )
    assert provider_configuration_error(missing_sender) == "RASEL_SENDER_ID is missing."
    with pytest.raises(ProviderConfigurationError):
        build_provider(incomplete)


def _rasel_config(**updates: Any):
    base = {
        "messaging_provider": "rasel",
        "rasel_api_key": "test-key",
        "rasel_sender_id": "TEST-SENDER",
        "rasel_base_url": "https://rasel.invalid",
    }
    base.update(updates)
    return messaging_config(**base)


def test_provider_configuration_rejects_fake_in_production() -> None:
    error = provider_configuration_error(
        messaging_config(messaging_provider="fake", app_env="production")
    )
    assert error == "The fake messaging provider is refused in production."


def test_provider_configuration_allows_explicit_production_fake_override() -> None:
    config = messaging_config(
        messaging_provider="fake",
        app_env="production",
        messaging_allow_fake_in_production=True,
    )
    assert provider_configuration_error(config) is None


def test_provider_configuration_allows_production_fake_when_messaging_disabled() -> None:
    config = messaging_config(
        messaging_provider="fake",
        app_env="production",
        messaging_enabled=False,
    )
    assert provider_configuration_error(config) is None


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        (
            {"messaging_rate_limit_per_second": 0},
            "MESSAGING_RATE_LIMIT_PER_SECOND must be greater than zero.",
        ),
        (
            {"messaging_max_attempts": 0},
            "MESSAGING_MAX_ATTEMPTS must be at least 1.",
        ),
        (
            {"messaging_lease_seconds": 0},
            "MESSAGING_LEASE_SECONDS must be greater than zero.",
        ),
        (
            {"rasel_base_url": "http://rasel.invalid"},
            "RASEL_BASE_URL must be a valid https URL.",
        ),
        (
            {"rasel_base_url": "not-a-url"},
            "RASEL_BASE_URL must be a valid https URL.",
        ),
        (
            {"messaging_allowlist": "+963993000701,not-a-phone"},
            "MESSAGING_ALLOWLIST contains an invalid phone number.",
        ),
        (
            {"messaging_allowlist": "0993000701"},
            "MESSAGING_ALLOWLIST contains an invalid phone number.",
        ),
    ],
)
def test_provider_configuration_rejects_unsafe_values(
    updates: dict[str, Any], expected: str
) -> None:
    error = provider_configuration_error(_rasel_config(**updates))
    assert error == expected


def test_provider_configuration_accepts_https_and_e164_allowlist() -> None:
    config = _rasel_config(
        rasel_base_url="https://rasel.invalid/api",
        messaging_allowlist="+963993000701, +963993000702",
    )
    assert provider_configuration_error(config) is None
    provider = build_provider(config)
    assert isinstance(provider, RaselProvider)
    provider.close()


def test_provider_configuration_allowlist_error_never_echoes_numbers() -> None:
    raw = "+963993000701,bad"
    error = provider_configuration_error(_rasel_config(messaging_allowlist=raw))
    assert error is not None
    assert "+963" not in error
    assert "bad" not in error

