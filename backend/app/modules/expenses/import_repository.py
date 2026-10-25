"""Persistence adapter for reviewed expense imports."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.categories.model import Category
from app.modules.expenses.import_contracts import ImportedInstallment, ImportExpenseCommand
from app.modules.expenses.model import Expense, ExpenseImportSource, ExpenseInstallment
from app.modules.payment_methods.model import PaymentMethod


class ExpenseImportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def user_exists(self, user_id: UUID) -> bool:
        return self._session.scalar(select(User.id).where(User.id == user_id)) is not None

    def active_category_names(self, user_id: UUID) -> list[str]:
        return list(
            self._session.scalars(
                select(Category.name).where(
                    Category.user_id == user_id,
                    Category.deleted_at.is_(None),
                )
            )
        )

    def existing_source_keys(self, user_id: UUID, source_keys: list[str]) -> set[str]:
        if not source_keys:
            return set()
        return set(
            self._session.scalars(
                select(ExpenseImportSource.source_key).where(
                    ExpenseImportSource.user_id == user_id,
                    ExpenseImportSource.source_key.in_(source_keys),
                )
            )
        )

    def active_catalog_ids(self, user_id: UUID) -> tuple[dict[str, int], dict[str, int]]:
        categories = {
            item.name: item.id
            for item in self._session.scalars(
                select(Category).where(
                    Category.user_id == user_id,
                    Category.deleted_at.is_(None),
                )
            )
        }
        methods = {
            item.name: item.id
            for item in self._session.scalars(
                select(PaymentMethod).where(
                    PaymentMethod.user_id == user_id,
                    PaymentMethod.deleted_at.is_(None),
                )
            )
        }
        return categories, methods

    def save_all(
        self,
        user_id: UUID,
        items: list[ImportExpenseCommand],
        installments_by_item: list[list[ImportedInstallment]],
        categories: dict[str, int],
        payment_methods: dict[str, int],
    ) -> None:
        for item, installments in zip(items, installments_by_item, strict=True):
            expense = Expense(
                description=item.description,
                amount=sum(item.amounts, start=Decimal("0.00")),
                expense_date=item.expense_date,
                installment_count=len(installments),
                first_installment_date=item.expense_date,
                category_id=categories[item.category_name],
                payment_method_id=payment_methods[item.payment_method_name],
                user_id=user_id,
            )
            self._session.add(expense)
            self._session.flush()
            self._session.add_all(
                ExpenseInstallment(
                    expense_id=expense.id,
                    installment_number=installment.number,
                    amount=installment.amount,
                    due_date=installment.due_date,
                )
                for installment in installments
            )
            self._session.add_all(
                ExpenseImportSource(
                    source_key=source_key,
                    expense_id=expense.id,
                    user_id=user_id,
                )
                for source_key in item.source_keys
            )
        self._session.flush()
