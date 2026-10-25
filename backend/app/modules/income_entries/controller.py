from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.dependencies import get_current_user_id
from app.modules.income_entries.contracts import IncomeEntryCommand
from app.modules.income_entries.dependencies import (
    get_income_category_service,
    get_income_entry_service,
)
from app.modules.income_entries.schema import (
    IncomeCategoryCreate,
    IncomeCategoryResponse,
    IncomeCategoryUpdate,
    IncomeEntryCreate,
    IncomeEntryPage,
    IncomeEntryResponse,
)
from app.modules.income_entries.service import IncomeCategoryService, IncomeEntryService
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Entradas"])
income_categories_router = APIRouter(tags=["Categorias de entrada"])


@income_categories_router.get("", response_model=list[IncomeCategoryResponse])
def get_income_categories(
    include_deleted: bool = Query(False),
    service: IncomeCategoryService = Depends(get_income_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    return service.list(user_id, include_deleted)


@income_categories_router.post(
    "", response_model=IncomeCategoryResponse, status_code=status.HTTP_201_CREATED
)
def post_income_category(
    data: IncomeCategoryCreate,
    service: IncomeCategoryService = Depends(get_income_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.create(user_id, data.name, data.requires_expense_category)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@income_categories_router.put("/{category_id}", response_model=IncomeCategoryResponse)
def put_income_category(
    category_id: int,
    data: IncomeCategoryUpdate,
    service: IncomeCategoryService = Depends(get_income_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.update(
            user_id,
            category_id,
            data.name,
            data.requires_expense_category,
        )
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@income_categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income_category(
    category_id: int,
    service: IncomeCategoryService = Depends(get_income_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        service.delete(user_id, category_id)
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
    service: IncomeEntryService = Depends(get_income_entry_service),
    user_id: UUID = Depends(get_current_user_id),
):
    items, total = service.list(
        user_id,
        page,
        page_size,
        start_month,
        end_month,
        income_category_id,
        expense_category_id,
        search,
    )
    return IncomeEntryPage(
        items=[IncomeEntryResponse(**item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=IncomeEntryResponse, status_code=status.HTTP_201_CREATED)
def post_income_entry(
    data: IncomeEntryCreate,
    service: IncomeEntryService = Depends(get_income_entry_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return IncomeEntryResponse(**service.create(user_id, _command(data)))
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{entry_id}", response_model=IncomeEntryResponse)
def put_income_entry(
    entry_id: int,
    data: IncomeEntryCreate,
    service: IncomeEntryService = Depends(get_income_entry_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return IncomeEntryResponse(**service.update(user_id, entry_id, _command(data)))
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income_entry(
    entry_id: int,
    service: IncomeEntryService = Depends(get_income_entry_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        service.delete(user_id, entry_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _command(data: IncomeEntryCreate) -> IncomeEntryCommand:
    return IncomeEntryCommand(
        description=data.description,
        amount=Decimal(data.amount),
        received_date=date.fromisoformat(str(data.received_date)),
        income_category_id=data.income_category_id,
        expense_category_id=data.expense_category_id,
    )
