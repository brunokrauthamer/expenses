from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.expenses.schema import (
    ExpenseCreate,
    ExpenseInstallmentResponse,
    ExpenseHistoryItem,
    ExpenseHistoryPage,
    ExpenseMonthlyPaymentResponse,
    ExpensePage,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdate,
)
from app.modules.expenses.service import (
    create_expense,
    delete_expense,
    get_expense_summary,
    list_expense_history,
    list_expenses_paid_in_month,
    list_expenses,
    list_recent_expenses,
    update_expense,
)
from app.shared.dependencies import get_db
from app.shared.auth import get_current_user
from app.shared.exceptions import ResourceNotFoundError

router = APIRouter(tags=["Despesas"])


@router.get("", response_model=ExpensePage)
def get_expenses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    start_month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    end_month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    search: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    payment_method_id: int | None = Query(default=None, ge=1),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpensePage:
    _validate_month_range(month, start_month, end_month)
    installments, total = list_expenses(
        database,
        user.id,
        page,
        page_size,
        month,
        search,
        start_month,
        end_month,
        category_id,
        payment_method_id,
    )
    return ExpensePage(
        items=[
            ExpenseInstallmentResponse(
                id=installment.expense_id,
                installment_id=installment.id,
                description=installment.expense.description,
                expense_date=installment.expense.expense_date,
                due_date=installment.due_date,
                payment_type=installment.expense.payment_type,
                installment_number=installment.installment_number,
                installment_count=installment.expense.installment_count,
                first_installment_date=installment.expense.first_installment_date,
                amount_due=installment.amount,
                total_amount=installment.expense.amount,
                category_id=installment.expense.category_id,
                payment_method_id=installment.expense.payment_method_id,
                category_name=category_name,
                category_deleted=category_deleted_at is not None,
                payment_method_name=payment_method_name,
                payment_method_deleted=payment_method_deleted_at is not None,
            )
            for installment, category_name, category_deleted_at, payment_method_name, payment_method_deleted_at in installments
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/history", response_model=ExpenseHistoryPage)
def get_expense_history(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    payment_method_id: int | None = Query(default=None, ge=1),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpenseHistoryPage:
    _validate_month_range(month, None, None)
    items, total, gross_amount, reimbursement_amount, net_amount = list_expense_history(
        database, user.id, page, page_size, month, search, category_id, payment_method_id
    )
    return ExpenseHistoryPage(
        items=[ExpenseHistoryItem(**item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
        gross_expense_amount=gross_amount,
        reimbursement_amount=reimbursement_amount,
        net_expense_amount=net_amount,
    )
@router.get("/recent", response_model=list[ExpenseResponse])
def get_recent_expenses(
    limit: int = Query(default=10, ge=1, le=50),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExpenseResponse]:
    return [
        ExpenseResponse(
            id=expense.id,
            description=expense.description,
            amount=expense.amount,
            expense_date=expense.expense_date,
            payment_type=expense.payment_type,
            installment_count=expense.installment_count,
            first_installment_date=expense.first_installment_date,
            category_id=expense.category_id,
            payment_method_id=expense.payment_method_id,
            created_at=expense.created_at,
            category_name=category_name,
            category_deleted=category_deleted_at is not None,
            payment_method_name=payment_method_name,
            payment_method_deleted=payment_method_deleted_at is not None,
        )
        for expense, category_name, category_deleted_at, payment_method_name, payment_method_deleted_at in list_recent_expenses(database, user.id, limit)
    ]


@router.get("/month", response_model=list[ExpenseMonthlyPaymentResponse])
def get_expenses_paid_in_month(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExpenseMonthlyPaymentResponse]:
    return [
        ExpenseMonthlyPaymentResponse(
            id=expense.id,
            description=expense.description,
            amount=expense.amount,
            expense_date=expense.expense_date,
            payment_type=expense.payment_type,
            installment_count=expense.installment_count,
            first_installment_date=expense.first_installment_date,
            category_id=expense.category_id,
            payment_method_id=expense.payment_method_id,
            created_at=expense.created_at,
            due_date=installment.due_date,
            installment_number=installment.installment_number,
            installment_amount=installment.amount,
            category_name=category_name,
            category_deleted=category_deleted_at is not None,
            payment_method_name=payment_method_name,
            payment_method_deleted=payment_method_deleted_at is not None,
        )
        for expense, installment, category_name, category_deleted_at, payment_method_name, payment_method_deleted_at in list_expenses_paid_in_month(database, user.id, month)
    ]


@router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expenses_summary(
    start_month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    end_month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    search: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    payment_method_id: int | None = Query(default=None, ge=1),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpenseSummaryResponse:
    _validate_month_range(None, start_month, end_month)
    return get_expense_summary(
        database, user.id, start_month, end_month, search, category_id, payment_method_id
    )


def _validate_month_range(
    month: str | None, start_month: str | None, end_month: str | None
) -> None:
    if (start_month is None) != (end_month is None):
        raise HTTPException(
            status_code=422,
            detail="Informe os meses inicial e final do período.",
        )
    if month is not None and start_month is not None:
        raise HTTPException(
            status_code=422,
            detail="Use o filtro de mês ou o intervalo, não os dois.",
        )
    values = [value for value in (month, start_month, end_month) if value is not None]
    try:
        parsed = [datetime.strptime(value, "%Y-%m") for value in values]
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="Informe meses válidos no formato AAAA-MM.",
        ) from error
    if len(parsed) == 2 and parsed[0] > parsed[1]:
        raise HTTPException(
            status_code=422,
            detail="O mês inicial não pode ser posterior ao mês final.",
        )
    period_length = (
        (parsed[1].year - parsed[0].year) * 12 + parsed[1].month - parsed[0].month
        if len(parsed) == 2
        else 0
    )
    if period_length >= 120:
        raise HTTPException(
            status_code=422,
            detail="O período não pode exceder 120 meses.",
        )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def post_expense(data: ExpenseCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExpenseResponse:
    try:
        return create_expense(database, user.id, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{expense_id}", response_model=ExpenseResponse)
def put_expense(
    expense_id: int,
    data: ExpenseUpdate,
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpenseResponse:
    try:
        return update_expense(database, user.id, expense_id, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_route(expense_id: int, database: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    try:
        delete_expense(database, user.id, expense_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
