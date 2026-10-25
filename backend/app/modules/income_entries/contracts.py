"""Application commands and snapshots for income entries."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class IncomeEntryCommand:
    description: str
    amount: Decimal
    received_date: date
    income_category_id: int
    expense_category_id: int | None


@dataclass(frozen=True)
class IncomeEntryState:
    id: int
    income_category_id: int
    expense_category_id: int | None
