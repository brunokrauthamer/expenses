"""Application commands and persisted expense snapshots."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ExpenseCommand:
    description: str
    amount: Decimal
    amount_type: str
    payment_type: str
    installment_count: int
    expense_date: date
    first_installment_date: date | None
    category_id: int
    payment_method_id: int


@dataclass(frozen=True)
class ExpenseState:
    id: int
    amount: Decimal
    expense_date: date
    installment_count: int
    first_installment_date: date
    category_id: int
    payment_method_id: int
