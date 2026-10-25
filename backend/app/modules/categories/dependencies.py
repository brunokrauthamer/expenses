"""FastAPI composition for expense-category use cases."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.categories.service import CategoryService
from app.shared.catalog_repository import CatalogRepository
from app.shared.dependencies import get_db
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork


def get_category_service(database: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(
        CatalogRepository(database, Category),
        SqlAlchemyUnitOfWork(database),
    )
