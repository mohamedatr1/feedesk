from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Response

from .config import settings

if TYPE_CHECKING:
    from .models import User

password_hasher = PasswordHasher()
# Verified against when a username does not exist, so unknown-user logins take
# approximately the same time as a wrong-password login.
DUMMY_PASSWORD_HASH = password_hasher.hash("feedesk-timing-equalization")

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "staff": {
        "dashboard.view",
        "files.download",
        "imports.view",
        "imports.upload",
        "imports.review",
        "imports.confirm",
        "finance.view",
        "guardians.view",
        "campaigns.view",
        "campaigns.create",
        "campaigns.edit",
        "campaigns.preview",
        "campaigns.submit",
        "messages.view",
        "settings.view",
        "templates.view",
    },
}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _role_and_approval_flag(principal: User | str) -> tuple[str, bool]:
    if isinstance(principal, str):
        return principal, False
    return principal.role, bool(principal.can_approve_campaigns)


def permissions_for(principal: User | str) -> list[str]:
    role, can_approve_campaigns = _role_and_approval_flag(principal)
    perms = set(ROLE_PERMISSIONS.get(role, set()))
    if can_approve_campaigns:
        # Per-user delegation is deliberately narrow: it only unlocks approval.
        perms.add("campaigns.approve")
    return ["*"] if "*" in perms else sorted(perms)


def has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def user_has_permission(user: User, permission: str) -> bool:
    if has_permission(user.role, permission):
        return True
    return permission == "campaigns.approve" and bool(user.can_approve_campaigns)


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def csrf_matches(expected: str, provided: str | None) -> bool:
    if not provided:
        return False
    return hmac.compare_digest(expected, provided)
