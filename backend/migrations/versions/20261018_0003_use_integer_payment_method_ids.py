"""use integer payment method ids

Revision ID: 20261018_0003
Revises: 20261018_0002
Create Date: 2026-10-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261018_0003"
down_revision: str | None = "20261018_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("expenses_payment_method_id_fkey", "expenses", type_="foreignkey")
    op.alter_column(
        "payment_methods",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="id::integer",
    )
    op.alter_column(
        "expenses",
        "payment_method_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="payment_method_id::integer",
    )
    op.create_foreign_key(
        "expenses_payment_method_id_fkey",
        "expenses",
        "payment_methods",
        ["payment_method_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("expenses_payment_method_id_fkey", "expenses", type_="foreignkey")
    op.alter_column(
        "expenses",
        "payment_method_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="payment_method_id::bigint",
    )
    op.alter_column(
        "payment_methods",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="id::bigint",
    )
    op.create_foreign_key(
        "expenses_payment_method_id_fkey",
        "expenses",
        "payment_methods",
        ["payment_method_id"],
        ["id"],
        ondelete="RESTRICT",
    )
