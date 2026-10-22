"""add income categories and entries

Revision ID: 20261022_0006
Revises: 20261019_0005
Create Date: 2026-10-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261022_0006"
down_revision: str | None = "20261019_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "income_categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("requires_expense_category", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "income_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("income_category_id", sa.BigInteger(), nullable=False),
        sa.Column("expense_category_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="income_entries_amount_positive"),
        sa.ForeignKeyConstraint(["income_category_id"], ["income_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["expense_category_id"], ["categories.id"], ondelete="RESTRICT"),
    )
    op.create_index("income_entries_received_date_index", "income_entries", ["received_date"])
    op.create_index("income_entries_income_category_id_index", "income_entries", ["income_category_id"])
    op.create_index("income_entries_expense_category_id_index", "income_entries", ["expense_category_id"])


def downgrade() -> None:
    op.drop_index("income_entries_expense_category_id_index", table_name="income_entries")
    op.drop_index("income_entries_income_category_id_index", table_name="income_entries")
    op.drop_index("income_entries_received_date_index", table_name="income_entries")
    op.drop_table("income_entries")
    op.drop_table("income_categories")
