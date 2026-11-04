"""harden identity and audit

Revision ID: b8c1d2e3f4a5
Revises: a7d3e9b1c4f2
Create Date: 2026-11-03 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a7d3e9b1c4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION prevent_audit_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events;")
    op.drop_index("uq_users_username_lower", table_name="users")
