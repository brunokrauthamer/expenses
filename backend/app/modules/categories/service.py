from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.shared.catalog import create_catalog_item, delete_catalog_item, list_catalog, update_catalog_item


def list_categories(database: Session, user_id: UUID, include_deleted: bool = False) -> list[Category]:
    return list_catalog(database, Category, user_id, include_deleted)


def create_category(database: Session, user_id: UUID, name: str) -> Category:
    return create_catalog_item(database, Category, user_id, name)


def update_category(database: Session, category_id: int, user_id: UUID, name: str) -> Category:
    return update_catalog_item(database, Category, category_id, user_id, name)


def delete_category(database: Session, category_id: int, user_id: UUID) -> None:
    delete_catalog_item(database, Category, category_id, user_id)
