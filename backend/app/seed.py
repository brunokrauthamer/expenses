"""Inicializa o catálogo de referência de uma conta específica."""

import argparse
from uuid import UUID

from sqlalchemy import select

from app.database import SessionLocal
import app.modules.registry  # noqa: F401 - registra todos os modelos e relações.
from app.modules.auth.model import User
from app.shared.reference_data import initialize_user_reference_data


def seed_initial_data(user_id: UUID) -> bool:
    """Insere o catálogo inicial uma vez, sem repor itens depois de edições."""
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise ValueError(f"Usuário não encontrado: {user_id}")
        initialized = initialize_user_reference_data(database, user)
        database.commit()
        return initialized


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, type=UUID, help="UUID da conta que receberá o catálogo")
    arguments = parser.parse_args()
    changed = seed_initial_data(arguments.user_id)
    print("Catálogo inicial criado." if changed else "Catálogo já inicializado; nenhuma alteração feita.")
