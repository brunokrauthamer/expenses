from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.expenses.schema import (
    ExpenseCreate,
    ExpenseInstallmentResponse,
    ExpensePage,
    ExpenseResponse,
    ExpenseUpdate,
)
from app.modules.expenses.service import create_expense, delete_expense, list_expenses, update_expense
from app.shared.dependencies import get_db
from app.shared.exceptions import ResourceNotFoundError

router = APIRouter(tags=["Despesas"])


@router.get("", response_model=ExpensePage)
def get_expenses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    search: str | None = Query(default=None, max_length=100),
    database: Session = Depends(get_db),
) -> ExpensePage:
    installments, total = list_expenses(database, page, page_size, month, search)
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
            )
            for installment in installments
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def post_expense(data: ExpenseCreate, database: Session = Depends(get_db)) -> ExpenseResponse:
    try:
        return create_expense(database, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.put("/{expense_id}", response_model=ExpenseResponse)
def put_expense(
    expense_id: int,
    data: ExpenseUpdate,
    database: Session = Depends(get_db),
) -> ExpenseResponse:
    try:
        return update_expense(database, expense_id, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_route(expense_id: int, database: Session = Depends(get_db)) -> Response:
    try:
        delete_expense(database, expense_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
