"""add expense import sources

Revision ID: 20261019_0005
Revises: 20261018_0004
Create Date: 2026-10-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261019_0005"
down_revision: str | None = "20261018_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "expense_import_sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("expense_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["expense_id"], ["expenses.id"], ondelete="CASCADE",
            name="expense_import_sources_expense_id_fkey",
        ),
        sa.UniqueConstraint(
            "source_key", name="expense_import_sources_source_key_unique"
        ),
    )
    op.create_index(
        "expense_import_sources_expense_id_index",
        "expense_import_sources", ["expense_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "expense_import_sources_expense_id_index",
        table_name="expense_import_sources",
    )
    op.drop_table("expense_import_sources")
