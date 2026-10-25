from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, case, delete, func, literal, or_, select, union_all
from sqlalchemy.orm import Session, selectinload

from app.modules.categories.model import Category
from app.modules.expenses.contracts import ExpenseCommand, ExpenseState
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.expenses.rules import InstallmentSpec
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.payment_methods.model import PaymentMethod
from app.shared.exceptions import ResourceNotFoundError


def list_expenses(
    database: Session,
    user_id: UUID,
    page: int,
    page_size: int,
    month: str | None = None,
    search: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
) -> tuple[list[ExpenseInstallment], int]:
    """Retorna cobranças paginadas, com filtros compartilhados com os relatórios."""
    from_expense, filters = _filtered_expenses(
        user_id=user_id,
        month=month,
        search=search,
        start_month=start_month,
        end_month=end_month,
        category_id=category_id,
        payment_method_id=payment_method_id,
    )
    statement = (
        select(
            ExpenseInstallment,
            Category.name,
            Category.deleted_at,
            PaymentMethod.name,
            PaymentMethod.deleted_at,
        )
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
    count_statement = select(func.count()).select_from(from_expense).where(*filters)
    rows = database.execute(statement).all()
    return [
        _installment_payload(row[0], row[1], row[2], row[3], row[4]) for row in rows
    ], database.scalar(count_statement) or 0


def list_expense_history(
    database: Session,
    user_id: UUID,
    page: int,
    page_size: int,
    month: str,
    search: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
):
    """Combina cobranças e reembolsos em uma lista ordenada por data do evento."""
    expense_from, expense_filters = _filtered_expenses(
        user_id=user_id,
        month=month,
        search=search,
        category_id=category_id,
        payment_method_id=payment_method_id,
    )
    expense_rows = (
        select(
            literal("expense").label("kind"),
            Expense.id.label("id"),
            ExpenseInstallment.id.label("installment_id"),
            Expense.description.label("description"),
            ExpenseInstallment.due_date.label("event_date"),
            ExpenseInstallment.amount.label("amount"),
            Expense.category_id.label("category_id"),
            Expense.payment_method_id.label("payment_method_id"),
            case((Expense.installment_count == 1, "one_time"), else_="installments").label(
                "payment_type"
            ),
            ExpenseInstallment.installment_number.label("installment_number"),
            Expense.installment_count.label("installment_count"),
            Expense.first_installment_date.label("first_installment_date"),
            Expense.amount.label("total_amount"),
            Category.name.label("category_name"),
            Category.deleted_at.is_not(None).label("category_deleted"),
            PaymentMethod.name.label("payment_method_name"),
            PaymentMethod.deleted_at.is_not(None).label("payment_method_deleted"),
            literal(None).label("income_category_name"),
            literal(None).label("income_category_deleted"),
        )
        .select_from(expense_from)
        .where(*expense_filters)
    )

    year, month_number = map(int, month.split("-"))
    first_day = date(year, month_number, 1)
    last_day = date(year, month_number, monthrange(year, month_number)[1])
    reimbursement_filters = [
        IncomeEntry.user_id == user_id,
        IncomeEntry.received_date.between(first_day, last_day),
        IncomeCategory.user_id == user_id,
        IncomeCategory.requires_expense_category.is_(True),
    ]
    if category_id is not None:
        reimbursement_filters.append(IncomeEntry.expense_category_id == category_id)
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        reimbursement_filters.append(
            or_(
                IncomeEntry.description.ilike(pattern),
                IncomeCategory.name.ilike(pattern),
                Category.name.ilike(pattern),
            )
        )
    reimbursement_from = IncomeEntry.__table__.join(
        IncomeCategory.__table__,
        (IncomeEntry.income_category_id == IncomeCategory.id)
        & (IncomeEntry.user_id == IncomeCategory.user_id),
    ).join(
        Category.__table__,
        (IncomeEntry.expense_category_id == Category.id)
        & (IncomeEntry.user_id == Category.user_id),
    )
    reimbursement_rows = (
        select(
            literal("reimbursement").label("kind"),
            IncomeEntry.id.label("id"),
            literal(None, type_=Integer).label("installment_id"),
            IncomeEntry.description.label("description"),
            IncomeEntry.received_date.label("event_date"),
            IncomeEntry.amount.label("amount"),
            IncomeEntry.expense_category_id.label("category_id"),
            literal(None, type_=Integer).label("payment_method_id"),
            literal(None).label("payment_type"),
            literal(None, type_=Integer).label("installment_number"),
            literal(None, type_=Integer).label("installment_count"),
            literal(None).label("first_installment_date"),
            literal(None).label("total_amount"),
            Category.name.label("category_name"),
            Category.deleted_at.is_not(None).label("category_deleted"),
            literal(None).label("payment_method_name"),
            literal(None).label("payment_method_deleted"),
            IncomeCategory.name.label("income_category_name"),
            IncomeCategory.deleted_at.is_not(None).label("income_category_deleted"),
        )
        .select_from(reimbursement_from)
        .where(*reimbursement_filters)
    )

    combined = union_all(expense_rows, reimbursement_rows).subquery()
    total = database.scalar(select(func.count()).select_from(combined)) or 0
    amounts_by_kind = dict(
        database.execute(
            select(combined.c.kind, func.sum(combined.c.amount)).group_by(combined.c.kind)
        ).all()
    )
    gross_amount = amounts_by_kind.get("expense") or Decimal("0.00")
    reimbursement_amount = amounts_by_kind.get("reimbursement") or Decimal("0.00")
    statement = (
        select(combined)
        .order_by(combined.c.event_date.desc(), combined.c.id.desc(), combined.c.kind.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return (
        list(database.execute(statement).mappings()),
        total,
        gross_amount,
        reimbursement_amount,
        gross_amount - reimbursement_amount,
    )


def list_recent_expenses(database: Session, user_id: UUID, limit: int):
    """Retorna compras únicas, ordenadas pela data de cadastro."""
    statement = (
        select(
            Expense,
            Category.name,
            Category.deleted_at,
            PaymentMethod.name,
            PaymentMethod.deleted_at,
        )
        .join(
            Category, (Expense.category_id == Category.id) & (Expense.user_id == Category.user_id)
        )
        .join(
            PaymentMethod,
            (Expense.payment_method_id == PaymentMethod.id)
            & (Expense.user_id == PaymentMethod.user_id),
        )
        .where(Expense.user_id == user_id)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .limit(limit)
    )
    return [
        _expense_payload(row[0], row[1], row[2], row[3], row[4])
        for row in database.execute(statement).all()
    ]


def list_expenses_paid_in_month(database: Session, user_id: UUID, month: str):
    """Retorna cada cobranÃ§a do mÃªs com os dados da compra correspondente."""
    first_day = date.fromisoformat(f"{month}-01")
    year, month_number = map(int, month.split("-"))
    last_day = date(year, month_number, monthrange(year, month_number)[1])
    statement = (
        select(
            Expense,
            ExpenseInstallment,
            Category.name,
            Category.deleted_at,
            PaymentMethod.name,
            PaymentMethod.deleted_at,
        )
        .join(ExpenseInstallment, ExpenseInstallment.expense_id == Expense.id)
        .join(
            Category, (Expense.category_id == Category.id) & (Expense.user_id == Category.user_id)
        )
        .join(
            PaymentMethod,
            (Expense.payment_method_id == PaymentMethod.id)
            & (Expense.user_id == PaymentMethod.user_id),
        )
        .where(Expense.user_id == user_id, ExpenseInstallment.due_date.between(first_day, last_day))
        .order_by(
            Expense.expense_date.desc(),
            Expense.id.desc(),
            ExpenseInstallment.installment_number.asc(),
        )
    )
    return [
        _month_expense_payload(row[0], row[1], row[2], row[3], row[4], row[5])
        for row in database.execute(statement).all()
    ]


def get_expense_summary_rows(
    database: Session,
    user_id: UUID,
    start_month: str,
    end_month: str,
    search: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
) -> list[tuple[str, int, Decimal]]:
    """Return SQL-aggregated expense facts without applying reimbursement rules."""
    from_expense, filters = _filtered_expenses(
        user_id=user_id,
        start_month=start_month,
        end_month=end_month,
        search=search,
        category_id=category_id,
        payment_method_id=payment_method_id,
    )
    month_expression = _month_expression(database.get_bind().dialect.name)
    statement = (
        select(
            month_expression.label("month"),
            Expense.category_id.label("category_id"),
            func.sum(ExpenseInstallment.amount).label("amount_due"),
        )
        .select_from(from_expense)
        .where(*filters)
        .group_by(month_expression, Expense.category_id)
        .order_by(month_expression, Expense.category_id)
    )

    return [
        (str(month)[:7], int(category_id), Decimal(amount))
        for month, category_id, amount in database.execute(statement)
    ]


def _filtered_expenses(
    user_id: UUID,
    month: str | None = None,
    search: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
):
    filters = [
        Expense.user_id == user_id,
        Category.user_id == user_id,
        PaymentMethod.user_id == user_id,
    ]
    if month:
        start_month = end_month = month
    if start_month and end_month:
        first_day = date.fromisoformat(f"{start_month}-01")
        last_year, last_month = map(int, end_month.split("-"))
        last_day = date(last_year, last_month, monthrange(last_year, last_month)[1])
        filters.append(ExpenseInstallment.due_date.between(first_day, last_day))
    if category_id is not None:
        filters.append(Expense.category_id == category_id)
    if payment_method_id is not None:
        filters.append(Expense.payment_method_id == payment_method_id)

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
        ExpenseInstallment.__table__.join(
            Expense.__table__, ExpenseInstallment.expense_id == Expense.id
        )
        .join(
            Category.__table__,
            (Expense.category_id == Category.id) & (Expense.user_id == Category.user_id),
        )
        .join(
            PaymentMethod.__table__,
            (Expense.payment_method_id == PaymentMethod.id)
            & (Expense.user_id == PaymentMethod.user_id),
        )
    )
    return from_expense, filters


def _month_expression(dialect: str):
    """Extrai o mês usando a função nativa do PostgreSQL ou SQLite."""
    from sqlalchemy import String, cast

    if dialect == "sqlite":
        return func.strftime("%Y-%m", ExpenseInstallment.due_date)
    if dialect == "postgresql":
        return func.to_char(ExpenseInstallment.due_date, "YYYY-MM")
    return cast(ExpenseInstallment.due_date, String)


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


def create_expense(
    database: Session,
    user_id: UUID,
    data: ExpenseCommand,
    amount: Decimal,
    installments: list[InstallmentSpec],
) -> dict:
    """Persist a validated purchase and its already calculated schedule."""
    expense = Expense(
        description=data.description,
        amount=amount,
        expense_date=data.expense_date,
        installment_count=data.installment_count,
        first_installment_date=data.first_installment_date or data.expense_date,
        category_id=data.category_id,
        payment_method_id=data.payment_method_id,
        user_id=user_id,
    )
    database.add(expense)
    database.flush()
    database.add_all(
        ExpenseInstallment(
            expense_id=expense.id,
            installment_number=item.number,
            amount=item.amount,
            due_date=item.due_date,
        )
        for item in installments
    )
    database.flush()
    return _expense_response(database, expense)


def update_expense(
    database: Session,
    user_id: UUID,
    expense_id: int,
    data: ExpenseCommand,
    amount: Decimal,
    installments: list[InstallmentSpec],
    schedule_changed: bool,
) -> dict:
    """Persist an updated purchase and, when requested, replace its schedule."""
    expense = _get_expense(database, user_id, expense_id)
    new_first_date = data.first_installment_date or data.expense_date

    expense.description = data.description
    expense.expense_date = data.expense_date
    expense.category_id = data.category_id
    expense.payment_method_id = data.payment_method_id
    if schedule_changed:
        expense.amount = amount
        expense.installment_count = data.installment_count
        expense.first_installment_date = new_first_date

    if schedule_changed:
        database.execute(
            delete(ExpenseInstallment).where(ExpenseInstallment.expense_id == expense.id)
        )
        database.expire(expense, ["installments"])
        database.add_all(
            ExpenseInstallment(
                expense_id=expense.id,
                installment_number=item.number,
                amount=item.amount,
                due_date=item.due_date,
            )
            for item in installments
        )
    database.flush()
    return _expense_response(database, expense)


def delete_expense(database: Session, user_id: UUID, expense_id: int) -> None:
    """Remove uma compra e todas as suas cobranças."""
    expense = _get_expense(database, user_id, expense_id)
    database.delete(expense)
    database.flush()


def _get_expense(database: Session, user_id: UUID, expense_id: int) -> Expense:
    expense = database.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
    )
    if expense is None:
        raise ResourceNotFoundError("Despesa não encontrada.")
    return expense


def get_expense_state(database: Session, user_id: UUID, expense_id: int) -> ExpenseState | None:
    expense = database.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
    )
    if expense is None:
        return None
    return ExpenseState(
        id=expense.id,
        amount=expense.amount,
        expense_date=expense.expense_date,
        installment_count=expense.installment_count,
        first_installment_date=expense.first_installment_date,
        category_id=expense.category_id,
        payment_method_id=expense.payment_method_id,
    )


