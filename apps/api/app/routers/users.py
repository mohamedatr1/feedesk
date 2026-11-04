from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import get_db
from ..deps import require_csrf, require_permission
from ..errors import ApiError
from ..models import User, UserSession
from ..schemas import PasswordResetResponse, UserCreate, UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "job_title": user.job_title,
        "can_approve_campaigns": user.can_approve_campaigns,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
    }


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.asc())).all())


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    current: User = Depends(require_permission("users.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> User:
    if payload.can_approve_campaigns and current.role != "admin":
        raise ApiError(
            403,
            "FORBIDDEN",
            "يمكن لمدير النظام فقط منح صلاحية اعتماد الحملات.",
            "Only an administrator can grant campaign approval permission.",
        )

    username = payload.username.strip()
    if db.scalar(select(User).where(func.lower(User.username) == username.lower())):
        raise ApiError(409, "USERNAME_EXISTS", "اسم المستخدم مستخدم مسبقًا.", "Username already exists.")
    if payload.email and db.scalar(select(User).where(User.email == payload.email)):
        raise ApiError(409, "EMAIL_EXISTS", "البريد الإلكتروني مستخدم مسبقًا.", "Email already exists.")

    user = User(
        username=username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        job_title=payload.job_title,
        can_approve_campaigns=payload.can_approve_campaigns,
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        after=_user_dict(user),
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    current: User = Depends(require_permission("users.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "المستخدم غير موجود.", "User not found.")

    before = _user_dict(user)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("can_approve_campaigns") and current.role != "admin":
        raise ApiError(
            403,
            "FORBIDDEN",
            "يمكن لمدير النظام فقط منح صلاحية اعتماد الحملات.",
            "Only an administrator can grant campaign approval permission.",
        )
    if changes.get("is_active") is False and user.id == current.id:
        raise ApiError(400, "SELF_DEACTIVATE", "لا يمكنك تعطيل حسابك الحالي.", "You cannot deactivate your own account.")
    removes_active_admin = (
        user.role == "admin"
        and user.is_active
        and (changes.get("role") == "staff" or changes.get("is_active") is False)
    )
    if removes_active_admin:
        other_active_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == "admin",
                User.is_active.is_(True),
                User.id != user.id,
            )
        ) or 0
        if other_active_admins == 0:
            raise ApiError(
                400,
                "LAST_ADMIN",
                "لا يمكن إزالة آخر مدير نظام نشط.",
                "Cannot remove the last active administrator.",
            )
        if user.id == current.id and changes.get("role") == "staff":
            raise ApiError(
                400,
                "SELF_DEMOTE",
                "لا يمكنك خفض دورك الحالي. اطلب من مدير نظام آخر تعديله.",
                "You cannot demote your own account.",
            )
    if "email" in changes and changes["email"]:
        other = db.scalar(select(User).where(User.email == changes["email"], User.id != user.id))
        if other:
            raise ApiError(409, "EMAIL_EXISTS", "البريد الإلكتروني مستخدم مسبقًا.", "Email already exists.")

    for key, value in changes.items():
        setattr(user, key, value)

    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after=_user_dict(user),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(
    user_id: str,
    request: Request,
    current: User = Depends(require_permission("users.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "المستخدم غير موجود.", "User not found.")

    temporary = secrets.token_urlsafe(9)
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    user.failed_login_count = 0
    user.locked_until = None
    user.last_failed_login_at = None
    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)

    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return PasswordResetResponse(temporary_password=temporary)
