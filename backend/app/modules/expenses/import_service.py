"""Application rules for applying explicitly reviewed spreadsheet imports."""

from calendar import monthrange
from datetime import date
from uuid import UUID

from app.modules.expenses.import_contracts import ImportedInstallment, ImportExpenseCommand
from app.shared.exceptions import DomainValidationError
from app.shared.transactions import UnitOfWork, atomic


class ExpenseImportService:
    def __init__(self, repository, unit_of_work: UnitOfWork) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def user_categories(self, user_id: UUID) -> list[str]:
        if not self._repository.user_exists(user_id):
            raise DomainValidationError(f"Usuário não encontrado: {user_id}")
        return self._repository.active_category_names(user_id)

    def apply(self, user_id: UUID, items: list[ImportExpenseCommand]) -> int:
        source_keys = [key for item in items for key in item.source_keys]
        existing = self._repository.existing_source_keys(user_id, source_keys)
        if existing:
            if existing == set(source_keys):
                return 0
            raise DomainValidationError(
                "Importação parcial detectada; gravação cancelada para evitar duplicatas."
            )

        categories, payment_methods = self._repository.active_catalog_ids(user_id)
        installments_by_item: list[list[ImportedInstallment]] = []
        for item in items:
            if item.category_name not in categories:
                raise DomainValidationError(f"Categoria ausente no banco: {item.category_name}")
            if item.payment_method_name not in payment_methods:
                raise DomainValidationError(
                    f"Meio de pagamento ausente no banco: {item.payment_method_name}"
                )
            installments_by_item.append(
                [
                    ImportedInstallment(
                        number=index + 1,
                        amount=amount,
                        due_date=_month_offset(item.expense_date, index),
                    )
                    for index, amount in enumerate(item.amounts)
                ]
            )

        with atomic(self._unit_of_work):
            self._repository.save_all(
                user_id,
                items,
                installments_by_item,
                categories,
                payment_methods,
            )
        return len(items)


def _month_offset(day: date, offset: int) -> date:
    month_index = (day.year - 1) * 12 + day.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year + 1, month, min(day.day, monthrange(year + 1, month)[1]))
