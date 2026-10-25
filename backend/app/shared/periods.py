"""Pure validation for inclusive year-month filters."""

from datetime import datetime

from app.shared.exceptions import DomainValidationError


class PeriodValidationError(DomainValidationError):
    """A year-month filter does not match a route's accepted period rules."""


def validate_expense_period(
    month: str | None, start_month: str | None, end_month: str | None
) -> None:
    if (start_month is None) != (end_month is None):
        raise PeriodValidationError("Informe os meses inicial e final do período.")
    if month is not None and start_month is not None:
        raise PeriodValidationError("Use o filtro de mês ou o intervalo, não os dois.")
    values = [value for value in (month, start_month, end_month) if value is not None]
    try:
        parsed = [datetime.strptime(value, "%Y-%m") for value in values]
    except ValueError as error:
        raise PeriodValidationError("Informe meses válidos no formato AAAA-MM.") from error
    _validate_order_and_length(
        parsed,
        order_message="O mês inicial não pode ser posterior ao mês final.",
        length_message="O período não pode exceder 120 meses.",
    )


def validate_income_period(start_month: str | None, end_month: str | None) -> None:
    if (start_month is None) != (end_month is None):
        raise PeriodValidationError("Informe os meses inicial e final do período.")
    if start_month is None:
        return
    try:
        parsed = [
            datetime.strptime(start_month, "%Y-%m"),
            datetime.strptime(end_month, "%Y-%m"),
        ]
    except ValueError as error:
        raise PeriodValidationError("Informe meses válidos.") from error
    _validate_order_and_length(
        parsed,
        order_message="Informe um período válido de até 120 meses.",
        length_message="Informe um período válido de até 120 meses.",
    )


def _validate_order_and_length(
    parsed: list[datetime], *, order_message: str, length_message: str
) -> None:
    if len(parsed) != 2:
        return
    first, last = parsed
    if first > last:
        raise PeriodValidationError(order_message)
    month_difference = (last.year - first.year) * 12 + last.month - first.month
    if month_difference >= 120:
        raise PeriodValidationError(length_message)
