"""Income and reimbursement use cases, independent of HTTP and SQLAlchemy."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.income_entries.contracts import IncomeEntryCommand
from app.modules.income_entries.repository import (
    IncomeCategoryRepository,
    IncomeEntryRepository,
)
from app.shared.catalog_repository import CatalogRecord
from app.shared.catalog_rules import normalize_catalog_name
from app.shared.exceptions import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.shared.periods import validate_income_period
from app.shared.transactions import UnitOfWork, atomic


class IncomeCategoryService:
    def __init__(
        self,
        repository: IncomeCategoryRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def list(self, user_id: UUID, include_deleted: bool = False) -> list[CatalogRecord]:
        return self._repository.list(user_id, include_deleted)

    def create(self, user_id: UUID, name: str, requires_expense_category: bool) -> CatalogRecord:
        normalized = normalize_catalog_name(name)
        with atomic(self._unit_of_work):
            self._ensure_name_available(user_id, normalized)
            return self._repository.create(
                user_id,
                normalized,
                requires_expense_category=requires_expense_category,
            )

    def update(
        self,
        user_id: UUID,
        category_id: int,
        name: str,
        requires_expense_category: bool | None,
    ) -> CatalogRecord:
        current = self._repository.get(category_id, user_id)
        if current is None:
            raise ResourceNotFoundError("Cadastro não encontrado.")
        if current.deleted_at is not None:
            raise DomainValidationError("Este cadastro foi excluído e não pode ser alterado.")
        normalized = normalize_catalog_name(name)
        attributes: dict[str, bool] = {}
        if requires_expense_category is not None:
            if (
                requires_expense_category != current.requires_expense_category
                and self._repository.rule_is_used(category_id, user_id)
            ):
                raise DomainValidationError(
                    "A regra de reembolso não pode mudar depois do primeiro lançamento."
                )
            attributes["requires_expense_category"] = requires_expense_category
        with atomic(self._unit_of_work):
            self._ensure_name_available(user_id, normalized, exclude_id=category_id)
            updated = self._repository.update(category_id, user_id, normalized, **attributes)
            if updated is None:
                raise ResourceNotFoundError("Cadastro não encontrado.")
            return updated

    def delete(self, user_id: UUID, category_id: int) -> None:
        if self._repository.get(category_id, user_id) is None:
            raise ResourceNotFoundError("Cadastro não encontrado.")
        with atomic(self._unit_of_work):
            if self._repository.soft_delete(category_id, user_id) is None:
                raise ResourceNotFoundError("Cadastro não encontrado.")

    def _ensure_name_available(
        self, user_id: UUID, name: str, *, exclude_id: int | None = None
    ) -> None:
        if self._repository.name_exists(user_id, name, exclude_id=exclude_id):
            raise DuplicateResourceError("Já existe um cadastro ativo com este nome.")


class IncomeEntryService:
    def __init__(
        self,
        repository: IncomeEntryRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def list(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        start_month: str | None = None,
        end_month: str | None = None,
        income_category_id: int | None = None,
        expense_category_id: int | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        validate_income_period(start_month, end_month)
        return self._repository.list(
            user_id,
            page,
            page_size,
            start_month,
            end_month,
            income_category_id,
            expense_category_id,
            search,
        )

    def create(self, user_id: UUID, command: IncomeEntryCommand) -> dict:
        self._validate_references(user_id, command)
        with atomic(self._unit_of_work):
            return self._repository.create(user_id, command)

    def update(self, user_id: UUID, entry_id: int, command: IncomeEntryCommand) -> dict:
        current = self._repository.get_state(user_id, entry_id)
        if current is None:
            raise ResourceNotFoundError("Entrada não encontrada.")
        self._validate_references(
            user_id,
            command,
            previous_income_category_id=current.income_category_id,
            previous_expense_category_id=current.expense_category_id,
        )
        with atomic(self._unit_of_work):
            updated = self._repository.update(user_id, entry_id, command)
            if updated is None:
                raise ResourceNotFoundError("Entrada não encontrada.")
            return updated

    def delete(self, user_id: UUID, entry_id: int) -> None:
        if self._repository.get_state(user_id, entry_id) is None:
            raise ResourceNotFoundError("Entrada não encontrada.")
        with atomic(self._unit_of_work):
            if not self._repository.delete(user_id, entry_id):
                raise ResourceNotFoundError("Entrada não encontrada.")

    def reimbursement_totals(
        self,
        user_id: UUID,
        start_month: str,
        end_month: str,
        category_id: int | None = None,
        search: str | None = None,
    ) -> tuple[dict[str, Decimal], dict[int, Decimal]]:
        rows = self._repository.reimbursement_rows(
            user_id, start_month, end_month, category_id, search
        )
        return aggregate_reimbursement_rows(rows)

    def _validate_references(
        self,
        user_id: UUID,
        command: IncomeEntryCommand,
        *,
        previous_income_category_id: int | None = None,
        previous_expense_category_id: int | None = None,
    ) -> None:
        income_category = self._repository.get_income_category(command.income_category_id, user_id)
        if income_category is None:
            raise ResourceNotFoundError("Categoria de entrada não encontrada.")
        if (
            income_category.deleted_at is not None
            and command.income_category_id != previous_income_category_id
        ):
            raise DomainValidationError("Escolha uma categoria de entrada ativa.")
        if income_category.requires_expense_category and command.expense_category_id is None:
            raise DomainValidationError("Selecione a categoria do gasto reembolsado.")
        if (
            not income_category.requires_expense_category
            and command.expense_category_id is not None
        ):
            raise DomainValidationError(
                "Esta categoria de entrada não aceita categoria de despesa."
            )
        if command.expense_category_id is None:
            return
        expense_category = self._repository.get_expense_category(
            command.expense_category_id, user_id
        )
        if expense_category is None:
            raise ResourceNotFoundError("Categoria de despesa não encontrada.")
        if (
            expense_category.deleted_at is not None
            and command.expense_category_id != previous_expense_category_id
        ):
            raise DomainValidationError("Escolha uma categoria de despesa ativa.")


def aggregate_reimbursement_rows(
    rows: list[tuple[date, int, Decimal]],
) -> tuple[dict[str, Decimal], dict[int, Decimal]]:
    """Group persisted reimbursement facts by received month and expense category."""
    by_month: dict[str, Decimal] = {}
    by_category: dict[int, Decimal] = {}
    for received_date, category_id, amount in rows:
        month = received_date.strftime("%Y-%m")
        by_month[month] = by_month.get(month, Decimal("0.00")) + amount
        by_category[int(category_id)] = by_category.get(int(category_id), Decimal("0.00")) + amount
    return by_month, by_category
