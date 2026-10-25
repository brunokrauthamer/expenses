from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.dependencies import get_current_user_id
from app.modules.categories.dependencies import get_category_service
from app.modules.categories.schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.modules.categories.service import CategoryService
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Categorias"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    include_deleted: bool = Query(False),
    service: CategoryService = Depends(get_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    return service.list(user_id, include_deleted)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def post_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.create(user_id, data.name)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{category_id}", response_model=CategoryResponse)
def put_category(
    category_id: int,
    data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.update(category_id, user_id, data.name)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        service.delete(category_id, user_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
