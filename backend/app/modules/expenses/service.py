from calendar import monthrange
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense
from app.modules.expenses.schema import ExpenseCreate, ExpenseUpdate
from app.modules.payment_methods.model import PaymentMethod
from app.shared.exceptions import ResourceNotFoundError


def list_expenses(
    database: Session,
    page: int,
    page_size: int,
    month: str | None = None,
    search: str | None = None,
) -> tuple[list[Expense], int]:
    """Retorna despesas paginadas, com filtros opcionais por mês e texto."""
    filters = []
    if month:
        year, month_number = map(int, month.split("-"))
        first_day = date(year, month_number, 1)
        last_day = date(year, month_number, monthrange(year, month_number)[1])
        filters.append(Expense.expense_date.between(first_day, last_day))

    normalized_search = search.strip() if search else ""
    if normalized_search:
        search_pattern = f"%{normalized_search}%"
        filters.append(
            or_(
                Expense.description.ilike(search_pattern),
                Category.name.ilike(search_pattern),
                PaymentMethod.name.ilike(search_pattern),
            )
        )

    statement = (
        select(Expense)
        .options(selectinload(Expense.category))
        .join(Expense.category)
        .join(Expense.payment_method)
        .where(*filters)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    count_statement = (
        select(func.count())
        .select_from(Expense)
        .join(Expense.category)
        .join(Expense.payment_method)
        .where(*filters)
    )
    return list(database.scalars(statement)), database.scalar(count_statement) or 0


def create_expense(database: Session, data: ExpenseCreate) -> Expense:
    """Valida as referências e persiste uma nova despesa."""
    _validate_references(database, data.category_id, data.payment_method_id)
    expense = Expense(**data.model_dump())
    database.add(expense)
    database.commit()
    database.refresh(expense)
    return expense


def update_expense(database: Session, expense_id: int, data: ExpenseUpdate) -> Expense:
    """Atualiza uma despesa existente após validar suas referências."""
    expense = _get_expense(database, expense_id)
    _validate_references(database, data.category_id, data.payment_method_id)

    for field, value in data.model_dump().items():
        setattr(expense, field, value)

    database.commit()
    database.refresh(expense)
    return expense


def delete_expense(database: Session, expense_id: int) -> None:
    """Remove uma despesa existente."""
    expense = _get_expense(database, expense_id)
    database.delete(expense)
    database.commit()


def _get_expense(database: Session, expense_id: int) -> Expense:
    expense = database.get(Expense, expense_id)
    if expense is None:
        raise ResourceNotFoundError("Despesa não encontrada.")
    return expense


def _validate_references(database: Session, category_id: int, payment_method_id: int) -> None:
    if database.get(Category, category_id) is None:
        raise ResourceNotFoundError("Categoria não encontrada.")
    if database.get(PaymentMethod, payment_method_id) is None:
        raise ResourceNotFoundError("Meio de pagamento não encontrado.")
