from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeCategoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value


class IncomeCategoryCreate(IncomeCategoryInput):
    requires_expense_category: bool = False


class IncomeCategoryUpdate(IncomeCategoryInput):
    requires_expense_category: bool | None = None


class IncomeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    requires_expense_category: bool
    deleted_at: datetime | None


class IncomeEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    income_category_name: str | None = None
    income_category_deleted: bool | None = None
    expense_category_name: str | None = None
    expense_category_deleted: bool | None = None


class IncomeEntryPage(BaseModel):
    items: list[IncomeEntryResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
