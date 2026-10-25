"""Expense use cases and financial rules, independent of HTTP and SQLAlchemy."""

from decimal import Decimal
from uuid import UUID

from app.modules.expenses.contracts import ExpenseCommand
from app.modules.expenses.repository import ExpenseRepository
from app.modules.expenses.rules import build_installments, total_amount, validate_payment_schedule
from app.modules.income_entries.service import IncomeEntryService
from app.shared.catalog_repository import CatalogRepository
from app.shared.exceptions import DomainValidationError, ResourceNotFoundError
from app.shared.periods import validate_expense_period
from app.shared.transactions import UnitOfWork, atomic


class ExpenseService:
    def __init__(
        self,
        repository: ExpenseRepository,
        categories: CatalogRepository,
        payment_methods: CatalogRepository,
        income_entries: IncomeEntryService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._categories = categories
        self._payment_methods = payment_methods
        self._income_entries = income_entries
        self._unit_of_work = unit_of_work

    def list(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        month: str | None = None,
        search: str | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
        category_id: int | None = None,
        payment_method_id: int | None = None,
    ):
        validate_expense_period(month, start_month, end_month)
        return self._repository.list(
            user_id,
            page,
            page_size,
            month,
            search,
            start_month,
            end_month,
            category_id,
            payment_method_id,
        )

    def history(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        month: str,
        search: str | None = None,
        category_id: int | None = None,
        payment_method_id: int | None = None,
    ):
        validate_expense_period(month, None, None)
        return self._repository.history(
            user_id, page, page_size, month, search, category_id, payment_method_id
        )

    def recent(self, user_id: UUID, limit: int):
        return self._repository.recent(user_id, limit)

    def in_month(self, user_id: UUID, month: str):
        validate_expense_period(month, None, None)
        return self._repository.in_month(user_id, month)

    def summary(
        self,
        user_id: UUID,
        start_month: str,
        end_month: str,
        search: str | None = None,
        category_id: int | None = None,
        payment_method_id: int | None = None,
    ):
        validate_expense_period(None, start_month, end_month)
        rows = self._repository.summary(
            user_id, start_month, end_month, search, category_id, payment_method_id
        )
        month_amounts: dict[str, Decimal] = {}
        category_amounts: dict[int, Decimal] = {}
        for month, expense_category_id, amount in rows:
            month_amounts[month] = month_amounts.get(month, Decimal("0.00")) + amount
            category = int(expense_category_id)
            category_amounts[category] = category_amounts.get(category, Decimal("0.00")) + amount

        if payment_method_id is None:
            reimbursement_months, reimbursement_categories = (
                self._income_entries.reimbursement_totals(
                    user_id, start_month, end_month, category_id, search
                )
            )
        else:
            reimbursement_months, reimbursement_categories = {}, {}

        monthly_totals = []
        for month in _months_between(start_month, end_month):
            gross = month_amounts.get(month, Decimal("0.00"))
            reimbursement = reimbursement_months.get(month, Decimal("0.00"))
            monthly_totals.append(
                {
                    "month": month,
                    "amount_due": gross - reimbursement,
                    "gross_expense_amount": gross,
                    "reimbursement_amount": reimbursement,
                    "net_expense_amount": gross - reimbursement,
                }
            )

        category_totals = []
        for category in set(category_amounts) | set(reimbursement_categories):
            gross = category_amounts.get(category, Decimal("0.00"))
            reimbursement = reimbursement_categories.get(category, Decimal("0.00"))
            category_totals.append(
                {
                    "category_id": category,
                    "amount_due": gross - reimbursement,
                    "gross_expense_amount": gross,
                    "reimbursement_amount": reimbursement,
                    "net_expense_amount": gross - reimbursement,
                }
            )
        category_totals.sort(key=lambda row: (-row["net_expense_amount"], row["category_id"]))
        gross_total = sum(month_amounts.values(), Decimal("0.00"))
        reimbursement_total = sum(reimbursement_months.values(), Decimal("0.00"))
        net_total = gross_total - reimbursement_total
        return {
            "total_amount_due": net_total,
            "gross_expense_amount": gross_total,
            "reimbursement_amount": reimbursement_total,
            "net_expense_amount": net_total,
            "monthly_totals": monthly_totals,
            "category_totals": category_totals,
        }

    def create(self, user_id: UUID, command: ExpenseCommand) -> dict:
        self._validate_schedule(command)
        self._validate_references(user_id, command)
        amount = total_amount(
            command.amount,
            command.amount_type,
            command.payment_type,
            command.installment_count,
        )
        first_date = command.first_installment_date or command.expense_date
        installments = build_installments(
            total=amount,
            count=command.installment_count,
            first_date=first_date,
        )
        with atomic(self._unit_of_work):
            return self._repository.create(user_id, command, amount, installments)

    def update(self, user_id: UUID, expense_id: int, command: ExpenseCommand) -> dict:
        self._validate_schedule(command)
        current = self._repository.get_state(user_id, expense_id)
        if current is None:
            raise ResourceNotFoundError("Despesa não encontrada.")
        self._validate_references(
            user_id,
            command,
            previous_category_id=current.category_id,
            previous_payment_method_id=current.payment_method_id,
        )
        amount = total_amount(
            command.amount,
            command.amount_type,
            command.payment_type,
            command.installment_count,
        )
        first_date = command.first_installment_date or command.expense_date
        schedule_changed = (
            current.amount != amount
            or current.expense_date != command.expense_date
            or current.installment_count != command.installment_count
            or current.first_installment_date != first_date
        )
        installments = (
            build_installments(
                total=amount,
                count=command.installment_count,
                first_date=first_date,
            )
            if schedule_changed
            else []
        )
        with atomic(self._unit_of_work):
            return self._repository.update(
                user_id,
                expense_id,
                command,
                amount,
                installments,
                schedule_changed,
            )

    def delete(self, user_id: UUID, expense_id: int) -> None:
        if self._repository.get_state(user_id, expense_id) is None:
            raise ResourceNotFoundError("Despesa não encontrada.")
        with atomic(self._unit_of_work):
            self._repository.delete(user_id, expense_id)

    @staticmethod
    def _validate_schedule(command: ExpenseCommand) -> None:
        validate_payment_schedule(
            payment_type=command.payment_type,
            amount_type=command.amount_type,
            amount=command.amount,
            installment_count=command.installment_count,
            expense_date=command.expense_date,
            first_installment_date=command.first_installment_date,
        )

    def _validate_references(
        self,
        user_id: UUID,
        command: ExpenseCommand,
        *,
        previous_category_id: int | None = None,
        previous_payment_method_id: int | None = None,
    ) -> None:
        category = self._categories.get(command.category_id, user_id)
        if category is None:
            raise ResourceNotFoundError("Categoria não encontrada.")
        if category.deleted_at is not None and command.category_id != previous_category_id:
            raise DomainValidationError("Escolha uma categoria ativa.")
        payment_method = self._payment_methods.get(command.payment_method_id, user_id)
        if payment_method is None:
            raise ResourceNotFoundError("Meio de pagamento não encontrado.")
        if (
            payment_method.deleted_at is not None
            and command.payment_method_id != previous_payment_method_id
        ):
            raise DomainValidationError("Escolha um meio de pagamento ativo.")


def _months_between(start_month: str, end_month: str) -> list[str]:
    start_year, start_number = map(int, start_month.split("-"))
    end_year, end_number = map(int, end_month.split("-"))
    start_index = start_year * 12 + start_number - 1
    end_index = end_year * 12 + end_number - 1
    months = []
    for index in range(start_index, end_index + 1):
        year, zero_based_month = divmod(index, 12)
        months.append(f"{year:04d}-{zero_based_month + 1:02d}")
    return months
