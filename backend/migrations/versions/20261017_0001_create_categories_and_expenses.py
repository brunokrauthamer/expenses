"""create categories and expenses tables

Revision ID: 20261017_0001
Revises:
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261017_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("name", name="categories_name_unique"),
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("description", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="expenses_amount_positive"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT", name="expenses_category_id_fkey"
        ),
    )
    op.create_index("expenses_category_id_index", "expenses", ["category_id"])
    op.create_index("expenses_expense_date_index", "expenses", ["expense_date"])


def downgrade() -> None:
    op.drop_index("expenses_expense_date_index", table_name="expenses")
    op.drop_index("expenses_category_id_index", table_name="expenses")
    op.drop_table("expenses")
    op.drop_table("categories")