def _installment_payload(
    installment, category_name, category_deleted_at, method_name, method_deleted_at
) -> dict:
    expense = installment.expense
    return {
        "id": expense.id,
        "installment_id": installment.id,
        "description": expense.description,
        "expense_date": expense.expense_date,
        "due_date": installment.due_date,
        "payment_type": expense.payment_type,
        "installment_number": installment.installment_number,
        "installment_count": expense.installment_count,
        "first_installment_date": expense.first_installment_date,
        "amount_due": installment.amount,
        "total_amount": expense.amount,
        "category_id": expense.category_id,
        "payment_method_id": expense.payment_method_id,
        "category_name": category_name,
        "category_deleted": category_deleted_at is not None,
        "payment_method_name": method_name,
        "payment_method_deleted": method_deleted_at is not None,
    }


def _expense_payload(
    expense, category_name, category_deleted_at, method_name, method_deleted_at
) -> dict:
    return {
        "id": expense.id,
        "description": expense.description,
        "amount": expense.amount,
        "expense_date": expense.expense_date,
        "payment_type": expense.payment_type,
        "installment_count": expense.installment_count,
        "first_installment_date": expense.first_installment_date,
        "category_id": expense.category_id,
        "payment_method_id": expense.payment_method_id,
        "created_at": expense.created_at,
        "category_name": category_name,
        "category_deleted": category_deleted_at is not None,
        "payment_method_name": method_name,
        "payment_method_deleted": method_deleted_at is not None,
    }


