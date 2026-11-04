from __future__ import annotations

import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres@127.0.0.1:55432/feedesk_test",
)
TEST_DB = make_url(TEST_DATABASE_URL).database or "feedesk_test"
ADMIN_URL = os.environ.get("TEST_DATABASE_ADMIN_URL") or (
    make_url(TEST_DATABASE_URL)
    .set(drivername="postgresql", database="postgres")
    .render_as_string(hide_password=False)
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["LOGIN_RATE_LIMIT"] = "1000"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import SchoolSettings, User  # noqa: E402
from app.security import hash_password  # noqa: E402


def _install_audit_trigger() -> None:
    """Mirror the append-only trigger created by the Alembic migration.

    Tests build the schema with ``Base.metadata.create_all``, which does not run
    migration DDL, so the trigger must be installed explicitly.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION prevent_audit_mutation()
                RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_events is append-only';
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        connection.execute(
            text("DROP TRIGGER IF EXISTS audit_events_no_update_delete ON audit_events")
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER audit_events_no_update_delete
                BEFORE UPDATE OR DELETE ON audit_events
                FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
                """
            )
        )
        connection.execute(
            text("DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events")
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER audit_events_no_truncate
                BEFORE TRUNCATE ON audit_events
                FOR EACH STATEMENT EXECUTE FUNCTION prevent_audit_mutation();
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower
                ON users (lower(username))
                """
            )
        )


def _ensure_database() -> None:
    conn = psycopg.connect(ADMIN_URL, autocommit=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB)))
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    _ensure_database()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _install_audit_trigger()
    with SessionLocal() as db:
        db.add(
            SchoolSettings(
                id=1,
                school_name="مدرسة الاختبار",
                default_currency="SYP",
                currency_symbol="د.س",
                timezone="Asia/Damascus",
                locale="ar-SY",
                contact_phone="+963900000000",
                contact_email="test@example.com",
                send_limit=100,
                batch_limit=100,
            )
        )
        db.add_all(
            [
                User(
                    username="admin_test",
                    password_hash=hash_password("AdminTest!2026"),
                    role="admin",
                    job_title="مدير النظام",
                    is_active=True,
                    must_change_password=False,
                ),
                User(
                    username="staff_test",
                    password_hash=hash_password("StaffTest!2026"),
                    role="staff",
                    job_title="موظف إداري",
                    is_active=True,
                    must_change_password=False,
                ),
                User(
                    username="must_change_test",
                    password_hash=hash_password("MustChange!2026"),
                    role="staff",
                    is_active=True,
                    must_change_password=True,
                ),
            ]
        )
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


@pytest.fixture()
def admin_client() -> tuple[TestClient, str]:
    client = TestClient(app)
    return client, login(client, "admin_test", "AdminTest!2026")


@pytest.fixture()
def staff_client() -> tuple[TestClient, str]:
    client = TestClient(app)
    return client, login(client, "staff_test", "StaffTest!2026")
