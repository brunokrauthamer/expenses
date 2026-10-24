from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.income_entries.schema import (
    IncomeCategoryCreate,
    IncomeCategoryResponse,
    IncomeCategoryUpdate,
    IncomeEntryCreate,
    IncomeEntryPage,
    IncomeEntryResponse,
)
from app.modules.income_entries.service import (
    create_income_category,
    create_income_entry,
    delete_income_category,
    delete_income_entry,
    income_entry_payload,
    list_income_categories,
    list_income_entries,
    update_income_category,
    update_income_entry,
)
from app.shared.auth import get_current_user
from app.shared.dependencies import get_db
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Entradas"])
income_categories_router = APIRouter(tags=["Categorias de entrada"])


@income_categories_router.get("", response_model=list[IncomeCategoryResponse])
def get_income_categories(
    include_deleted: bool = Query(False),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_income_categories(database, user.id, include_deleted)


@income_categories_router.post("", response_model=IncomeCategoryResponse, status_code=status.HTTP_201_CREATED)
def post_income_category(data: IncomeCategoryCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return create_income_category(database, user.id, data.name, data.requires_expense_category)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@income_categories_router.put("/{category_id}", response_model=IncomeCategoryResponse)
def put_income_category(category_id: int, data: IncomeCategoryUpdate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return update_income_category(database, category_id, user.id, data.name, data.requires_expense_category)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@income_categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income_category(category_id: int, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        delete_income_category(database, category_id, user.id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=IncomeEntryPage)
def get_income_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    end_month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    income_category_id: int | None = Query(None, ge=1),
    expense_category_id: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=100),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if (start_month is None) != (end_month is None):
        raise HTTPException(status_code=422, detail="Informe os meses inicial e final do período.")
    if start_month:
        try:
            first, last = datetime.strptime(start_month, "%Y-%m"), datetime.strptime(end_month, "%Y-%m")
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Informe meses válidos.") from error
        if first > last or (last.year - first.year) * 12 + last.month - first.month >= 120:
            raise HTTPException(status_code=422, detail="Informe um período válido de até 120 meses.")
    items, total = list_income_entries(
        database, user.id, page, page_size, start_month, end_month,
        income_category_id, expense_category_id, search,
    )
    return IncomeEntryPage(items=items, page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=IncomeEntryResponse, status_code=status.HTTP_201_CREATED)
def post_income_entry(data: IncomeEntryCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        entry = create_income_entry(database, user.id, data)
        return income_entry_payload(database, entry)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{entry_id}", response_model=IncomeEntryResponse)
def put_income_entry(entry_id: int, data: IncomeEntryCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        entry = update_income_entry(database, user.id, entry_id, data)
        return income_entry_payload(database, entry)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income_entry(entry_id: int, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        delete_income_entry(database, user.id, entry_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
