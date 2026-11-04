"""restrict audit actor deletion

Revision ID: 9f1c2b7a4d10
Revises: 2ee42a46e58c
Create Date: 2026-11-03 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "9f1c2b7a4d10"
down_revision: Union[str, Sequence[str], None] = "2ee42a46e58c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("audit_events_actor_user_id_fkey", "audit_events", type_="foreignkey")
    op.create_foreign_key(
        "audit_events_actor_user_id_fkey",
        "audit_events",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("audit_events_actor_user_id_fkey", "audit_events", type_="foreignkey")
    op.create_foreign_key(
        "audit_events_actor_user_id_fkey",
        "audit_events",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
