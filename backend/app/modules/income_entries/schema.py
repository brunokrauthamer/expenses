from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    requires_expense_category: bool


class IncomeEntryCreate(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    received_date: date
    income_category_id: int = Field(gt=0)
    expense_category_id: int | None = Field(default=None, gt=0)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A descrição não pode ficar vazia.")
        return value


class IncomeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    amount: Decimal
    received_date: date
    income_category_id: int
    expense_category_id: int | None
    created_at: datetime


class IncomeEntryPage(BaseModel):
    items: list[IncomeEntryResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
