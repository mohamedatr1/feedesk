from __future__ import annotations

from sqlalchemy import func, select

from .campaigns.constants import DEFAULT_TEMPLATE_BODY, DEFAULT_TEMPLATE_NAME
from .config import settings
from .db import SessionLocal
from .models import MessageTemplate, SchoolSettings, User
from .security import hash_password

DEFAULT_SEED_PASSWORD = "ChangeMe!2026"


def ensure_seed_password_safe() -> None:
    """Refuse the well-known default seed password outside development.

    ``SEED_ALLOW_DEFAULT_PASSWORD=true`` is an explicit, documented override for
    isolated non-production environments (for example CI). It has no effect in
    production, where the settings validator rejects the default regardless.
    """
    if (
        settings.seed_admin_password == DEFAULT_SEED_PASSWORD
        and settings.app_env.lower() != "development"
        and not settings.seed_allow_default_password
    ):
        raise RuntimeError(
            "Refusing to seed the default admin password outside development. "
            "Set SEED_ADMIN_PASSWORD to a unique value, or explicitly set "
            "SEED_ALLOW_DEFAULT_PASSWORD=true for an isolated non-production database."
        )


def seed() -> None:
    ensure_seed_password_safe()
    with SessionLocal() as db:
        settings_row = db.get(SchoolSettings, 1)
        if settings_row is None:
            settings_row = SchoolSettings(
                id=1,
                school_name=settings.seed_school_name,
                default_currency=settings.seed_currency,
                currency_symbol=settings.seed_currency_symbol,
            )
            db.add(settings_row)
            db.flush()

        admin = db.scalar(
            select(User).where(
                func.lower(User.username) == settings.seed_admin_username.lower()
            )
        )
        if admin is None:
            admin = User(
                username=settings.seed_admin_username,
                password_hash=hash_password(settings.seed_admin_password),
                role="admin",
                job_title="مدير النظام",
                is_active=True,
                must_change_password=True,
            )
            db.add(admin)
            db.flush()
            print(f"Seeded admin user: {admin.username}")
            print("Temporary password is in SEED_ADMIN_PASSWORD in .env.local; change it on first login.")
        else:
            print(f"Admin user already exists: {admin.username}")

        active_template = db.scalar(
            select(MessageTemplate.id)
            .where(
                MessageTemplate.channel == "sms",
                MessageTemplate.language == "ar",
                MessageTemplate.is_active.is_(True),
            )
            .limit(1)
        )
        # Never rewrite an existing active template. Existing installations keep
        # their historical body; an admin must create and activate a new version
        # if they want the privacy-safe default that omits student names.
        if active_template is None:
            latest = db.scalar(
                select(MessageTemplate)
                .where(MessageTemplate.name == DEFAULT_TEMPLATE_NAME)
                .order_by(MessageTemplate.version.desc())
                .limit(1)
            )
            db.add(
                MessageTemplate(
                    name=DEFAULT_TEMPLATE_NAME,
                    language="ar",
                    channel="sms",
                    template_body=DEFAULT_TEMPLATE_BODY,
                    version=(latest.version + 1) if latest else 1,
                    is_active=True,
                    created_by=admin.id,
                )
            )
            print(f"Seeded default SMS template: {DEFAULT_TEMPLATE_NAME}")
        else:
            print("An active SMS template already exists; leaving templates unchanged.")

        db.commit()
        print(f"School settings ready: {settings_row.school_name} ({settings_row.default_currency})")


if __name__ == "__main__":
    seed()
