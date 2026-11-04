from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..db import get_db
from ..deps import client_ip, get_current_session, require_csrf
from ..errors import ApiError
from ..models import AuditEvent, User, UserSession
from ..schemas import ChangePasswordRequest, LoginRequest, LoginResponse, MeResponse, UserOut
from ..security import (
    DUMMY_PASSWORD_HASH,
    clear_session_cookie,
    hash_password,
    hash_token,
    new_csrf_token,
    new_session_token,
    permissions_for,
    session_expiry,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _check_rate_limit(db: Session, ip: str, now: datetime) -> None:
    since = now - timedelta(seconds=settings.login_rate_window_seconds)
    attempts = db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.action.in_(("auth.login_failed", "auth.login_blocked")),
            AuditEvent.ip_address == ip,
            AuditEvent.created_at >= since,
        )
    ) or 0
    if attempts >= settings.login_rate_limit:
        raise ApiError(
            429,
            "RATE_LIMITED",
            "محاولات تسجيل دخول كثيرة. حاول بعد قليل.",
            "Too many login attempts. Try again shortly.",
        )


def _expire_stale_lockout(user: User, now: datetime) -> None:
    if user.locked_until is not None and user.locked_until <= now:
        user.locked_until = None
        user.failed_login_count = 0
        user.last_failed_login_at = None
        return
    if user.last_failed_login_at is not None and (
        now - user.last_failed_login_at > timedelta(minutes=settings.login_lockout_minutes)
    ):
        user.failed_login_count = 0
        user.last_failed_login_at = None


def _record_login_failure(
    db: Session,
    request: Request,
    user: User | None,
    username: str,
    reason: str,
    now: datetime,
) -> bool:
    failed_count = None
    locked = False
    if user is not None and user.is_active:
        failed_count = (user.failed_login_count or 0) + 1
        user.failed_login_count = failed_count
        user.last_failed_login_at = now
        if failed_count >= settings.login_lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            locked = True
    record_audit(
        db,
        request=request,
        actor_user_id=None,
        action="auth.login_failed",
        entity_type="user" if user is not None else "auth",
        entity_id=user.id if user is not None else None,
        before=None,
        after={
            "username": username,
            "reason": reason,
            "failed_login_count": failed_count,
            "locked": locked,
        },
    )
    db.commit()
    return locked


def _account_locked_error(retry_after_seconds: int) -> ApiError:
    return ApiError(
        429,
        "ACCOUNT_LOCKED",
        "تم قفل الحساب مؤقتًا بعد محاولات دخول فاشلة. حاول بعد قليل.",
        "Account temporarily locked after repeated failed logins.",
        {"retry_after_seconds": retry_after_seconds},
    )


def _record_login_blocked(
    db: Session, request: Request, user: User, retry_after_seconds: int
) -> None:
    record_audit(
        db,
        request=request,
        actor_user_id=None,
        action="auth.login_blocked",
        entity_type="user",
        entity_id=user.id,
        after={
            "username": user.username,
            "retry_after_seconds": retry_after_seconds,
        },
    )
    db.commit()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    ip = client_ip(request) or "unknown"
    now = datetime.now(timezone.utc)
    _check_rate_limit(db, ip, now)

    username = payload.username.strip()
    user = db.scalar(select(User).where(func.lower(User.username) == username.lower()))

    if user is not None:
        _expire_stale_lockout(user, now)
        if user.locked_until is not None and user.locked_until > now:
            retry_after = max(1, int((user.locked_until - now).total_seconds()))
            _record_login_blocked(db, request, user, retry_after)
            raise _account_locked_error(retry_after)
    else:
        # Equalize timing with a real password verification.
        verify_password(payload.password, DUMMY_PASSWORD_HASH)

    if user is not None and not verify_password(payload.password, user.password_hash):
        locked = _record_login_failure(
            db, request, user, username, "invalid_credentials", now
        )
        if locked:
            raise _account_locked_error(settings.login_lockout_minutes * 60)
        raise ApiError(401, "INVALID_CREDENTIALS", "اسم المستخدم أو كلمة المرور غير صحيحة.", "Invalid credentials.")
    if user is None:
        _record_login_failure(db, request, user, username, "invalid_credentials", now)
        raise ApiError(401, "INVALID_CREDENTIALS", "اسم المستخدم أو كلمة المرور غير صحيحة.", "Invalid credentials.")
    if not user.is_active:
        _record_login_failure(db, request, user, username, "inactive", now)
        raise ApiError(401, "INVALID_CREDENTIALS", "اسم المستخدم أو كلمة المرور غير صحيحة.", "Invalid credentials.")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_failed_login_at = None

    token = new_session_token()
    csrf = new_csrf_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token=csrf,
        expires_at=session_expiry(),
        ip_address=ip,
        user_agent=(request.headers.get("user-agent") or "")[:500],
    )
    user.last_login_at = now
    db.add(session)
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()

    set_session_cookie(response, token)
    return LoginResponse(
        user=UserOut.model_validate(user),
        permissions=permissions_for(user),
        csrf_token=csrf,
    )


@router.get("/me", response_model=MeResponse)
def me(
    current: tuple[User, UserSession] = Depends(get_current_session),
) -> MeResponse:
    user, session = current
    return MeResponse(
        user=UserOut.model_validate(user),
        permissions=permissions_for(user),
        csrf_token=session.csrf_token,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current: tuple[User, UserSession] = Depends(get_current_session),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user, session = current
    session.revoked_at = datetime.now(timezone.utc)
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="auth.logout",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current: tuple[User, UserSession] = Depends(get_current_session),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user, session = current
    if not verify_password(payload.current_password, user.password_hash):
        raise ApiError(400, "INVALID_PASSWORD", "كلمة المرور الحالية غير صحيحة.", "Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise ApiError(400, "SAME_PASSWORD", "كلمة المرور الجديدة يجب أن تختلف عن الحالية.", "New password must differ.")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.id != session.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="auth.password_change",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return {"ok": True}
