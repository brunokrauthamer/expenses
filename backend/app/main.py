from fastapi import FastAPI
from fastapi import Depends

import app.modules.registry  # noqa: F401 - registra modelos SQLAlchemy na inicialização.
from app.modules.categories.controller import router as categories_router
from app.modules.auth.controller import router as auth_router
from app.modules.expenses.controller import router as expenses_router
from app.modules.income_entries.controller import income_categories_router, router as income_entries_router
from app.modules.payment_methods.controller import router as payment_methods_router
from app.shared.auth import get_current_user

app = FastAPI(title="Expenses API", version="0.1.0")

app.include_router(auth_router, prefix="/auth")
protected = [Depends(get_current_user)]
app.include_router(categories_router, prefix="/categories", dependencies=protected)
app.include_router(expenses_router, prefix="/expenses", dependencies=protected)
app.include_router(income_entries_router, prefix="/income-entries", dependencies=protected)
app.include_router(income_categories_router, prefix="/income-categories", dependencies=protected)
app.include_router(payment_methods_router, prefix="/payment-methods", dependencies=protected)
