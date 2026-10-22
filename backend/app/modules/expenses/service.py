from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import Integer, case, delete, func, literal, or_, select, union_all
from sqlalchemy.orm import Session, selectinload

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.expenses.schema import ExpenseCreate, ExpenseUpdate
from app.modules.income_entries.service import reimbursement_totals
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.payment_methods.model import PaymentMethod
from app.shared.exceptions import ResourceNotFoundError


def list_expenses(
    database: Session,
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
        month=month,
        search=search,
        start_month=start_month,
        end_month=end_month,
        category_id=category_id,
        payment_method_id=payment_method_id,
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


def list_expense_history(
    database: Session,
    page: int,
    page_size: int,
    month: str,
    search: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
):
    """Combina cobranças e reembolsos em uma lista ordenada por data do evento."""
    expense_from, expense_filters = _filtered_expenses(
        month=month,
        search=search,
        category_id=category_id,
        payment_method_id=payment_method_id,
    )
    expense_rows = select(
        literal("expense").label("kind"),
        Expense.id.label("id"),
        ExpenseInstallment.id.label("installment_id"),
        Expense.description.label("description"),
        ExpenseInstallment.due_date.label("event_date"),
        ExpenseInstallment.amount.label("amount"),
        Expense.category_id.label("category_id"),
        Expense.payment_method_id.label("payment_method_id"),
        case((Expense.installment_count == 1, "one_time"), else_="installments").label("payment_type"),
        ExpenseInstallment.installment_number.label("installment_number"),
        Expense.installment_count.label("installment_count"),
        Expense.first_installment_date.label("first_installment_date"),
        Expense.amount.label("total_amount"),
    ).select_from(expense_from).where(*expense_filters)

    year, month_number = map(int, month.split("-"))
    first_day = date(year, month_number, 1)
    last_day = date(year, month_number, monthrange(year, month_number)[1])
    reimbursement_filters = [
        IncomeEntry.received_date.between(first_day, last_day),
        IncomeCategory.requires_expense_category.is_(True),
    ]
    if category_id is not None:
        reimbursement_filters.append(IncomeEntry.expense_category_id == category_id)
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{normalized_search}%"
        reimbursement_filters.append(or_(
            IncomeEntry.description.ilike(pattern),
            IncomeCategory.name.ilike(pattern),
            Category.name.ilike(pattern),
        ))
    reimbursement_from = (
        IncomeEntry.__table__
        .join(IncomeCategory.__table__, IncomeEntry.income_category_id == IncomeCategory.id)
        .join(Category.__table__, IncomeEntry.expense_category_id == Category.id)
    )
    reimbursement_rows = select(
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
    ).select_from(reimbursement_from).where(*reimbursement_filters)

    combined = union_all(expense_rows, reimbursement_rows).subquery()
    total = database.scalar(select(func.count()).select_from(combined)) or 0
    amounts_by_kind = dict(database.execute(
        select(combined.c.kind, func.sum(combined.c.amount)).group_by(combined.c.kind)
    ).all())
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


def list_recent_expenses(database: Session, limit: int) -> list[Expense]:
    """Retorna compras únicas, ordenadas pela data de cadastro."""
    statement = (
        select(Expense)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .limit(limit)
    )
    return list(database.scalars(statement))


def list_expenses_paid_in_month(
    database: Session, month: str
) -> list[tuple[Expense, ExpenseInstallment]]:
    """Retorna cada cobranÃ§a do mÃªs com os dados da compra correspondente."""
    first_day = date.fromisoformat(f"{month}-01")
    year, month_number = map(int, month.split("-"))
    last_day = date(year, month_number, monthrange(year, month_number)[1])
    statement = (
        select(Expense, ExpenseInstallment)
        .join(ExpenseInstallment, ExpenseInstallment.expense_id == Expense.id)
        .where(ExpenseInstallment.due_date.between(first_day, last_day))
        .order_by(
            Expense.expense_date.desc(),
            Expense.id.desc(),
            ExpenseInstallment.installment_number.asc(),
        )
    )
    return list(database.execute(statement))


def get_expense_summary(
    database: Session,
    start_month: str,
    end_month: str,
    search: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
) -> dict[str, object]:
    """Agrega uma única consulta por mês e categoria para alimentar o resumo e os gráficos."""
    from_expense, filters = _filtered_expenses(
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

    month_amounts: dict[str, Decimal] = {}
    category_amounts: dict[int, Decimal] = {}
    for month, expense_category_id, amount_due in database.execute(statement):
        month = str(month)[:7]
        amount = Decimal(amount_due)
        month_amounts[month] = month_amounts.get(month, Decimal("0.00")) + amount
        expense_category_id = int(expense_category_id)
        category_amounts[expense_category_id] = (
            category_amounts.get(expense_category_id, Decimal("0.00")) + amount
        )

    reimbursement_months, reimbursement_categories = reimbursement_totals(
        database, start_month, end_month, category_id, search,
        include=payment_method_id is None,
    )
    months = _months_between(start_month, end_month)
    monthly_totals = []
    for month in months:
        gross = month_amounts.get(month, Decimal("0.00"))
        reimbursement = reimbursement_months.get(month, Decimal("0.00"))
        monthly_totals.append({
            "month": month,
            "amount_due": gross - reimbursement,
            "gross_expense_amount": gross,
            "reimbursement_amount": reimbursement,
            "net_expense_amount": gross - reimbursement,
        })
    category_totals = []
    for expense_category_id in set(category_amounts) | set(reimbursement_categories):
        gross = category_amounts.get(expense_category_id, Decimal("0.00"))
        reimbursement = reimbursement_categories.get(expense_category_id, Decimal("0.00"))
        category_totals.append({
            "category_id": expense_category_id,
            "amount_due": gross - reimbursement,
            "gross_expense_amount": gross,
            "reimbursement_amount": reimbursement,
            "net_expense_amount": gross - reimbursement,
        })
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


def _filtered_expenses(
    month: str | None = None,
    search: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    category_id: int | None = None,
    payment_method_id: int | None = None,
):
    filters = []
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
        ExpenseInstallment.__table__
        .join(Expense.__table__, ExpenseInstallment.expense_id == Expense.id)
        .join(Category.__table__, Expense.category_id == Category.id)
        .join(PaymentMethod.__table__, Expense.payment_method_id == PaymentMethod.id)
    )
    return from_expense, filters


def _month_expression(dialect: str):
    """Extrai o mês usando a função nativa do PostgreSQL ou SQLite."""
    from sqlalchemy import cast, String

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
