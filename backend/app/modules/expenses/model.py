from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="expenses_amount_positive"),
        CheckConstraint(
            "installment_count BETWEEN 1 AND 1200",
            name="expenses_installment_count_valid",
        ),
        UniqueConstraint("id", "user_id", name="expenses_id_user_unique"),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            ondelete="RESTRICT",
            name="expenses_category_user_fk",
        ),
        ForeignKeyConstraint(
            ["payment_method_id", "user_id"],
            ["payment_methods.id", "payment_methods.user_id"],
            ondelete="RESTRICT",
            name="expenses_payment_method_user_fk",
        ),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT", name="expenses_user_fk"
        ),
        Index("expenses_user_expense_date_index", "user_id", "expense_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    installment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    first_installment_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_method_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    installments: Mapped[list["ExpenseInstallment"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def payment_type(self) -> str:
        return "one_time" if self.installment_count == 1 else "installments"


class ExpenseInstallment(Base):
    __tablename__ = "expense_installments"
    __table_args__ = (
        CheckConstraint("installment_number > 0", name="expense_installments_number_positive"),
        CheckConstraint("amount > 0", name="expense_installments_amount_positive"),
        UniqueConstraint(
            "expense_id", "installment_number", name="expense_installments_number_unique"
        ),
        Index("expense_installments_expense_due_date_index", "expense_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense: Mapped[Expense] = relationship(back_populates="installments")


class ExpenseImportSource(Base):
    """Rastreia linhas de origem para tornar a importação repetível sem duplicatas."""

    __tablename__ = "expense_import_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "source_key", name="expense_import_sources_user_source_unique"),
        ForeignKeyConstraint(
            ["expense_id", "user_id"],
            ["expenses.id", "expenses.user_id"],
            ondelete="CASCADE",
            name="expense_import_sources_expense_user_fk",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    expense_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
