"""Financial rules for validating and building an expense schedule."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared.exceptions import DomainValidationError

MAX_AMOUNT = Decimal("9999999999.99")
MAX_INSTALLMENT_COUNT = 1200


@dataclass(frozen=True)
class InstallmentSpec:
    number: int
    amount: Decimal
    due_date: date


def validate_payment_schedule(
    *,
    payment_type: str,
    amount_type: str,
    amount: Decimal,
    installment_count: int,
    expense_date: date,
    first_installment_date: date | None,
) -> None:
    if payment_type == "one_time":
        if installment_count != 1:
            raise DomainValidationError("Um gasto à vista deve ter uma parcela.")
        if amount_type != "total":
            raise DomainValidationError("Informe o valor total para um gasto à vista.")
        if first_installment_date not in (None, expense_date):
            raise DomainValidationError("A cobrança à vista deve ocorrer na data do gasto.")
    elif installment_count < 2:
        raise DomainValidationError("Um gasto parcelado deve ter ao menos duas parcelas.")

    if first_installment_date is not None and first_installment_date < expense_date:
        raise DomainValidationError("A primeira parcela não pode anteceder a data do gasto.")

    first_date = first_installment_date or expense_date
    final_month = (first_date.year - 1) * 12 + first_date.month - 1 + installment_count - 1
    final_year = final_month // 12 + 1
    if final_year > date.max.year:
        raise DomainValidationError("O cronograma ultrapassa o intervalo de datas suportado.")

    total = total_amount(amount, amount_type, payment_type, installment_count)
    if total > MAX_AMOUNT:
        raise DomainValidationError("O valor total excede o limite permitido.")
    if payment_type == "installments" and amount_type == "total":
        if installment_count > int(total * 100):
            raise DomainValidationError(
                "O valor não permite parcelas positivas para essa quantidade."
            )


def total_amount(
    amount: Decimal, amount_type: str, payment_type: str, installment_count: int
) -> Decimal:
    if payment_type == "installments" and amount_type == "installment":
        return amount * installment_count
    return amount


def build_installments(*, total: Decimal, count: int, first_date: date) -> list[InstallmentSpec]:
    total_cents = int(total * 100)
    installment_cents = total_cents // count
    first_installment_cents = total_cents - (count - 1) * installment_cents
    installments: list[InstallmentSpec] = []

    for index in range(count):
        month_index = (first_date.year - 1) * 12 + first_date.month - 1 + index
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        day = min(first_date.day, monthrange(year + 1, month)[1])
        amount_cents = first_installment_cents if index == 0 else installment_cents
        installments.append(
            InstallmentSpec(
                number=index + 1,
                amount=Decimal(amount_cents) / 100,
                due_date=date(year + 1, month, day),
            )
        )
    return installments
