from fastapi import FastAPI

import app.modules.registry  # noqa: F401 - registra modelos SQLAlchemy na inicialização.
from app.modules.categories.controller import router as categories_router
from app.modules.expenses.controller import router as expenses_router
from app.modules.payment_methods.controller import router as payment_methods_router

app = FastAPI(title="Expenses API", version="0.1.0")

app.include_router(categories_router, prefix="/categories")
app.include_router(expenses_router, prefix="/expenses")
app.include_router(payment_methods_router, prefix="/payment-methods")
