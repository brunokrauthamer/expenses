from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expense_date: date
    category_id: int = Field(gt=0)
    payment_method_id: int = Field(gt=0)

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("A descrição não pode ficar vazia.")
        return normalized_value


class ExpenseUpdate(ExpenseCreate):
    pass


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    amount: Decimal
    expense_date: date
    category_id: int
    payment_method_id: int
    created_at: datetime


class ExpensePage(BaseModel):
    items: list[ExpenseResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
