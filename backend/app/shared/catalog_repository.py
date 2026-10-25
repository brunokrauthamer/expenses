"""SQLAlchemy persistence adapter for the user's reference catalogs."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.shared.exceptions import DuplicateResourceError


@dataclass(frozen=True)
class CatalogRecord:
    id: int
    name: str
    deleted_at: datetime | None
    requires_expense_category: bool | None = None


class CatalogRepository:
    """Catalog queries and persistence without naming or lifecycle policy."""

    def __init__(self, session: Session, model: type[Any]) -> None:
        self._session = session
        self._model = model

    def list(self, user_id: UUID, include_deleted: bool = False) -> list[CatalogRecord]:
        statement = select(self._model).where(self._model.user_id == user_id)
        if not include_deleted:
            statement = statement.where(self._model.deleted_at.is_(None))
        rows = self._session.scalars(
            statement.order_by(func.lower(func.trim(self._model.name)), self._model.id)
        )
        return [self._record(row) for row in rows]

    def get(self, item_id: int, user_id: UUID) -> CatalogRecord | None:
        item = self._session.scalar(
            select(self._model).where(
                self._model.id == item_id,
                self._model.user_id == user_id,
            )
        )
        return self._record(item) if item is not None else None

    def name_exists(self, user_id: UUID, name: str, *, exclude_id: int | None = None) -> bool:
        statement = select(self._model.id).where(
            self._model.user_id == user_id,
            self._model.deleted_at.is_(None),
            func.lower(func.trim(self._model.name)) == name.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(self._model.id != exclude_id)
        return self._session.scalar(statement.limit(1)) is not None

    def create(self, user_id: UUID, name: str, **attributes: Any) -> CatalogRecord:
        item = self._model(user_id=user_id, name=name, **attributes)
        self._session.add(item)
        self._flush()
        return self._record(item)

    def update(
        self, item_id: int, user_id: UUID, name: str, **attributes: Any
    ) -> CatalogRecord | None:
        item = self._session.scalar(
            select(self._model).where(
                self._model.id == item_id,
                self._model.user_id == user_id,
            )
        )
        if item is None:
            return None
        item.name = name
        for key, value in attributes.items():
            setattr(item, key, value)
        self._flush()
        return self._record(item)

    def soft_delete(self, item_id: int, user_id: UUID) -> CatalogRecord | None:
        item = self._session.scalar(
            select(self._model).where(
                self._model.id == item_id,
                self._model.user_id == user_id,
            )
        )
        if item is None:
            return None
        if item.deleted_at is None:
            item.deleted_at = datetime.now(timezone.utc)
            self._flush()
        return self._record(item)

    def _flush(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as error:
            message = str(error).lower()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", "") or ""
            if "active_name" in constraint or "unique" in message or "duplicate key" in message:
                raise DuplicateResourceError(
                    "Já existe um cadastro ativo com este nome."
                ) from error
            raise

    @staticmethod
    def _record(item: Any) -> CatalogRecord:
        return CatalogRecord(
            id=item.id,
            name=item.name,
            deleted_at=item.deleted_at,
            requires_expense_category=getattr(item, "requires_expense_category", None),
        )
