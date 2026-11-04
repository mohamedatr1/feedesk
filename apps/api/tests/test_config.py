from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import Settings

PRODUCTION_VALUES = {
    "app_env": "production",
    "session_secret": "s" * 48,
    "cookie_secure": True,
    "cookie_name": "__Host-fd_session",
    "app_base_url": "https://feedesk.example.com",
    "seed_admin_password": "StrongSeed!2026",
    # Generated at test time: a synthetic test key, never a real secret.
    "provider_credential_key": Fernet.generate_key().decode(),
}


def _production(**overrides: object) -> Settings:
    values = dict(PRODUCTION_VALUES)
    values.update(overrides)
    return Settings(**values)


def test_production_settings_accept_hardened_values() -> None:
    config = _production()

    assert config.app_env == "production"
    assert config.cookie_secure is True


def test_production_requires_provider_credential_key() -> None:
    with pytest.raises(ValidationError):
        _production(provider_credential_key="")


def test_production_rejects_invalid_provider_credential_key() -> None:
    with pytest.raises(ValidationError):
        _production(provider_credential_key="not-a-fernet-key")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_secret", "dev-only-change-me"),
        ("session_secret", "too-short"),
        ("seed_admin_password", "ChangeMe!2026"),
        ("cookie_secure", False),
        ("cookie_name", "fd_session"),
        ("app_base_url", "http://feedesk.example.com"),
    ],
)
def test_production_settings_reject_unsafe_defaults(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _production(**{field: value})


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://"])
def test_managed_postgres_url_gets_psycopg_driver(scheme: str) -> None:
    config = Settings(database_url=f"{scheme}user:pass@db.example.com:5432/feedesk")

    assert config.database_url.startswith("postgresql+psycopg://")
    assert "db.example.com:5432/feedesk" in config.database_url


def test_development_settings_keep_local_defaults() -> None:
    config = Settings(
        app_env="development",
        cookie_secure=False,
        cookie_name="fd_session",
        app_base_url="http://localhost:3000",
    )

    assert config.cookie_name == "fd_session"
    assert config.cookie_secure is False


def test_production_rejects_fake_provider_when_messaging_enabled() -> None:
    with pytest.raises(ValidationError):
        _production(messaging_enabled=True, messaging_provider="fake")


def test_production_allows_fake_with_explicit_override() -> None:
    config = _production(
        messaging_enabled=True,
        messaging_provider="fake",
        messaging_allow_fake_in_production=True,
    )

    assert config.messaging_allow_fake_in_production is True


def test_production_allows_fake_when_messaging_disabled() -> None:
    config = _production(messaging_enabled=False, messaging_provider="fake")

    assert config.messaging_enabled is False


def test_production_rejects_unsupported_and_zero_rate_messaging() -> None:
    with pytest.raises(ValidationError):
        _production(messaging_enabled=True, messaging_provider="console")
    with pytest.raises(ValidationError):
        _production(
            messaging_enabled=True,
            messaging_provider="rasel",
            messaging_rate_limit_per_second=0,
        )


def test_seed_refuses_default_password_outside_development(monkeypatch) -> None:
    import app.seed as seed_module

    monkeypatch.setattr(seed_module.settings, "app_env", "staging")
    monkeypatch.setattr(seed_module.settings, "seed_admin_password", "ChangeMe!2026")
    monkeypatch.setattr(seed_module.settings, "seed_allow_default_password", False)

    with pytest.raises(RuntimeError):
        seed_module.ensure_seed_password_safe()


def test_seed_allows_documented_override_outside_development(monkeypatch) -> None:
    import app.seed as seed_module

    monkeypatch.setattr(seed_module.settings, "app_env", "staging")
    monkeypatch.setattr(seed_module.settings, "seed_admin_password", "ChangeMe!2026")
    monkeypatch.setattr(seed_module.settings, "seed_allow_default_password", True)

    seed_module.ensure_seed_password_safe()


def test_seed_allows_default_password_in_development(monkeypatch) -> None:
    import app.seed as seed_module

    monkeypatch.setattr(seed_module.settings, "app_env", "development")
    monkeypatch.setattr(seed_module.settings, "seed_admin_password", "ChangeMe!2026")
    monkeypatch.setattr(seed_module.settings, "seed_allow_default_password", False)

    seed_module.ensure_seed_password_safe()
