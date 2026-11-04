"""add send job claim fencing token

Revision ID: d1e2f3a4b5c6
Revises: c4f7a1b2d3e5
Create Date: 2026-11-04 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c4f7a1b2d3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "send_jobs",
        sa.Column("claim_token", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("send_jobs", "claim_token")
