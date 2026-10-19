from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.categories.schema import CategoryResponse
from app.modules.categories.service import list_categories
from app.shared.dependencies import get_db

router = APIRouter(tags=["Categorias"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(database: Session = Depends(get_db)) -> list[CategoryResponse]:
    return list_categories(database)
