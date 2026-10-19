"""add expense installments

Revision ID: 20261018_0004
Revises: 20261018_0003
Create Date: 2026-10-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261018_0004"
down_revision: str | None = "20261018_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("installment_count", sa.Integer(), server_default="1", nullable=True),
    )
    op.add_column(
        "expenses",
        sa.Column("first_installment_date", sa.Date(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE expenses "
            "SET installment_count = 1, first_installment_date = expense_date"
        )
    )
    op.alter_column(
        "expenses",
        "installment_count",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "expenses",
        "first_installment_date",
        existing_type=sa.Date(),
        nullable=False,
    )
    op.create_check_constraint(
        "expenses_installment_count_valid",
        "expenses",
        "installment_count BETWEEN 1 AND 1200",
    )

    op.create_table(
        "expense_installments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("expense_id", sa.BigInteger(), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "installment_number > 0", name="expense_installments_number_positive"
        ),
        sa.CheckConstraint("amount > 0", name="expense_installments_amount_positive"),
        sa.ForeignKeyConstraint(
            ["expense_id"], ["expenses.id"], ondelete="CASCADE",
            name="expense_installments_expense_id_fkey",
        ),
        sa.UniqueConstraint(
            "expense_id", "installment_number",
            name="expense_installments_number_unique",
        ),
    )
    op.create_index(
        "expense_installments_due_date_index", "expense_installments", ["due_date"]
    )
    op.create_index(
        "expense_installments_expense_id_index", "expense_installments", ["expense_id"]
    )
    op.execute(
        sa.text(
            "INSERT INTO expense_installments "
            "(expense_id, installment_number, amount, due_date) "
            "SELECT id, 1, amount, expense_date FROM expenses"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "expense_installments_expense_id_index", table_name="expense_installments"
    )
    op.drop_index("expense_installments_due_date_index", table_name="expense_installments")
    op.drop_table("expense_installments")
    op.drop_constraint("expenses_installment_count_valid", "expenses", type_="check")
    op.drop_column("expenses", "first_installment_date")
    op.drop_column("expenses", "installment_count")
