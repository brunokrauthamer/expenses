"""Inicializa o catálogo de referência de uma conta específica."""

import argparse
from uuid import UUID

import app.modules.registry  # noqa: F401 - registra todos os modelos e relações.
from app.database import SessionLocal
from app.shared.reference_data import ReferenceDataRepository
from app.shared.reference_data_service import ReferenceDataService
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork


def seed_initial_data(user_id: UUID) -> bool:
    """Insere o catálogo inicial uma vez, sem repor itens depois de edições."""
    with SessionLocal() as database:
        service = ReferenceDataService(
            ReferenceDataRepository(database),
            SqlAlchemyUnitOfWork(database),
        )
        return service.initialize_for_user(user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", required=True, type=UUID, help="UUID da conta que receberá o catálogo"
    )
    arguments = parser.parse_args()
    changed = seed_initial_data(arguments.user_id)
    print(
        "Catálogo inicial criado."
        if changed
        else "Catálogo já inicializado; nenhuma alteração feita."
    )
