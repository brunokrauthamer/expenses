from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.payment_methods.model import PaymentMethod
from app.shared.catalog import create_catalog_item, delete_catalog_item, list_catalog, update_catalog_item


def list_payment_methods(database: Session, user_id: UUID, include_deleted: bool = False) -> list[PaymentMethod]:
    return list_catalog(database, PaymentMethod, user_id, include_deleted)


def create_payment_method(database: Session, user_id: UUID, name: str) -> PaymentMethod:
    return create_catalog_item(database, PaymentMethod, user_id, name)


def update_payment_method(database: Session, method_id: int, user_id: UUID, name: str) -> PaymentMethod:
    return update_catalog_item(database, PaymentMethod, method_id, user_id, name)


def delete_payment_method(database: Session, method_id: int, user_id: UUID) -> None:
    delete_catalog_item(database, PaymentMethod, method_id, user_id)
