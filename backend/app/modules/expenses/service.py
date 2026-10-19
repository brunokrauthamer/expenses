from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.expenses.schema import ExpenseCreate, ExpenseUpdate
from app.modules.payment_methods.model import PaymentMethod
from app.shared.exceptions import ResourceNotFoundError


def list_expenses(
    database: Session,
    page: int,
    page_size: int,
    month: str | None = None,
    search: str | None = None,
) -> tuple[list[ExpenseInstallment], int]:
    """Retorna cobranças paginadas, com filtros opcionais por mês e texto."""
    filters = []
    if month:
        year, month_number = map(int, month.split("-"))
        first_day = date(year, month_number, 1)
        last_day = date(year, month_number, monthrange(year, month_number)[1])
        filters.append(ExpenseInstallment.due_date.between(first_day, last_day))

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

    from_expense = (
        ExpenseInstallment.__table__
        .join(Expense.__table__, ExpenseInstallment.expense_id == Expense.id)
        .join(Category.__table__, Expense.category_id == Category.id)
        .join(PaymentMethod.__table__, Expense.payment_method_id == PaymentMethod.id)
    )
    statement = (
        select(ExpenseInstallment)
        .select_from(from_expense)
        .options(selectinload(ExpenseInstallment.expense))
        .where(*filters)
        .order_by(
            ExpenseInstallment.due_date.desc(),
            Expense.id.desc(),
            ExpenseInstallment.installment_number.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    count_statement = (
        select(func.count())
        .select_from(from_expense)
        .where(*filters)
    )
    return list(database.scalars(statement)), database.scalar(count_statement) or 0


def create_expense(database: Session, data: ExpenseCreate) -> Expense:
    """Valida referências e persiste a compra com todas as suas cobranças."""
    _validate_references(database, data.category_id, data.payment_method_id)
    expense = Expense(
        description=data.description,
        amount=_total_amount(data),
        expense_date=data.expense_date,
        installment_count=data.installment_count,
        first_installment_date=data.first_installment_date or data.expense_date,
        category_id=data.category_id,
        payment_method_id=data.payment_method_id,
    )
    database.add(expense)
    try:
        database.flush()
        database.add_all(_build_installments(expense, data))
        database.commit()
        database.refresh(expense)
    except Exception:
        database.rollback()
        raise
    return expense


def update_expense(database: Session, expense_id: int, data: ExpenseUpdate) -> Expense:
    """Atualiza a compra e recalcula as cobranças quando seu cronograma muda."""
    expense = _get_expense(database, expense_id)
    _validate_references(database, data.category_id, data.payment_method_id)

    new_amount = _total_amount(data)
    new_first_date = data.first_installment_date or data.expense_date
    schedule_changed = (
        expense.amount != new_amount
        or expense.expense_date != data.expense_date
        or expense.installment_count != data.installment_count
        or expense.first_installment_date != new_first_date
    )

    expense.description = data.description
    expense.expense_date = data.expense_date
    expense.category_id = data.category_id
    expense.payment_method_id = data.payment_method_id
    if schedule_changed:
        expense.amount = new_amount
        expense.installment_count = data.installment_count
        expense.first_installment_date = new_first_date

    try:
        if schedule_changed:
            database.execute(
                delete(ExpenseInstallment).where(ExpenseInstallment.expense_id == expense.id)
            )
            database.expire(expense, ["installments"])
            database.add_all(_build_installments(expense, data))
        database.commit()
        database.refresh(expense)
    except Exception:
        database.rollback()
        raise
    return expense


def delete_expense(database: Session, expense_id: int) -> None:
    """Remove uma compra e todas as suas cobranças."""
    expense = _get_expense(database, expense_id)
    database.delete(expense)
    try:
        database.commit()
    except Exception:
        database.rollback()
        raise


def _total_amount(data: ExpenseCreate) -> Decimal:
    if data.payment_type == "installments" and data.amount_type == "installment":
        return data.amount * data.installment_count
    return data.amount


def _build_installments(expense: Expense, data: ExpenseCreate) -> list[ExpenseInstallment]:
    count = data.installment_count
    total_cents = int(expense.amount * 100)
    installment_cents = total_cents // count
    first_installment_cents = total_cents - (count - 1) * installment_cents
    first_date = expense.first_installment_date
    installments: list[ExpenseInstallment] = []

    for index in range(count):
        month_index = (first_date.year - 1) * 12 + first_date.month - 1 + index
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        day = min(first_date.day, monthrange(year + 1, month)[1])
        amount_cents = first_installment_cents if index == 0 else installment_cents
        installments.append(
            ExpenseInstallment(
                expense_id=expense.id,
                installment_number=index + 1,
                amount=Decimal(amount_cents) / 100,
                due_date=date(year + 1, month, day),
            )
        )
    return installments


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
