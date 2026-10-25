"""Use case for the one-time initialization of an account's reference data."""

from uuid import UUID

from app.shared.transactions import UnitOfWork, atomic


class ReferenceDataService:
    def __init__(self, repository, unit_of_work: UnitOfWork) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def initialize_for_user(self, user_id: UUID) -> bool:
        with atomic(self._unit_of_work):
            return self._repository.initialize_for_user(user_id)
