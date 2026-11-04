"""Server-side provider credential encryption and vault helpers.

Secrets only ever exist as Fernet ciphertext at rest and as plaintext in memory
for the duration of a single call.  Errors raised here are fixed, generic
strings so key material, ciphertext, or API keys can never reach logs or API
responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, NamedTuple

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ProviderCredential, User

CREDENTIAL_PROVIDER = "rasel"
SUPPORTED_CHANNELS = frozenset({"local_sms", "sms"})

_MISSING_KEY_ERROR = "Provider credential encryption key is not configured."
_INVALID_KEY_ERROR = "Provider credential encryption key is invalid."
_DECRYPT_ERROR = "Stored provider credential could not be decrypted."
_EMPTY_KEY_ERROR = "Provider credential is empty."
_INCOMPLETE_ERROR = "Provider credentials are incomplete."
_UNSUPPORTED_CHANNEL_ERROR = "Provider credential channel is invalid."


class CredentialError(RuntimeError):
    """Raised when credential encryption or decryption cannot proceed safely."""


class ResolvedCredentials(NamedTuple):
    """Plaintext credentials resolved for an in-process provider call."""

    api_key: str
    sender_id: str
    channel: str


class CredentialFingerprint(NamedTuple):
    """Non-secret identity of the currently authoritative credential.

    Used by the worker to detect revocation and rotation without ever holding
    or logging the plaintext key or the ciphertext.
    """

    source: str
    key_version: int | None
    is_active: bool


def _fernet() -> Fernet:
    raw = (settings.provider_credential_key or "").strip()
    if not raw:
        raise CredentialError(_MISSING_KEY_ERROR)
    try:
        return Fernet(raw.encode("utf-8"))
    except (TypeError, ValueError):
        raise CredentialError(_INVALID_KEY_ERROR) from None


def encrypt_api_key(api_key: str) -> str:
    """Encrypt a provider API key with the configured Fernet key."""
    value = (api_key or "").strip()
    if not value:
        raise CredentialError(_EMPTY_KEY_ERROR)
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_api_key(ciphertext: str | None) -> str:
    """Decrypt stored ciphertext.  Never include ciphertext in raised errors."""
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        raise CredentialError(_DECRYPT_ERROR) from None


def _normalize_channel(channel: str | None) -> str:
    normalized = (channel or "local_sms").strip().lower()
    if normalized not in SUPPORTED_CHANNELS:
        raise ValueError(_UNSUPPORTED_CHANNEL_ERROR)
    return normalized


def _row_for(db: Session, provider: str) -> ProviderCredential | None:
    return db.scalar(
        select(ProviderCredential).where(ProviderCredential.provider == provider)
    )


def _row_metadata(db: Session, row: ProviderCredential) -> dict[str, Any]:
    rotated_by_name = None
    if row.rotated_by:
        actor = db.get(User, row.rotated_by)
        if actor is not None:
            rotated_by_name = actor.username
    return {
        "provider": row.provider,
        "sender_id": row.sender_id,
        "channel": row.channel,
        "key_version": row.key_version,
        "rotated_at": row.rotated_at,
        "rotated_by_name": rotated_by_name,
    }


def credential_status(db: Session) -> dict[str, Any]:
    """Return credential metadata only, never the key or ciphertext.

    A database row always takes precedence over environment configuration, so a
    revoked row cannot silently fall back to a stale environment secret.
    """
    row = _row_for(db, CREDENTIAL_PROVIDER)
    if row is not None:
        configured = bool(row.is_active and row.api_key_ciphertext)
        error: str | None = None
        if configured:
            try:
                decrypt_api_key(row.api_key_ciphertext)
            except CredentialError as exc:
                configured = False
                error = str(exc)
        if configured and not (row.sender_id or "").strip():
            configured = False
            error = _INCOMPLETE_ERROR
        if configured and row.channel not in SUPPORTED_CHANNELS:
            configured = False
            error = _UNSUPPORTED_CHANNEL_ERROR
        metadata = _row_metadata(db, row)
        return {
            "credential_source": "database",
            "configured": configured,
            "credential_error": error,
            **metadata,
        }

    env_key = (settings.rasel_api_key or "").strip()
    env_sender = (settings.rasel_sender_id or "").strip()
    env_channel = (settings.rasel_channel or "local_sms").strip().lower()
    source = "environment" if (env_key or env_sender) else "none"
    configured = bool(
        env_key and env_sender and env_channel in SUPPORTED_CHANNELS
    )
    error = None
    if not configured:
        error = (
            _UNSUPPORTED_CHANNEL_ERROR
            if env_channel not in SUPPORTED_CHANNELS
            else _INCOMPLETE_ERROR
        )
    return {
        "credential_source": source,
        "configured": configured,
        "credential_error": error,
        "provider": CREDENTIAL_PROVIDER,
        "sender_id": env_sender or None,
        "channel": env_channel if source == "environment" else None,
        "key_version": None,
        "rotated_at": None,
        "rotated_by_name": None,
    }


def upsert_credential(
    db: Session,
    provider: str = CREDENTIAL_PROVIDER,
    api_key: str = "",
    sender_id: str | None = None,
    channel: str | None = None,
    user: User | None = None,
) -> ProviderCredential:
    """Encrypt and store a credential, rotating the key version.

    The caller owns the transaction and the audit record.
    """
    normalized_provider = (provider or CREDENTIAL_PROVIDER).strip().lower()
    normalized_channel = _normalize_channel(channel)
    ciphertext = encrypt_api_key(api_key)

    row = _row_for(db, normalized_provider)
    if row is None:
        row = ProviderCredential(
            provider=normalized_provider,
            key_version=0,
            is_active=True,
        )
        db.add(row)
    row.api_key_ciphertext = ciphertext
    row.sender_id = (sender_id or "").strip() or None
    row.channel = normalized_channel
    row.key_version = int(row.key_version or 0) + 1
    row.is_active = True
    row.rotated_at = datetime.now(timezone.utc)
    row.rotated_by = user.id if user is not None else None
    db.flush()
    return row


def revoke_credential(
    db: Session,
    provider: str = CREDENTIAL_PROVIDER,
    user: User | None = None,
) -> ProviderCredential | None:
    """Clear ciphertext and deactivate the stored credential."""
    row = _row_for(db, (provider or CREDENTIAL_PROVIDER).strip().lower())
    if row is None:
        return None
    row.api_key_ciphertext = None
    row.is_active = False
    row.rotated_at = datetime.now(timezone.utc)
    row.rotated_by = user.id if user is not None else None
    db.flush()
    return row


def credential_fingerprint(db: Session) -> CredentialFingerprint:
    """Return a secret-free fingerprint of the authoritative credential.

    A database row always wins over the environment, matching
    :func:`resolve_rasel_credentials`, so revocation/rotation is observable
    without revealing the key, sender, or ciphertext.
    """
    row = _row_for(db, CREDENTIAL_PROVIDER)
    if row is not None:
        return CredentialFingerprint(
            source="database",
            key_version=row.key_version,
            is_active=bool(row.is_active),
        )
    env_key = (settings.rasel_api_key or "").strip()
    env_sender = (settings.rasel_sender_id or "").strip()
    source = "environment" if (env_key or env_sender) else "none"
    return CredentialFingerprint(source=source, key_version=None, is_active=True)


def resolve_rasel_credentials(db: Session) -> ResolvedCredentials | None:
    """Resolve usable Rasel credentials for future worker integration.

    The database row wins over the environment.  A revoked, incomplete, or
    undecryptable row returns ``None`` rather than falling back to environment
    values, so revocation is authoritative.
    """
    row = _row_for(db, CREDENTIAL_PROVIDER)
    if row is not None:
        if not row.is_active or not row.api_key_ciphertext:
            return None
        try:
            key = decrypt_api_key(row.api_key_ciphertext)
        except CredentialError:
            return None
        sender = (row.sender_id or "").strip()
        channel = (row.channel or "").strip().lower()
        if not key or not sender or channel not in SUPPORTED_CHANNELS:
            return None
        return ResolvedCredentials(api_key=key, sender_id=sender, channel=channel)

    key = (settings.rasel_api_key or "").strip()
    sender = (settings.rasel_sender_id or "").strip()
    channel = (settings.rasel_channel or "local_sms").strip().lower()
    if not key or not sender or channel not in SUPPORTED_CHANNELS:
        return None
    return ResolvedCredentials(api_key=key, sender_id=sender, channel=channel)
