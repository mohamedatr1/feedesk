"""add import summary aggregate fields

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-11-03 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "import_batches",
        sa.Column(
            "excluded_rows",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column(
            "totals_by_currency",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill derived aggregates for any batches staged before this revision.
    op.execute(
        """
        UPDATE import_batches AS b
        SET excluded_rows = (
            SELECT count(*) FROM staged_rows AS s
            WHERE s.import_batch_id = b.id AND s.is_excluded = true
        )
        """
    )
    op.execute(
        """
        UPDATE import_batches AS b
        SET totals_by_currency = COALESCE((
            SELECT jsonb_object_agg(x.currency, x.total)
            FROM (
                SELECT
                    s.normalized_data->>'currency' AS currency,
                    sum((s.normalized_data->>'remaining_balance')::numeric(18, 2))::text AS total
                FROM staged_rows AS s
                WHERE s.import_batch_id = b.id
                  AND s.is_excluded = false
                  AND s.validation_status <> 'invalid'
                  AND s.normalized_data->>'currency' IS NOT NULL
                  AND s.normalized_data->>'remaining_balance'
                      ~ '^-?[0-9]+(\\.[0-9]+)?$'
                GROUP BY 1
            ) AS x
        ), '{}'::jsonb)
        """
    )


def downgrade() -> None:
    op.drop_column("import_batches", "cancelled_at")
    op.drop_column("import_batches", "updated_at")
    op.drop_column("import_batches", "totals_by_currency")
    op.drop_column("import_batches", "excluded_rows")
