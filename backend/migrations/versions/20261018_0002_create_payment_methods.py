"""create payment methods

Revision ID: 20261018_0002
Revises: 20261017_0001
Create Date: 2026-10-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261018_0002"
down_revision: str | None = "20261017_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("name", name="payment_methods_name_unique"),
    )
    op.add_column(
        "expenses",
        sa.Column("payment_method_id", sa.BigInteger(), nullable=False),
    )
    op.create_foreign_key(
        "expenses_payment_method_id_fkey",
        "expenses",
        "payment_methods",
        ["payment_method_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "expenses_payment_method_id_index",
        "expenses",
        ["payment_method_id"],
    )


def downgrade() -> None:
    op.drop_index("expenses_payment_method_id_index", table_name="expenses")
    op.drop_constraint("expenses_payment_method_id_fkey", "expenses", type_="foreignkey")
    op.drop_column("expenses", "payment_method_id")
    op.drop_table("payment_methods")
