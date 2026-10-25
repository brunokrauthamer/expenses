from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.expenses.rules import MAX_INSTALLMENT_COUNT


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    amount_type: Literal["total", "installment"] = "total"
    payment_type: Literal["one_time", "installments"] = "one_time"
    installment_count: int = Field(default=1, ge=1, le=MAX_INSTALLMENT_COUNT, strict=True)
    expense_date: date
    first_installment_date: date | None = None
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
    total_amount: Decimal = Field(validation_alias="amount")
    expense_date: date
    payment_type: str
    installment_count: int
    first_installment_date: date
    category_id: int
    payment_method_id: int
    created_at: datetime
    category_name: str | None = None
    category_deleted: bool | None = None
    payment_method_name: str | None = None
    payment_method_deleted: bool | None = None


class ExpenseMonthlyPaymentResponse(ExpenseResponse):
    due_date: date
    installment_number: int
    installment_amount: Decimal


class ExpenseInstallmentResponse(BaseModel):
    id: int
    installment_id: int
    description: str
    expense_date: date
    due_date: date
    payment_type: str
    installment_number: int
    installment_count: int
    first_installment_date: date
    amount_due: Decimal
    total_amount: Decimal
    category_id: int
    payment_method_id: int
    category_name: str | None = None
    category_deleted: bool | None = None
    payment_method_name: str | None = None
    payment_method_deleted: bool | None = None


class ExpensePage(BaseModel):
    items: list[ExpenseInstallmentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ExpenseHistoryItem(BaseModel):
    kind: Literal["expense", "reimbursement"]
    id: int
    installment_id: int | None = None
    description: str
    event_date: date
    amount: Decimal
    category_id: int
    payment_method_id: int | None = None
    payment_type: str | None = None
    installment_number: int | None = None
    installment_count: int | None = None
    first_installment_date: date | None = None
    total_amount: Decimal | None = None
    category_name: str | None = None
    category_deleted: bool | None = None
    payment_method_name: str | None = None
    payment_method_deleted: bool | None = None
    income_category_name: str | None = None
    income_category_deleted: bool | None = None


class ExpenseHistoryPage(BaseModel):
    items: list[ExpenseHistoryItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    gross_expense_amount: Decimal
    reimbursement_amount: Decimal
    net_expense_amount: Decimal


class ExpenseMonthTotal(BaseModel):
    month: str
    amount_due: Decimal
    gross_expense_amount: Decimal
    reimbursement_amount: Decimal
    net_expense_amount: Decimal


class ExpenseCategoryTotal(BaseModel):
    category_id: int
    amount_due: Decimal
    gross_expense_amount: Decimal
    reimbursement_amount: Decimal
    net_expense_amount: Decimal


class ExpenseSummaryResponse(BaseModel):
    total_amount_due: Decimal
    gross_expense_amount: Decimal
    reimbursement_amount: Decimal
    net_expense_amount: Decimal
    monthly_totals: list[ExpenseMonthTotal]
    category_totals: list[ExpenseCategoryTotal]
