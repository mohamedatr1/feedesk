from __future__ import annotations

import re
from typing import Any

import httpx

from ..redaction import redact_text
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

_SMS_CHANNELS = frozenset({"sms", "local_sms"})
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,40}$")


def _map_status(value: str | None) -> str:
    if not value:
        return OUTCOME_UNKNOWN
    normalized = value.strip().lower()
    if normalized == "delivered":
        return OUTCOME_DELIVERED
    if normalized == "queued":
        return OUTCOME_QUEUED
    if normalized in {"sent", "accepted"}:
        return OUTCOME_ACCEPTED
    if normalized in {"failed", "rejected", "error"}:
        return OUTCOME_FAILED
    return OUTCOME_UNKNOWN


def _safe_token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    if not token or not _SAFE_TOKEN.fullmatch(token):
        return None
    return token


def _body_dict(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _nested(body: dict[str, Any], key: str) -> Any:
    data = body.get("data")
    if isinstance(data, dict) and key in data:
        return data.get(key)
    return body.get(key)


def _extract(body: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = _nested(body, key)
        if value is not None:
            return value
    return None


def _extract_code(body: dict[str, Any]) -> str | None:
    code = _extract(body, "code", "error_code", "errorCode")
    if code is None:
        error = body.get("error")
        if isinstance(error, dict):
            code = error.get("code") or error.get("error_code")
        elif isinstance(error, str) and _SAFE_TOKEN.fullmatch(error.strip()):
            code = error
    if code is None:
        return None
    return redact_text(str(code).strip())[:80] or None


def _extract_status(body: dict[str, Any]) -> str | None:
    value = _extract(body, "status", "state", "message_status", "messageStatus")
    return _safe_token(value)


def _extract_message_id(body: dict[str, Any]) -> str | None:
    return _safe_token(_extract(body, "message_id", "messageId", "id"))


def _extract_request_id(body: dict[str, Any]) -> str | None:
    return _safe_token(_extract(body, "request_id", "requestId"))


class RaselProvider:
    """Rasel SMS adapter using the published v2 contract.

    Tests must inject an ``httpx.Client`` backed by ``httpx.MockTransport``.
    This module performs no import-time network I/O.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        sender_id: str,
        channel: str = "local_sms",
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://raselsms.com").rstrip("/")
        self.sender_id = (sender_id or "").strip()
        self.channel = (channel or "local_sms").strip()
        self._client = client or httpx.Client(timeout=timeout)

    @property
    def name(self) -> str:
        return "rasel"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RaselProvider:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def _payload(
        *,
        http_status: int | None,
        provider_status: str | None = None,
        code: str | None = None,
        provider_message_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"provider": "rasel"}
        if http_status is not None:
            payload["http_status"] = http_status
        if provider_status:
            payload["status"] = provider_status
        if code:
            payload["code"] = code
        if provider_message_id:
            payload["provider_message_id"] = provider_message_id
        if request_id:
            payload["request_id"] = request_id
        return payload

    def _interpret(self, response: httpx.Response) -> ProviderResult:
        http_status = response.status_code
        if http_status in {401, 403}:
            code = "AUTH_FAILED" if http_status == 401 else "FORBIDDEN"
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code=code,
                error_summary="Provider authentication failed.",
                payload_redacted=self._payload(http_status=http_status, code=code),
            )
        if http_status == 429:
            retry_after = None
            raw_retry_after = response.headers.get("retry-after")
            if raw_retry_after:
                try:
                    retry_after = max(0, int(raw_retry_after.strip()))
                except ValueError:
                    retry_after = None
            return ProviderResult(
                outcome=OUTCOME_RATE_LIMITED,
                provider_status="rate_limited",
                error_code="RATE_LIMITED",
                error_summary="Provider rate limit exceeded.",
                retry_after_seconds=retry_after,
                payload_redacted=self._payload(
                    http_status=http_status, code="RATE_LIMITED"
                ),
            )
        if http_status >= 500:
            return ProviderResult(
                outcome=OUTCOME_TEMPORARY_ERROR,
                provider_status="error",
                error_code="TEMPORARY_ERROR",
                error_summary="Provider temporary failure.",
                payload_redacted=self._payload(
                    http_status=http_status, code="TEMPORARY_ERROR"
                ),
            )
        if not response.is_success:
            code = "INVALID_REQUEST" if http_status < 500 else "PROVIDER_ERROR"
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code=code,
                error_summary="Provider rejected the submission.",
                payload_redacted=self._payload(http_status=http_status, code=code),
            )

        body = _body_dict(response)
        status = _extract_status(body)
        code = _extract_code(body)
        message_id = _extract_message_id(body)
        request_id = _extract_request_id(body)
        outcome = _map_status(status)

        success_flag = body.get("success")
        if outcome == OUTCOME_UNKNOWN and success_flag is False:
            outcome = OUTCOME_FAILED
            code = code or "PROVIDER_FAILED"
        if outcome == OUTCOME_FAILED:
            code = code or "PROVIDER_FAILED"

        payload = self._payload(
            http_status=http_status,
            provider_status=status,
            code=code,
            provider_message_id=message_id,
            request_id=request_id,
        )
        error_summary = None
        if outcome == OUTCOME_FAILED:
            error_summary = "Provider rejected the submission."
        elif outcome == OUTCOME_UNKNOWN:
            error_summary = "Provider response could not be mapped; outcome unknown."
        return ProviderResult(
            outcome=outcome,
            provider_status=status,
            request_id=request_id,
            provider_message_id=message_id,
            error_code=code if outcome == OUTCOME_FAILED else None,
            error_summary=error_summary,
            payload_redacted=payload,
        )

    def send(
        self,
        *,
        to: str,
        text: str,
        idempotency_key: str,
        channel: str,
    ) -> ProviderResult:
        if not self.api_key or not self.sender_id:
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code="PROVIDER_CONFIG_INVALID",
                error_summary="Provider credentials are incomplete.",
                payload_redacted=self._payload(http_status=None),
            )
        if channel not in _SMS_CHANNELS or self.channel not in _SMS_CHANNELS:
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code="UNSUPPORTED_CHANNEL",
                error_summary="Only SMS channels are enabled.",
                payload_redacted=self._payload(http_status=None),
            )

        body = {
            "to": to,
            "channel": "local_sms",
            "messageType": "free_text",
            "content": {"text": text},
        }
        url = f"{self.base_url}/api/v2/messages/send"
        try:
            response = self._client.post(
                url,
                headers=self._headers(idempotency_key),
                json=body,
            )
        except httpx.TimeoutException:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="TIMEOUT",
                error_summary="Provider response timed out; outcome unknown.",
                payload_redacted=self._payload(http_status=None, code="TIMEOUT"),
            )
        except httpx.TransportError:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="TRANSPORT_ERROR",
                error_summary="Provider transport failed; outcome unknown.",
                payload_redacted=self._payload(
                    http_status=None, code="TRANSPORT_ERROR"
                ),
            )
        except httpx.HTTPError:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="TRANSPORT_ERROR",
                error_summary="Provider request failed; outcome unknown.",
                payload_redacted=self._payload(
                    http_status=None, code="TRANSPORT_ERROR"
                ),
            )
        except Exception:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="UNEXPECTED_ERROR",
                error_summary="Provider request failed; outcome unknown.",
                payload_redacted=self._payload(
                    http_status=None, code="UNEXPECTED_ERROR"
                ),
            )
        return self._interpret(response)

    def get_status(self, *, provider_message_id: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(
                outcome=OUTCOME_FAILED,
                error_code="PROVIDER_CONFIG_INVALID",
                error_summary="Provider credentials are incomplete.",
                payload_redacted=self._payload(http_status=None),
            )
        url = f"{self.base_url}/api/v2/messages/{provider_message_id}"
        try:
            response = self._client.get(url, headers=self._headers())
        except httpx.TimeoutException:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="TIMEOUT",
                error_summary="Provider response timed out; outcome unknown.",
                payload_redacted=self._payload(http_status=None, code="TIMEOUT"),
            )
        except httpx.HTTPError:
            return ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="TRANSPORT_ERROR",
                error_summary="Provider request failed; outcome unknown.",
                payload_redacted=self._payload(
                    http_status=None, code="TRANSPORT_ERROR"
                ),
            )
        return self._interpret(response)

    def get_balance(self) -> dict[str, Any]:
        if not self.api_key:
            return {"provider": "rasel", "available": False}
        url = f"{self.base_url}/api/v2/balance"
        try:
            response = self._client.get(url, headers=self._headers())
        except httpx.HTTPError:
            return {"provider": "rasel", "available": False}
        if not response.is_success:
            return {"provider": "rasel", "available": False}
        body = _body_dict(response)
        return {
            "provider": "rasel",
            "available": True,
            "currency": str(body.get("currency") or ""),
            "balance": str(body.get("balance") or ""),
        }

    def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = self._client.get(self.base_url, headers=self._headers())
        except httpx.HTTPError:
            return False
        return response.status_code < 500


RaselAdapter = RaselProvider
