from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IncomeCategory(Base):
    __tablename__ = "income_categories"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="income_categories_id_user_unique"),
        Index(
            "income_categories_user_active_name_unique",
            "user_id",
            text("lower(trim(name))"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("income_categories_user_id_index", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_expense_category: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class IncomeEntry(Base):
    __tablename__ = "income_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="income_entries_amount_positive"),
        ForeignKeyConstraint(["income_category_id", "user_id"], ["income_categories.id", "income_categories.user_id"], ondelete="RESTRICT", name="income_entries_income_category_user_fk"),
        ForeignKeyConstraint(["expense_category_id", "user_id"], ["categories.id", "categories.user_id"], ondelete="RESTRICT", name="income_entries_expense_category_user_fk"),
        ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT", name="income_entries_user_fk"),
        Index("income_entries_user_received_date_index", "user_id", "received_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    income_category_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expense_category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
