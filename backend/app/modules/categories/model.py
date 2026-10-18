from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.modules.expenses.model import Expense


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    expenses: Mapped[list["Expense"]] = relationship(back_populates="category")
