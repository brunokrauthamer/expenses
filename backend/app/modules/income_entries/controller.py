from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.income_entries.schema import IncomeCategoryResponse, IncomeEntryCreate, IncomeEntryPage, IncomeEntryResponse
from app.modules.income_entries.service import create_income_entry, delete_income_entry, list_income_categories, list_income_entries, update_income_entry
from app.shared.dependencies import get_db
from app.shared.exceptions import ResourceNotFoundError

router = APIRouter(tags=["Entradas"])
income_categories_router = APIRouter(tags=["Categorias de entrada"])


@income_categories_router.get("", response_model=list[IncomeCategoryResponse])
def get_income_categories(database: Session = Depends(get_db)):
    return list_income_categories(database)


@router.get("", response_model=IncomeEntryPage)
def get_income_entries(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), start_month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), end_month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), income_category_id: int | None = Query(None, ge=1), expense_category_id: int | None = Query(None, ge=1), search: str | None = Query(None, max_length=100), database: Session = Depends(get_db)):
    if (start_month is None) != (end_month is None):
        raise HTTPException(status_code=422, detail="Informe os meses inicial e final do período.")
    if start_month:
        try:
            first, last = datetime.strptime(start_month, "%Y-%m"), datetime.strptime(end_month, "%Y-%m")
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Informe meses válidos.") from error
        if first > last or (last.year - first.year) * 12 + last.month - first.month >= 120:
            raise HTTPException(status_code=422, detail="Informe um período válido de até 120 meses.")
    items, total = list_income_entries(database, page, page_size, start_month, end_month, income_category_id, expense_category_id, search)
    return IncomeEntryPage(items=items, page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=IncomeEntryResponse, status_code=status.HTTP_201_CREATED)
def post_income_entry(data: IncomeEntryCreate, database: Session = Depends(get_db)):
    try:
        return create_income_entry(database, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{entry_id}", response_model=IncomeEntryResponse)
def put_income_entry(entry_id: int, data: IncomeEntryCreate, database: Session = Depends(get_db)):
    try:
        return update_income_entry(database, entry_id, data)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income_entry(entry_id: int, database: Session = Depends(get_db)):
    try:
        delete_income_entry(database, entry_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
