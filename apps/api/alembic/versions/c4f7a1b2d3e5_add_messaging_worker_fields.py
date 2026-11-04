"""add messaging provider payload and worker lease fields

Revision ID: c4f7a1b2d3e5
Revises: a9b8c7d6e5f4
Create Date: 2026-11-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4f7a1b2d3e5"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "provider_payload_redacted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "send_jobs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "send_jobs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_send_jobs_lease_expires_at",
        "send_jobs",
        ["lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_send_jobs_lease_expires_at", table_name="send_jobs")
    op.drop_column("send_jobs", "heartbeat_at")
    op.drop_column("send_jobs", "lease_expires_at")
    op.drop_column("messages", "provider_payload_redacted")
