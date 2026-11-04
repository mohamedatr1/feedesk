from __future__ import annotations

import re
from urllib.parse import urlsplit

import phonenumbers

from ..config import Settings
from ..config import settings as default_settings
from .credentials import ResolvedCredentials
from .fake import SCENARIOS, FakeProvider
from .port import ProviderPort
from .rasel import RaselProvider

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")
_ALLOWED_PROVIDERS = frozenset({"fake", "rasel"})


class ProviderConfigurationError(RuntimeError):
    """Raised when the configured provider cannot be constructed safely."""


def provider_name(config: Settings | None = None) -> str:
    return ((config or default_settings).messaging_provider or "").strip().lower()


def _is_e164(value: str) -> bool:
    if not _E164.fullmatch(value):
        return False
    try:
        number = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        return False
    return phonenumbers.is_valid_number(number)


def _allowlist_invalid(raw: str) -> bool:
    for part in (raw or "").split(","):
        value = part.strip()
        if value and not _is_e164(value):
            return True
    return False


def transport_configuration_error(config: Settings | None = None) -> str | None:
    """Validate everything that is independent of stored credentials.

    This covers the provider name, pacing/attempt/lease safety limits, the
    allowlist, fake-provider production guards, and the Rasel transport (base
    URL and channel).  It deliberately does **not** require
    ``RASEL_API_KEY``/``RASEL_SENDER_ID``: the worker resolves those from the
    credential vault at runtime.  Messages are fixed strings and never contain
    credential values or phone numbers.
    """
    config = config or default_settings
    name = provider_name(config)
    if name not in _ALLOWED_PROVIDERS:
        return "Unsupported messaging provider."
    if config.messaging_rate_limit_per_second <= 0:
        return "MESSAGING_RATE_LIMIT_PER_SECOND must be greater than zero."
    if config.messaging_max_attempts < 1:
        return "MESSAGING_MAX_ATTEMPTS must be at least 1."
    if config.messaging_lease_seconds <= 0:
        return "MESSAGING_LEASE_SECONDS must be greater than zero."
    if _allowlist_invalid(config.messaging_allowlist):
        return "MESSAGING_ALLOWLIST contains an invalid phone number."
    if name == "fake":
        if (
            config.app_env.strip().lower() == "production"
            and config.messaging_enabled
            and not config.messaging_allow_fake_in_production
        ):
            return "The fake messaging provider is refused in production."
        scenario = (config.fake_provider_scenario or "delivered").strip().lower()
        if scenario not in SCENARIOS:
            return "Unsupported fake provider scenario."
        return None
    if not (config.rasel_base_url or "").strip():
        return "RASEL_BASE_URL is missing."
    if (config.rasel_channel or "").strip() not in {"local_sms", "sms"}:
        return "RASEL_CHANNEL must be an SMS channel."
    parsed = urlsplit((config.rasel_base_url or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return "RASEL_BASE_URL must be a valid https URL."
    return None


def provider_configuration_error(config: Settings | None = None) -> str | None:
    """Return an operator-facing reason, or ``None`` when configuration is usable.

    Environment-based construction additionally requires the legacy
    ``RASEL_API_KEY``/``RASEL_SENDER_ID`` variables.  The worker uses
    :func:`build_provider_from_credentials` so stored credentials can be used
    without environment secrets.
    """
    config = config or default_settings
    error = transport_configuration_error(config)
    if error is not None:
        return error
    if provider_name(config) == "fake":
        return None
    if not (config.rasel_api_key or "").strip():
        return "RASEL_API_KEY is missing."
    if not (config.rasel_sender_id or "").strip():
        return "RASEL_SENDER_ID is missing."
    return None


def build_provider(config: Settings | None = None) -> ProviderPort:
    config = config or default_settings
    error = provider_configuration_error(config)
    if error is not None:
        raise ProviderConfigurationError(error)
    name = provider_name(config)
    if name == "fake":
        return FakeProvider(scenario=config.fake_provider_scenario)
    return RaselProvider(
        api_key=config.rasel_api_key,
        base_url=config.rasel_base_url,
        sender_id=config.rasel_sender_id,
        channel=config.rasel_channel,
    )


def build_provider_from_credentials(
    config: Settings | None = None,
    resolved: ResolvedCredentials | None = None,
) -> ProviderPort | None:
    """Build a provider from already-resolved credentials.

    A database credential always wins: when ``resolved`` is ``None`` in Rasel
    mode this returns ``None`` instead of falling back to environment secrets.
    """
    config = config or default_settings
    if transport_configuration_error(config) is not None:
        return None
    if provider_name(config) == "fake":
        return FakeProvider(scenario=config.fake_provider_scenario)
    if resolved is None:
        return None
    return RaselProvider(
        api_key=resolved.api_key,
        base_url=config.rasel_base_url,
        sender_id=resolved.sender_id,
        channel=resolved.channel,
    )


create_provider = build_provider
