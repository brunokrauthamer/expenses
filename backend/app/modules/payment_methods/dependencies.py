"""FastAPI composition for payment-method use cases."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.payment_methods.model import PaymentMethod
from app.modules.payment_methods.service import PaymentMethodService
from app.shared.catalog_repository import CatalogRepository
from app.shared.dependencies import get_db
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork


def get_payment_method_service(database: Session = Depends(get_db)) -> PaymentMethodService:
    return PaymentMethodService(
        CatalogRepository(database, PaymentMethod),
        SqlAlchemyUnitOfWork(database),
    )
