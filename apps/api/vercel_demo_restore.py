"""One-time restore of the synthetic FeeDesk demo dataset into the managed DB.

Enabled only when ``RESTORE_DEMO_DATA=true`` in the Vercel build environment.
Rows are inserted with ON CONFLICT DO NOTHING, so subsequent builds are safe.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Date, DateTime, Numeric, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Base, User

DATA_FILE = Path(__file__).with_name("vercel_demo_data.json")

TABLE_ORDER = (
    "guardians",
    "students",
    "guardian_contacts",
    "import_batches",
    "source_files",
    "staged_rows",
    "guardian_student_relationships",
    "fee_balances",
    "message_templates",
    "campaigns",
    "campaign_recipients",
    "messages",
    "send_jobs",
    "dashboard_metrics_daily",
)


def _decode(value: object, column: object) -> object:
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(str(value))
    if isinstance(column.type, Date):
        return date.fromisoformat(str(value))
    if isinstance(column.type, Numeric):
        return Decimal(str(value))
    return value


def _user_columns(table: object) -> set[str]:
    return {
        column.name
        for column in table.columns
        if any(fk.column.table.name == "users" for fk in column.foreign_keys)
    }


def restore() -> None:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))
        if admin_id is None:
            admin_id = db.scalar(select(User.id).where(User.role == "admin"))
        if admin_id is None:
            raise RuntimeError("No admin user exists for demo data ownership mapping")

        template_ids: dict[str, str] = {}
        for name in TABLE_ORDER:
            rows = payload.get(name) or []
            if not rows:
                print(f"demo restore: {name}: 0")
                continue
            table = Base.metadata.tables[name]
            users = _user_columns(table)
            decoded = []
            for raw in rows:
                row = {
                    column.name: _decode(raw.get(column.name), column)
                    for column in table.columns
                }
                for column_name in users:
                    row[column_name] = admin_id if raw.get(column_name) is not None else None
                if name == "campaigns" and row.get("template_id"):
                    row["template_id"] = template_ids.get(
                        str(row["template_id"]), str(row["template_id"])
                    )
                decoded.append(row)

            statement = pg_insert(table).on_conflict_do_nothing()
            db.execute(statement, decoded)
            db.flush()

            if name == "message_templates":
                # A production seed may already own the same name/version.
                # Map the local template id to the existing row so campaign
                # foreign keys remain valid without deleting production data.
                for raw in rows:
                    local_id = str(raw["id"])
                    present = db.scalar(
                        select(table.c.id).where(table.c.id == local_id)
                    )
                    if present:
                        template_ids[local_id] = local_id
                        continue
                    existing = db.scalar(
                        select(table.c.id).where(
                            table.c.name == raw["name"],
                            table.c.version == raw["version"],
                        )
                    )
                    if existing:
                        template_ids[local_id] = str(existing)

            print(f"demo restore: {name}: {len(decoded)}")

        db.commit()
        print("demo restore complete")


if __name__ == "__main__":
    if os.environ.get("RESTORE_DEMO_DATA", "").lower() not in {"1", "true", "yes"}:
        raise SystemExit("RESTORE_DEMO_DATA is not enabled")
    restore()
