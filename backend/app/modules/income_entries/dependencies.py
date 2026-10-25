"""FastAPI composition for income use cases."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.income_entries.repository import (
    IncomeCategoryRepository,
    IncomeEntryRepository,
)
from app.modules.income_entries.service import IncomeCategoryService, IncomeEntryService
from app.shared.dependencies import get_db
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork


def get_income_category_service(
    database: Session = Depends(get_db),
) -> IncomeCategoryService:
    return IncomeCategoryService(
        IncomeCategoryRepository(database),
        SqlAlchemyUnitOfWork(database),
    )


def get_income_entry_service(
    database: Session = Depends(get_db),
) -> IncomeEntryService:
    return IncomeEntryService(
        IncomeEntryRepository(database),
        SqlAlchemyUnitOfWork(database),
    )
