from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.modules.categories.model import Category
    from app.modules.payment_methods.model import PaymentMethod


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="expenses_amount_positive"),
        CheckConstraint(
            "installment_count BETWEEN 1 AND 1200",
            name="expenses_installment_count_valid",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    installment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    first_installment_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    payment_method_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("payment_methods.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    category: Mapped["Category"] = relationship(back_populates="expenses")
    payment_method: Mapped["PaymentMethod"] = relationship(back_populates="expenses")
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
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    expense_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense: Mapped[Expense] = relationship(back_populates="installments")
