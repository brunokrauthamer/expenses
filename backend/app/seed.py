"""Popula categorias e meios de pagamento iniciais.

Execute a partir da pasta ``backend`` com ``python -m app.seed``.
O seeder pode ser executado novamente sem duplicar registros existentes.
"""

from sqlalchemy import select

from app.database import SessionLocal
import app.modules.registry  # noqa: F401 - registra todos os modelos e relações.
from app.modules.categories.model import Category
from app.modules.payment_methods.model import PaymentMethod
from app.modules.income_entries.model import IncomeCategory


CATEGORIES = (
    "Mercado",
    "Lazer",
    "Restaurante",
    "Transporte",
    "Carro",
    "Presentes",
    "Faxina",
    "Serviços",
    "Cuidados Pessoais",
    "Saúde",
    "Viagem",
    "Boletos",
    "Moradia",
    "Itens para casa",
)

PAYMENT_METHODS = ("PIX", "Cartão de Crédito")
INCOME_CATEGORIES = (("Salário", False), ("Reembolso", True))


def seed_initial_data() -> None:
    """Insere os registros iniciais ausentes, preservando os existentes."""
    with SessionLocal() as database:
        existing_categories = set(database.scalars(select(Category.name)))
        existing_payment_methods = set(database.scalars(select(PaymentMethod.name)))
        existing_income_categories = set(database.scalars(select(IncomeCategory.name)))

        database.add_all(
            Category(name=name)
            for name in CATEGORIES
            if name not in existing_categories
        )
        database.add_all(
            PaymentMethod(name=name)
            for name in PAYMENT_METHODS
            if name not in existing_payment_methods
        )
        database.add_all(
            IncomeCategory(name=name, requires_expense_category=requires_expense_category)
            for name, requires_expense_category in INCOME_CATEGORIES
            if name not in existing_income_categories
        )
        database.commit()


if __name__ == "__main__":
    seed_initial_data()
