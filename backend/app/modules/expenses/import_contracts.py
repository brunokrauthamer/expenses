"""Commands used to apply a reviewed spreadsheet import."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ImportExpenseCommand:
    description: str
    category_name: str
    payment_method_name: str
    expense_date: date
    amounts: tuple[Decimal, ...]
    source_keys: tuple[str, ...]


@dataclass(frozen=True)
class ImportedInstallment:
    number: int
    amount: Decimal
    due_date: date
