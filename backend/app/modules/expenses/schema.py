from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_AMOUNT = Decimal("9999999999.99")
MAX_INSTALLMENT_COUNT = 1200


class ExpenseCreate(BaseModel):
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

    @model_validator(mode="after")
    def validate_payment_schedule(self) -> "ExpenseCreate":
        if self.payment_type == "one_time":
            if self.installment_count != 1:
                raise ValueError("Um gasto à vista deve ter uma parcela.")
            if self.amount_type != "total":
                raise ValueError("Informe o valor total para um gasto à vista.")
            if self.first_installment_date not in (None, self.expense_date):
                raise ValueError("A cobrança à vista deve ocorrer na data do gasto.")
        elif self.installment_count < 2:
            raise ValueError("Um gasto parcelado deve ter ao menos duas parcelas.")

        if self.first_installment_date is not None and self.first_installment_date < self.expense_date:
            raise ValueError("A primeira parcela não pode anteceder a data do gasto.")

        first_date = self.first_installment_date or self.expense_date
        final_month = (first_date.year - 1) * 12 + first_date.month - 1 + self.installment_count - 1
        final_year = final_month // 12 + 1
        if final_year > date.max.year:
            raise ValueError("O cronograma ultrapassa o intervalo de datas suportado.")

        total_amount = self.amount
        if self.payment_type == "installments" and self.amount_type == "installment":
            total_amount *= self.installment_count
        if total_amount > MAX_AMOUNT:
            raise ValueError("O valor total excede o limite permitido.")
        if self.payment_type == "installments" and self.amount_type == "total":
            total_cents = int(total_amount * 100)
            if self.installment_count > total_cents:
                raise ValueError("O valor não permite parcelas positivas para essa quantidade.")
        return self


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


class ExpenseMonthlyPaymentResponse(ExpenseResponse):
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


class ExpensePage(BaseModel):
    items: list[ExpenseInstallmentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


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
