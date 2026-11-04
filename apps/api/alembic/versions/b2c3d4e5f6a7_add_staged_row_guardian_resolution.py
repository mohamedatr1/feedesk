"""add staged row guardian resolution

Revision ID: b2c3d4e5f6a7
Revises: f7b8c9d0e1f2
Create Date: 2026-11-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staged_rows",
        sa.Column(
            "guardian_resolution_mode",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'auto'"),
        ),
    )
    op.add_column(
        "staged_rows",
        sa.Column("resolved_guardian_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_staged_rows_resolved_guardian_id",
        "staged_rows",
        ["resolved_guardian_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_staged_rows_resolved_guardian_id_guardians",
        "staged_rows",
        "guardians",
        ["resolved_guardian_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_staged_rows_resolved_guardian_id_guardians",
        "staged_rows",
        type_="foreignkey",
    )
    op.drop_index("ix_staged_rows_resolved_guardian_id", table_name="staged_rows")
    op.drop_column("staged_rows", "resolved_guardian_id")
    op.drop_column("staged_rows", "guardian_resolution_mode")
