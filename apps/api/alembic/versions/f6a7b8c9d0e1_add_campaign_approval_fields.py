"""add campaign approval fields and recipient immutability

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-03 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "recipient_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "excluded_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "invalid_contact_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "totals_by_currency",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "preview_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "revision", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column("previewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("cancelled_by", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("cancel_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_campaigns_cancelled_by_users",
        "campaigns",
        "users",
        ["cancelled_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_message_templates_name_version",
        "message_templates",
        ["name", "version"],
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_approved_campaign_recipient_mutation()
        RETURNS trigger AS $$
        DECLARE
            target_campaign_id text;
            campaign_status text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                target_campaign_id := OLD.campaign_id;
            ELSE
                target_campaign_id := NEW.campaign_id;
            END IF;
            SELECT status INTO campaign_status
            FROM campaigns
            WHERE id = target_campaign_id;
            IF campaign_status IN (
                'approved',
                'queued',
                'sending',
                'completed',
                'completed_with_errors'
            ) THEN
                RAISE EXCEPTION
                    'campaign_recipients is immutable while campaign is %',
                    campaign_status;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER campaign_recipients_immutable
        BEFORE UPDATE OR DELETE ON campaign_recipients
        FOR EACH ROW EXECUTE FUNCTION prevent_approved_campaign_recipient_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS campaign_recipients_immutable ON campaign_recipients;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS prevent_approved_campaign_recipient_mutation();"
    )
    op.drop_constraint(
        "uq_message_templates_name_version", "message_templates", type_="unique"
    )
    op.drop_constraint(
        "fk_campaigns_cancelled_by_users", "campaigns", type_="foreignkey"
    )
    op.drop_column("campaigns", "cancel_reason")
    op.drop_column("campaigns", "cancelled_by")
    op.drop_column("campaigns", "cancelled_at")
    op.drop_column("campaigns", "submitted_at")
    op.drop_column("campaigns", "previewed_at")
    op.drop_column("campaigns", "revision")
    op.drop_column("campaigns", "preview_snapshot")
    op.drop_column("campaigns", "warnings")
    op.drop_column("campaigns", "totals_by_currency")
    op.drop_column("campaigns", "invalid_contact_count")
    op.drop_column("campaigns", "excluded_count")
    op.drop_column("campaigns", "recipient_count")
