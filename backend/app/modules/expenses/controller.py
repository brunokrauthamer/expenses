from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.dependencies import get_current_user_id
from app.modules.expenses.contracts import ExpenseCommand
from app.modules.expenses.dependencies import get_expense_service
from app.modules.expenses.schema import (
    ExpenseCreate,
    ExpenseHistoryItem,
    ExpenseHistoryPage,
    ExpenseInstallmentResponse,
    ExpenseMonthlyPaymentResponse,
    ExpensePage,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdate,
)
from app.modules.expenses.service import ExpenseService
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
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> ExpensePage:
    items, total = service.list(
        user_id,
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
        items=[ExpenseInstallmentResponse(**item) for item in items],
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
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> ExpenseHistoryPage:
    items, total, gross_amount, reimbursement_amount, net_amount = service.history(
        user_id, page, page_size, month, search, category_id, payment_method_id
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
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ExpenseResponse]:
    return [ExpenseResponse(**expense) for expense in service.recent(user_id, limit)]


@router.get("/month", response_model=list[ExpenseMonthlyPaymentResponse])
def get_expenses_paid_in_month(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ExpenseMonthlyPaymentResponse]:
    return [ExpenseMonthlyPaymentResponse(**item) for item in service.in_month(user_id, month)]


@router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expenses_summary(
    start_month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    end_month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    search: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    payment_method_id: int | None = Query(default=None, ge=1),
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> ExpenseSummaryResponse:
    return ExpenseSummaryResponse(
        **service.summary(user_id, start_month, end_month, search, category_id, payment_method_id)
    )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def post_expense(
    data: ExpenseCreate,
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> ExpenseResponse:
    try:
        return ExpenseResponse(**service.create(user_id, _command(data)))
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{expense_id}", response_model=ExpenseResponse)
def put_expense(
    expense_id: int,
    data: ExpenseUpdate,
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> ExpenseResponse:
    try:
        return ExpenseResponse(**service.update(user_id, expense_id, _command(data)))
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_route(
    expense_id: int,
    service: ExpenseService = Depends(get_expense_service),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    try:
        service.delete(user_id, expense_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _command(data: ExpenseCreate | ExpenseUpdate) -> ExpenseCommand:
    return ExpenseCommand(
        description=data.description,
        amount=Decimal(data.amount),
        amount_type=data.amount_type,
        payment_type=data.payment_type,
        installment_count=data.installment_count,
        expense_date=date.fromisoformat(str(data.expense_date)),
        first_installment_date=(
            date.fromisoformat(str(data.first_installment_date))
            if data.first_installment_date is not None
            else None
        ),
        category_id=data.category_id,
        payment_method_id=data.payment_method_id,
    )
