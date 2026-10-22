from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IncomeCategory(Base):
    __tablename__ = "income_categories"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    requires_expense_category: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class IncomeEntry(Base):
    __tablename__ = "income_entries"
    __table_args__ = (CheckConstraint("amount > 0", name="income_entries_amount_positive"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    income_category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("income_categories.id", ondelete="RESTRICT"), nullable=False)
    expense_category_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