def _month_expense_payload(
    expense, installment, category_name, category_deleted_at, method_name, method_deleted_at
) -> dict:
    item = _expense_payload(
        expense, category_name, category_deleted_at, method_name, method_deleted_at
    )
    item.update(
        due_date=installment.due_date,
        installment_number=installment.installment_number,
        installment_amount=installment.amount,
    )
    return item


def _expense_response(database: Session, expense: Expense) -> dict:
    category = database.scalar(
        select(Category).where(
            Category.id == expense.category_id,
            Category.user_id == expense.user_id,
        )
    )
    payment_method = database.scalar(
        select(PaymentMethod).where(
            PaymentMethod.id == expense.payment_method_id,
            PaymentMethod.user_id == expense.user_id,
        )
    )
    return _expense_payload(
        expense,
        category.name if category else None,
        category.deleted_at if category else None,
        payment_method.name if payment_method else None,
        payment_method.deleted_at if payment_method else None,
    )


class ExpenseRepository:
    """Data access facade; writes flush and leave commit to the caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *args, **kwargs):
        return list_expenses(self._session, *args, **kwargs)

    def history(self, *args, **kwargs):
        return list_expense_history(self._session, *args, **kwargs)

    def recent(self, *args, **kwargs):
        return list_recent_expenses(self._session, *args, **kwargs)

    def in_month(self, *args, **kwargs):
        return list_expenses_paid_in_month(self._session, *args, **kwargs)

    def summary(self, *args, **kwargs):
        return get_expense_summary_rows(self._session, *args, **kwargs)

    def get_state(self, *args, **kwargs):
        return get_expense_state(self._session, *args, **kwargs)

    def create(self, *args, **kwargs):
        return create_expense(self._session, *args, **kwargs)

    def update(self, *args, **kwargs):
        return update_expense(self._session, *args, **kwargs)

    def delete(self, *args, **kwargs):
        return delete_expense(self._session, *args, **kwargs)
