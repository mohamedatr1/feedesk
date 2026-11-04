"""Vercel build hook: apply migrations and seed the managed database.

The local workstation cannot reach the Neon endpoint, so this runs from the
Vercel build environment where the production DATABASE_URL is available.
"""

from __future__ import annotations

import os

from alembic.config import Config

from alembic import command


def main() -> None:
    direct_url = (os.environ.get("DATABASE_URL_UNPOOLED") or "").strip()
    if direct_url:
        os.environ["DATABASE_URL"] = direct_url

    command.upgrade(Config("alembic.ini"), "head")

    from app.seed import seed

    seed()

    if os.environ.get("RESTORE_DEMO_DATA", "").lower() in {"1", "true", "yes"}:
        from vercel_demo_restore import restore

        restore()


if __name__ == "__main__":
    main()
