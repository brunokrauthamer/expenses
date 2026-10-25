"""Application rules for a user's expense categories."""

from uuid import UUID

from app.shared.catalog_repository import CatalogRecord, CatalogRepository
from app.shared.catalog_rules import normalize_catalog_name
from app.shared.exceptions import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.shared.transactions import UnitOfWork, atomic


class CategoryService:
    def __init__(self, repository: CatalogRepository, unit_of_work: UnitOfWork) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def list(self, user_id: UUID, include_deleted: bool = False) -> list[CatalogRecord]:
        return self._repository.list(user_id, include_deleted)

    def create(self, user_id: UUID, name: str) -> CatalogRecord:
        normalized = normalize_catalog_name(name)
        with atomic(self._unit_of_work):
            self._ensure_name_available(user_id, normalized)
            return self._repository.create(user_id, normalized)

    def update(self, item_id: int, user_id: UUID, name: str) -> CatalogRecord:
        current = self._owned_item(item_id, user_id)
        if current.deleted_at is not None:
            raise DomainValidationError("Este cadastro foi excluído e não pode ser alterado.")
        normalized = normalize_catalog_name(name)
        with atomic(self._unit_of_work):
            self._ensure_name_available(user_id, normalized, exclude_id=item_id)
            updated = self._repository.update(item_id, user_id, normalized)
            if updated is None:
                raise ResourceNotFoundError("Cadastro não encontrado.")
            return updated

    def delete(self, item_id: int, user_id: UUID) -> None:
        self._owned_item(item_id, user_id)
        with atomic(self._unit_of_work):
            if self._repository.soft_delete(item_id, user_id) is None:
                raise ResourceNotFoundError("Cadastro não encontrado.")

    def _owned_item(self, item_id: int, user_id: UUID) -> CatalogRecord:
        item = self._repository.get(item_id, user_id)
        if item is None:
            raise ResourceNotFoundError("Cadastro não encontrado.")
        return item

    def _ensure_name_available(
        self, user_id: UUID, name: str, *, exclude_id: int | None = None
    ) -> None:
        if self._repository.name_exists(user_id, name, exclude_id=exclude_id):
            raise DuplicateResourceError("Já existe um cadastro ativo com este nome.")
