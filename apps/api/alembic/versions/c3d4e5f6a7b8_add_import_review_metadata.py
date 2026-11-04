"""add import review metadata

Revision ID: c3d4e5f6a7b8
Revises: b8c1d2e3f4a5
Create Date: 2026-11-03 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b8c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "import_batches",
        sa.Column("available_sheets", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("error_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("duplicate_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("confirmed_by", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_import_batches_confirmed_by_users",
        "import_batches",
        "users",
        ["confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "staged_rows",
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "staged_rows",
        sa.Column(
            "parser_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "staged_rows",
        sa.Column(
            "is_excluded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("staged_rows", "is_excluded")
    op.drop_column("staged_rows", "parser_warnings")
    op.drop_column("staged_rows", "position")
    op.drop_constraint(
        "fk_import_batches_confirmed_by_users", "import_batches", type_="foreignkey"
    )
    op.drop_column("import_batches", "confirmed_by")
    op.drop_column("import_batches", "duplicate_reason")
    op.drop_column("import_batches", "error_summary")
    op.drop_column("import_batches", "warnings")
    op.drop_column("import_batches", "column_mapping")
    op.drop_column("import_batches", "available_sheets")
