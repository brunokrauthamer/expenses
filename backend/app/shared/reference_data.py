"""Individual reference catalogs and their one-time initialization."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.categories.model import Category
from app.modules.income_entries.model import IncomeCategory
from app.modules.payment_methods.model import PaymentMethod
from app.shared.exceptions import ResourceNotFoundError

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


def initialize_user_reference_data(database: Session, user: User) -> bool:
    """Create the initial catalog once, inside the caller's transaction."""
    if user.reference_data_initialized_at is not None:
        return False

    _add_missing(database, Category, user.id, CATEGORIES)
    _add_missing(database, PaymentMethod, user.id, PAYMENT_METHODS)
    existing_income = {
        name.strip().lower(): requires
        for name, requires in database.execute(
            select(IncomeCategory.name, IncomeCategory.requires_expense_category).where(
                IncomeCategory.user_id == user.id
            )
        )
    }
    database.add_all(
        IncomeCategory(
            user_id=user.id,
            name=name,
            requires_expense_category=requires,
        )
        for name, requires in INCOME_CATEGORIES
        if name.strip().lower() not in existing_income
    )
    user.reference_data_initialized_at = datetime.now(timezone.utc)
    return True


class ReferenceDataRepository:
    """Persistence adapter used by account initialization and the seed command."""

    def __init__(self, database: Session) -> None:
        self._database = database

    def initialize_for_user(self, user_id: UUID) -> bool:
        user = self._database.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise ResourceNotFoundError(f"Usuário não encontrado: {user_id}")
        return initialize_user_reference_data(self._database, user)


def _add_missing(database: Session, model, user_id: UUID, names: tuple[str, ...]) -> None:
    existing = {
        name.strip().lower()
        for name in database.scalars(select(model.name).where(model.user_id == user_id))
    }
    database.add_all(
        model(user_id=user_id, name=name) for name in names if name.strip().lower() not in existing
    )
