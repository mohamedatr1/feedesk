"""persist campaign excluded snapshot

Revision ID: a9b8c7d6e5f4
Revises: f6a7b8c9d0e1
Create Date: 2026-11-04 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "excluded_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Backfill previously computed previews so existing campaigns retain the
    # excluded records that were visible at their last preview/approval.
    op.execute(
        """
        UPDATE campaigns
        SET excluded_snapshot = COALESCE(
            preview_snapshot -> 'excluded',
            '[]'::jsonb
        )
        """
    )


def downgrade() -> None:
    op.drop_column("campaigns", "excluded_snapshot")
