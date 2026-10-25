"""SQLAlchemy persistence for income categories, entries and reimbursements."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.income_entries.contracts import IncomeEntryCommand, IncomeEntryState
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.shared.catalog_repository import CatalogRepository


class IncomeCategoryRepository(CatalogRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, IncomeCategory)
        self._session = session

    def rule_is_used(self, category_id: int, user_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(IncomeEntry.id)
                .where(
                    IncomeEntry.income_category_id == category_id,
                    IncomeEntry.user_id == user_id,
                )
                .limit(1)
            )
            is not None
        )


@dataclass(frozen=True)
class ReferenceState:
    id: int
    deleted_at: Any
    requires_expense_category: bool | None = None


class IncomeEntryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._income_categories = IncomeCategoryRepository(session)
        self._expense_categories = CatalogRepository(session, Category)

    def get_income_category(self, category_id: int, user_id: UUID) -> ReferenceState | None:
        record = self._income_categories.get(category_id, user_id)
        if record is None:
            return None
        return ReferenceState(
            id=record.id,
            deleted_at=record.deleted_at,
            requires_expense_category=record.requires_expense_category,
        )

    def get_expense_category(self, category_id: int, user_id: UUID) -> ReferenceState | None:
        record = self._expense_categories.get(category_id, user_id)
        if record is None:
            return None
        return ReferenceState(id=record.id, deleted_at=record.deleted_at)

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
        filters = self._entry_filters(
            user_id,
            start_month,
            end_month,
            income_category_id,
            expense_category_id,
            search,
        )
        joins = self._income_entry_joins()
        statement = (
            select(
                IncomeEntry,
                IncomeCategory.name,
                IncomeCategory.deleted_at,
                Category.name,
                Category.deleted_at,
            )
            .select_from(joins)
            .where(*filters)
            .order_by(IncomeEntry.received_date.desc(), IncomeEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_statement = select(func.count(IncomeEntry.id)).select_from(joins).where(*filters)
        items = [self._entry_payload(row) for row in self._session.execute(statement).all()]
        return items, self._session.scalar(count_statement) or 0

    def get_state(self, user_id: UUID, entry_id: int) -> IncomeEntryState | None:
        entry = self._session.scalar(
            select(IncomeEntry).where(
                IncomeEntry.id == entry_id,
                IncomeEntry.user_id == user_id,
            )
        )
        if entry is None:
            return None
        return IncomeEntryState(
            id=entry.id,
            income_category_id=entry.income_category_id,
            expense_category_id=entry.expense_category_id,
        )

    def create(self, user_id: UUID, command: IncomeEntryCommand) -> dict:
        entry = IncomeEntry(user_id=user_id, **command.__dict__)
        self._session.add(entry)
        self._session.flush()
        return self._get_payload(entry)

    def update(self, user_id: UUID, entry_id: int, command: IncomeEntryCommand) -> dict | None:
        entry = self._session.scalar(
            select(IncomeEntry).where(
                IncomeEntry.id == entry_id,
                IncomeEntry.user_id == user_id,
            )
        )
        if entry is None:
            return None
        for key, value in command.__dict__.items():
            setattr(entry, key, value)
        self._session.flush()
        return self._get_payload(entry)

    def delete(self, user_id: UUID, entry_id: int) -> bool:
        entry = self._session.scalar(
            select(IncomeEntry).where(
                IncomeEntry.id == entry_id,
                IncomeEntry.user_id == user_id,
            )
        )
        if entry is None:
            return False
        self._session.delete(entry)
        self._session.flush()
        return True

    def reimbursement_rows(
        self,
        user_id: UUID,
        start_month: str,
        end_month: str,
        category_id: int | None = None,
        search: str | None = None,
    ) -> list[tuple[date, int, Decimal]]:
        start = date.fromisoformat(f"{start_month}-01")
        year, month = map(int, end_month.split("-"))
        end = date(year, month, monthrange(year, month)[1])
        filters = [
            IncomeEntry.user_id == user_id,
            IncomeEntry.received_date.between(start, end),
            IncomeCategory.user_id == user_id,
            IncomeCategory.requires_expense_category.is_(True),
        ]
        if category_id is not None:
            filters.append(IncomeEntry.expense_category_id == category_id)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    IncomeEntry.description.ilike(pattern),
                    IncomeCategory.name.ilike(pattern),
                    Category.name.ilike(pattern),
                )
            )
        query = (
            select(
                IncomeEntry.received_date,
                IncomeEntry.expense_category_id,
                func.sum(IncomeEntry.amount),
            )
            .select_from(self._income_entry_joins())
            .where(*filters)
            .group_by(IncomeEntry.received_date, IncomeEntry.expense_category_id)
        )
        return list(self._session.execute(query))

    def _get_payload(self, entry: IncomeEntry) -> dict:
        row = self._session.execute(
            select(
                IncomeCategory.name,
                IncomeCategory.deleted_at,
                Category.name,
                Category.deleted_at,
            )
            .select_from(self._income_entry_joins())
            .where(IncomeEntry.id == entry.id, IncomeEntry.user_id == entry.user_id)
        ).one()
        return self._entry_payload((entry, *row))

    @staticmethod
    def _entry_payload(row) -> dict:
        entry, income_name, income_deleted_at, expense_name, expense_deleted_at = row
        return {
            "id": entry.id,
            "description": entry.description,
            "amount": entry.amount,
            "received_date": entry.received_date,
            "income_category_id": entry.income_category_id,
            "expense_category_id": entry.expense_category_id,
            "created_at": entry.created_at,
            "income_category_name": income_name,
            "income_category_deleted": income_deleted_at is not None,
            "expense_category_name": expense_name,
            "expense_category_deleted": (
                expense_deleted_at is not None if expense_name is not None else None
            ),
        }

    @staticmethod
    def _income_entry_joins():
        return IncomeEntry.__table__.join(
            IncomeCategory.__table__,
            (IncomeEntry.income_category_id == IncomeCategory.id)
            & (IncomeEntry.user_id == IncomeCategory.user_id),
        ).outerjoin(
            Category.__table__,
            (IncomeEntry.expense_category_id == Category.id)
            & (IncomeEntry.user_id == Category.user_id),
        )

    def _entry_filters(
        self,
        user_id,
        start_month,
        end_month,
        income_category_id,
        expense_category_id,
        search,
    ):
        filters = [IncomeEntry.user_id == user_id]
        if start_month and end_month:
            start = date.fromisoformat(f"{start_month}-01")
            year, month = map(int, end_month.split("-"))
            filters.append(
                IncomeEntry.received_date.between(
                    start, date(year, month, monthrange(year, month)[1])
                )
            )
        if income_category_id is not None:
            filters.append(IncomeEntry.income_category_id == income_category_id)
        if expense_category_id is not None:
            filters.append(IncomeEntry.expense_category_id == expense_category_id)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    IncomeEntry.description.ilike(pattern),
                    IncomeCategory.name.ilike(pattern),
                    Category.name.ilike(pattern),
                )
            )
        return filters
