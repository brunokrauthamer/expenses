from calendar import monthrange
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.income_entries.schema import IncomeEntryCreate
from app.shared.exceptions import ResourceNotFoundError


def list_income_categories(database: Session) -> list[IncomeCategory]:
    return list(database.scalars(select(IncomeCategory).order_by(IncomeCategory.id)))


def list_income_entries(database: Session, page: int, page_size: int, start_month: str | None = None, end_month: str | None = None, income_category_id: int | None = None, expense_category_id: int | None = None, search: str | None = None):
    filters = _entry_filters(start_month, end_month, income_category_id, expense_category_id, search)
    statement = select(IncomeEntry).outerjoin(IncomeCategory).outerjoin(Category, IncomeEntry.expense_category_id == Category.id).where(*filters).order_by(IncomeEntry.received_date.desc(), IncomeEntry.id.desc()).offset((page - 1) * page_size).limit(page_size)
    total = database.scalar(select(func.count(IncomeEntry.id)).select_from(IncomeEntry).outerjoin(IncomeCategory).outerjoin(Category, IncomeEntry.expense_category_id == Category.id).where(*filters)) or 0
    return list(database.scalars(statement)), total


def create_income_entry(database: Session, data: IncomeEntryCreate) -> IncomeEntry:
    entry = IncomeEntry(**data.model_dump())
    _validate_entry(database, entry)
    database.add(entry)
    try:
        database.commit()
        database.refresh(entry)
    except Exception:
        database.rollback()
        raise
    return entry


def update_income_entry(database: Session, entry_id: int, data: IncomeEntryCreate) -> IncomeEntry:
    entry = database.get(IncomeEntry, entry_id)
    if entry is None:
        raise ResourceNotFoundError("Entrada não encontrada.")
    for key, value in data.model_dump().items():
        setattr(entry, key, value)
    _validate_entry(database, entry)
    try:
        database.commit()
        database.refresh(entry)
    except Exception:
        database.rollback()
        raise
    return entry


def delete_income_entry(database: Session, entry_id: int) -> None:
    entry = database.get(IncomeEntry, entry_id)
    if entry is None:
        raise ResourceNotFoundError("Entrada não encontrada.")
    database.delete(entry)
    try:
        database.commit()
    except Exception:
        database.rollback()
        raise


def reimbursement_totals(database: Session, start_month: str, end_month: str, category_id: int | None = None, search: str | None = None, include: bool = True):
    if not include:
        return {}, {}
    start = date.fromisoformat(f"{start_month}-01")
    year, month = map(int, end_month.split("-"))
    end = date(year, month, monthrange(year, month)[1])
    filters = [IncomeEntry.received_date.between(start, end), IncomeCategory.requires_expense_category.is_(True)]
    if category_id is not None:
        filters.append(IncomeEntry.expense_category_id == category_id)
    normalized = search.strip() if search else ""
    if normalized:
        pattern = f"%{normalized}%"
        filters.append(or_(IncomeEntry.description.ilike(pattern), IncomeCategory.name.ilike(pattern), Category.name.ilike(pattern)))
    query = select(IncomeEntry.received_date, IncomeEntry.expense_category_id, func.sum(IncomeEntry.amount)).join(IncomeCategory).join(Category, IncomeEntry.expense_category_id == Category.id).where(*filters).group_by(IncomeEntry.received_date, IncomeEntry.expense_category_id)
    by_month: dict[str, object] = {}
    by_category: dict[int, object] = {}
    for received_date, expense_category_id, amount in database.execute(query):
        key = received_date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0) + amount
        by_category[int(expense_category_id)] = by_category.get(int(expense_category_id), 0) + amount
    return by_month, by_category


def _validate_entry(database: Session, entry: IncomeEntry) -> None:
    category = database.get(IncomeCategory, entry.income_category_id)
    if category is None:
        raise ResourceNotFoundError("Categoria de entrada não encontrada.")
    if category.requires_expense_category and entry.expense_category_id is None:
        raise ValueError("Selecione a categoria do gasto reembolsado.")
    if not category.requires_expense_category and entry.expense_category_id is not None:
        raise ValueError("Esta categoria de entrada não aceita categoria de despesa.")
    if entry.expense_category_id is not None and database.get(Category, entry.expense_category_id) is None:
        raise ResourceNotFoundError("Categoria de despesa não encontrada.")


def _entry_filters(start_month, end_month, income_category_id, expense_category_id, search):
    filters = []
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
