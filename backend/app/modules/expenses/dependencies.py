"""FastAPI composition for expense use cases."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.expenses.repository import ExpenseRepository
from app.modules.expenses.service import ExpenseService
from app.modules.income_entries.repository import IncomeEntryRepository
from app.modules.income_entries.service import IncomeEntryService
from app.modules.payment_methods.model import PaymentMethod
from app.shared.catalog_repository import CatalogRepository
from app.shared.dependencies import get_db
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork


def get_expense_service(database: Session = Depends(get_db)) -> ExpenseService:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    return ExpenseService(
        ExpenseRepository(database),
        CatalogRepository(database, Category),
        CatalogRepository(database, PaymentMethod),
        IncomeEntryService(IncomeEntryRepository(database), unit_of_work),
        unit_of_work,
    )
