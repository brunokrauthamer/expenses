from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError


def list_catalog(database: Session, model, user_id: UUID, include_deleted: bool = False):
    statement = select(model).where(model.user_id == user_id)
    if not include_deleted:
        statement = statement.where(model.deleted_at.is_(None))
    return list(database.scalars(statement.order_by(func.lower(func.trim(model.name)), model.id)))


def create_catalog_item(database: Session, model, user_id: UUID, name: str, **attributes):
    normalized_name = _validate_name(name)
    _ensure_name_available(database, model, user_id, normalized_name)
    item = model(user_id=user_id, name=normalized_name, **attributes)
    database.add(item)
    _commit(database)
    database.refresh(item)
    return item


def update_catalog_item(database: Session, model, item_id: int, user_id: UUID, name: str, **attributes):
    item = _owned_item(database, model, item_id, user_id)
    if item.deleted_at is not None:
        raise ValueError("Este cadastro foi excluído e não pode ser alterado.")

    normalized_name = _validate_name(name)
    _ensure_name_available(database, model, user_id, normalized_name, exclude_id=item.id)
    if model is IncomeCategory and "requires_expense_category" in attributes:
        if attributes["requires_expense_category"] != item.requires_expense_category:
            used = database.scalar(select(IncomeEntry.id).where(IncomeEntry.income_category_id == item.id, IncomeEntry.user_id == user_id).limit(1))
            if used is not None:
                raise ValueError("A regra de reembolso não pode mudar depois do primeiro lançamento.")
    item.name = normalized_name
    for key, value in attributes.items():
        setattr(item, key, value)
    _commit(database)
    database.refresh(item)
    return item


def delete_catalog_item(database: Session, model, item_id: int, user_id: UUID) -> None:
    item = _owned_item(database, model, item_id, user_id)
    if item.deleted_at is None:
        item.deleted_at = datetime.now(timezone.utc)
        _commit(database)


def owned_catalog_item(database: Session, model, item_id: int, user_id: UUID):
    return _owned_item(database, model, item_id, user_id)


def _owned_item(database: Session, model, item_id: int, user_id: UUID):
    item = database.scalar(select(model).where(model.id == item_id, model.user_id == user_id))
    if item is None:
        raise ResourceNotFoundError("Cadastro não encontrado.")
    return item


def _validate_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise ValueError("O nome não pode ficar vazio.")
    if len(value) > 50:
        raise ValueError("O nome pode ter no máximo 50 caracteres.")
    return value


def _ensure_name_available(database: Session, model, user_id: UUID, name: str, exclude_id: int | None = None) -> None:
    statement = select(model.id).where(
        model.user_id == user_id,
        model.deleted_at.is_(None),
        func.lower(func.trim(model.name)) == name.lower(),
    )
    if exclude_id is not None:
        statement = statement.where(model.id != exclude_id)
    if database.scalar(statement.limit(1)) is not None:
        raise DuplicateResourceError("Já existe um cadastro ativo com este nome.")


def _commit(database: Session) -> None:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        message = str(error).lower()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", "") or ""
        if "active_name" in constraint or "unique" in message or "duplicate key" in message:
            raise DuplicateResourceError("Já existe um cadastro ativo com este nome.") from error
        raise
