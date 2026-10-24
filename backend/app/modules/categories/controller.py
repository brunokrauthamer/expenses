from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.categories.schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.modules.categories.service import create_category, delete_category, list_categories, update_category
from app.shared.auth import get_current_user
from app.shared.dependencies import get_db
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Categorias"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    include_deleted: bool = Query(False),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_categories(database, user.id, include_deleted)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def post_category(data: CategoryCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return create_category(database, user.id, data.name)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{category_id}", response_model=CategoryResponse)
def put_category(category_id: int, data: CategoryUpdate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return update_category(database, category_id, user.id, data.name)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(category_id: int, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        delete_category(database, category_id, user.id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
