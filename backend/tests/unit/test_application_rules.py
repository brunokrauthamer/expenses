from datetime import date
from decimal import Decimal

import pytest
from app.modules.expenses.rules import build_installments, validate_payment_schedule
from app.modules.income_entries.service import aggregate_reimbursement_rows
from app.shared.catalog_rules import normalize_catalog_name
from app.shared.exceptions import DomainValidationError
from app.shared.periods import validate_expense_period, validate_income_period
from app.shared.transactions import atomic

pytestmark = pytest.mark.unit


def test_installment_schedule_assigns_remainder_to_first_and_keeps_month_end():
    installments = build_installments(
        total=Decimal("100.01"),
        count=3,
        first_date=date(2024, 1, 31),
    )

    assert [(item.amount, item.due_date) for item in installments] == [
        (Decimal("33.35"), date(2024, 1, 31)),
        (Decimal("33.33"), date(2024, 2, 29)),
        (Decimal("33.33"), date(2024, 3, 31)),
    ]


def test_payment_schedule_rejects_one_time_expense_with_multiple_installments():
    with pytest.raises(DomainValidationError, match="Um gasto à vista deve ter uma parcela"):
        validate_payment_schedule(
            payment_type="one_time",
            amount_type="total",
            amount=Decimal("50.00"),
            installment_count=2,
            expense_date=date(2026, 1, 1),
            first_installment_date=None,
        )


@pytest.mark.parametrize(
    ("validator", "start", "end", "message"),
    [
        (
            validate_expense_period,
            "2020-01",
            "2029-12",
            None,
        ),
        (
            validate_expense_period,
            "2020-01",
            "2030-01",
            "O período não pode exceder 120 meses",
        ),
        (
            validate_income_period,
            "2020-01",
            "2030-01",
            "período válido de até 120 meses",
        ),
    ],
)
def test_period_limit_is_120_inclusive_months(validator, start, end, message):
    if message is None:
        validator(None, start, end)
        return
    with pytest.raises(DomainValidationError, match=message):
        validator(None, start, end) if validator is validate_expense_period else validator(
            start, end
        )


def test_period_validation_preserves_distinct_income_and_expense_messages():
    with pytest.raises(DomainValidationError, match="Informe meses válidos no formato AAAA-MM"):
        validate_expense_period("2026-13", None, None)
    with pytest.raises(DomainValidationError, match="Informe meses válidos"):
        validate_income_period("2026-13", "2026-10")


def test_catalog_name_is_trimmed_and_rejects_blank_and_long_values():
    assert normalize_catalog_name("  Casa  ") == "Casa"
    with pytest.raises(DomainValidationError, match="não pode ficar vazio"):
        normalize_catalog_name("   ")
    with pytest.raises(DomainValidationError, match="no máximo 50"):
        normalize_catalog_name("x" * 51)


def test_reimbursements_are_grouped_by_received_month_and_expense_category():
    monthly, categories = aggregate_reimbursement_rows(
        [
            (date(2026, 1, 5), 2, Decimal("10.00")),
            (date(2026, 1, 20), 2, Decimal("5.00")),
            (date(2026, 2, 1), 3, Decimal("7.25")),
        ]
    )

    assert monthly == {"2026-01": Decimal("15.00"), "2026-02": Decimal("7.25")}
    assert categories == {2: Decimal("15.00"), 3: Decimal("7.25")}


def test_atomic_commits_once_or_rolls_back_after_failure():
    class FakeUnitOfWork:
        commits = 0
        rollbacks = 0
        fail_commit = False

        def commit(self):
            self.commits += 1
            if self.fail_commit:
                raise RuntimeError("commit failed")

        def rollback(self):
            self.rollbacks += 1

    unit_of_work = FakeUnitOfWork()
    with atomic(unit_of_work):
        pass
    assert (unit_of_work.commits, unit_of_work.rollbacks) == (1, 0)

    unit_of_work.fail_commit = True
    with pytest.raises(RuntimeError, match="commit failed"):
        with atomic(unit_of_work):
            pass
    assert (unit_of_work.commits, unit_of_work.rollbacks) == (2, 1)
