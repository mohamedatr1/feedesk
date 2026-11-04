from __future__ import annotations

import ipaddress
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .errors import ApiError
from .models import User, UserSession
from .security import csrf_matches, hash_token, user_has_permission


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request) -> str | None:
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = _valid_ip(forwarded.split(",", 1)[0])
            if candidate:
                return candidate
    return request.client.host[:64] if request.client and request.client.host else None


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
) -> tuple[User, UserSession]:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "يجب تسجيل الدخول للمتابعة.", "Authentication required.")

    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    now = datetime.now(timezone.utc)
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise ApiError(401, "SESSION_EXPIRED", "انتهت الجلسة. يرجى تسجيل الدخول مجددًا.", "Session expired.")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "UNAUTHORIZED", "الحساب غير نشط.", "Inactive account.")

    request.state.user = user
    request.state.session = session
    return user, session


def require_permission(permission: str) -> Callable:
    def dependency(
        request: Request,
        current: tuple[User, UserSession] = Depends(get_current_session),
    ) -> User:
        user, _ = current
        if user.must_change_password:
            raise ApiError(
                403,
                "PASSWORD_CHANGE_REQUIRED",
                "يجب تغيير كلمة المرور قبل المتابعة.",
                "Password change required.",
            )
        if not user_has_permission(user, permission):
            raise ApiError(403, "FORBIDDEN", "ليس لديك صلاحية لهذا الإجراء.", "Permission denied.")
        return user

    return dependency


def require_csrf(
    request: Request,
    current: tuple[User, UserSession] = Depends(get_current_session),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    _, session = current
    provided = request.headers.get("x-csrf-token")
    if not csrf_matches(session.csrf_token, provided):
        raise ApiError(403, "CSRF_INVALID", "رمز الحماية غير صالح. أعد تحميل الصفحة.", "Invalid CSRF token.")
