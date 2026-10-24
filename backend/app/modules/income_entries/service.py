from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.income_entries.schema import IncomeEntryCreate
from app.shared.catalog import create_catalog_item, delete_catalog_item, list_catalog, update_catalog_item
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError


def list_income_categories(database: Session, user_id: UUID, include_deleted: bool = False) -> list[IncomeCategory]:
    return list_catalog(database, IncomeCategory, user_id, include_deleted)


def create_income_category(database: Session, user_id: UUID, name: str, requires_expense_category: bool) -> IncomeCategory:
    return create_catalog_item(database, IncomeCategory, user_id, name, requires_expense_category=requires_expense_category)


def update_income_category(database: Session, category_id: int, user_id: UUID, name: str, requires_expense_category: bool | None) -> IncomeCategory:
    attributes = {} if requires_expense_category is None else {"requires_expense_category": requires_expense_category}
    return update_catalog_item(database, IncomeCategory, category_id, user_id, name, **attributes)


def delete_income_category(database: Session, category_id: int, user_id: UUID) -> None:
    delete_catalog_item(database, IncomeCategory, category_id, user_id)


def list_income_entries(
    database: Session,
    user_id: UUID,
    page: int,
    page_size: int,
    start_month: str | None = None,
    end_month: str | None = None,
    income_category_id: int | None = None,
    expense_category_id: int | None = None,
    search: str | None = None,
):
    filters = _entry_filters(user_id, start_month, end_month, income_category_id, expense_category_id, search)
    joins = _income_entry_joins()
    statement = (
        select(IncomeEntry, IncomeCategory.name, IncomeCategory.deleted_at, Category.name, Category.deleted_at)
        .select_from(joins)
        .where(*filters)
        .order_by(IncomeEntry.received_date.desc(), IncomeEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    count = select(func.count(IncomeEntry.id)).select_from(joins).where(*filters)
    items = [_entry_payload(row) for row in database.execute(statement).all()]
    return items, database.scalar(count) or 0


def create_income_entry(database: Session, user_id: UUID, data: IncomeEntryCreate) -> IncomeEntry:
    entry = IncomeEntry(user_id=user_id, **data.model_dump())
    _validate_entry(database, entry, user_id)
    database.add(entry)
    _commit_entry(database)
    database.refresh(entry)
    return entry


def update_income_entry(database: Session, user_id: UUID, entry_id: int, data: IncomeEntryCreate) -> IncomeEntry:
    entry = database.scalar(select(IncomeEntry).where(IncomeEntry.id == entry_id, IncomeEntry.user_id == user_id))
    if entry is None:
        raise ResourceNotFoundError("Entrada não encontrada.")
    previous_income_category_id = entry.income_category_id
    previous_expense_category_id = entry.expense_category_id
    for key, value in data.model_dump().items():
        setattr(entry, key, value)
    _validate_entry(
        database, entry, user_id,
        previous_income_category_id=previous_income_category_id,
        previous_expense_category_id=previous_expense_category_id,
    )
    _commit_entry(database)
    database.refresh(entry)
    return entry


def delete_income_entry(database: Session, user_id: UUID, entry_id: int) -> None:
    entry = database.scalar(select(IncomeEntry).where(IncomeEntry.id == entry_id, IncomeEntry.user_id == user_id))
    if entry is None:
        raise ResourceNotFoundError("Entrada não encontrada.")
    database.delete(entry)
    _commit_entry(database)


def income_entry_payload(database: Session, entry: IncomeEntry) -> dict:
    row = database.execute(
        select(IncomeCategory.name, IncomeCategory.deleted_at, Category.name, Category.deleted_at)
        .select_from(_income_entry_joins())
        .where(IncomeEntry.id == entry.id, IncomeEntry.user_id == entry.user_id)
    ).one()
    return _entry_payload((entry, *row))


def reimbursement_totals(
    database: Session,
    user_id: UUID,
    start_month: str,
    end_month: str,
    category_id: int | None = None,
    search: str | None = None,
    include: bool = True,
):
    if not include:
        return {}, {}
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
        filters.append(or_(IncomeEntry.description.ilike(pattern), IncomeCategory.name.ilike(pattern), Category.name.ilike(pattern)))
    query = (
        select(IncomeEntry.received_date, IncomeEntry.expense_category_id, func.sum(IncomeEntry.amount))
        .select_from(_income_entry_joins())
        .where(*filters)
        .group_by(IncomeEntry.received_date, IncomeEntry.expense_category_id)
    )
    by_month: dict[str, Decimal] = {}
    by_category: dict[int, Decimal] = {}
    for received_date, expense_category_id, amount in database.execute(query):
        key = received_date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, Decimal("0.00")) + amount
        by_category[int(expense_category_id)] = by_category.get(int(expense_category_id), Decimal("0.00")) + amount
    return by_month, by_category


def _validate_entry(
    database: Session,
    entry: IncomeEntry,
    user_id: UUID,
    *,
    previous_income_category_id: int | None = None,
    previous_expense_category_id: int | None = None,
) -> None:
    category = database.scalar(select(IncomeCategory).where(IncomeCategory.id == entry.income_category_id, IncomeCategory.user_id == user_id))
    if category is None:
        raise ResourceNotFoundError("Categoria de entrada não encontrada.")
    if category.deleted_at is not None and category.id != previous_income_category_id:
        raise ValueError("Escolha uma categoria de entrada ativa.")
    if category.requires_expense_category and entry.expense_category_id is None:
        raise ValueError("Selecione a categoria do gasto reembolsado.")
    if not category.requires_expense_category and entry.expense_category_id is not None:
        raise ValueError("Esta categoria de entrada não aceita categoria de despesa.")
    if entry.expense_category_id is not None:
        expense_category = database.scalar(select(Category).where(Category.id == entry.expense_category_id, Category.user_id == user_id))
        if expense_category is None:
            raise ResourceNotFoundError("Categoria de despesa não encontrada.")
        if expense_category.deleted_at is not None and expense_category.id != previous_expense_category_id:
            raise ValueError("Escolha uma categoria de despesa ativa.")


def _entry_filters(user_id, start_month, end_month, income_category_id, expense_category_id, search):
    filters = [IncomeEntry.user_id == user_id]
    if start_month and end_month:
        start = date.fromisoformat(f"{start_month}-01")
        year, month = map(int, end_month.split("-"))
        filters.append(IncomeEntry.received_date.between(start, date(year, month, monthrange(year, month)[1])))
    if income_category_id is not None:
        filters.append(IncomeEntry.income_category_id == income_category_id)
    if expense_category_id is not None:
        filters.append(IncomeEntry.expense_category_id == expense_category_id)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(or_(IncomeEntry.description.ilike(pattern), IncomeCategory.name.ilike(pattern), Category.name.ilike(pattern)))
    return filters


def _income_entry_joins():
    return (
        IncomeEntry.__table__
        .join(IncomeCategory.__table__, (IncomeEntry.income_category_id == IncomeCategory.id) & (IncomeEntry.user_id == IncomeCategory.user_id))
        .outerjoin(Category.__table__, (IncomeEntry.expense_category_id == Category.id) & (IncomeEntry.user_id == Category.user_id))
    )


def _entry_payload(row):
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
        "expense_category_deleted": expense_deleted_at is not None if expense_name is not None else None,
    }


def _commit_entry(database: Session) -> None:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        if "unique" in str(error).lower() or "duplicate key" in str(error).lower():
            raise DuplicateResourceError("Já existe um registro com estes dados.") from error
        raise
