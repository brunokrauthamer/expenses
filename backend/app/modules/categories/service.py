from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.categories.model import Category


def list_categories(database: Session) -> list[Category]:
    """Retorna as categorias em ordem alfabética para uso nos clientes."""
    statement = select(Category).order_by(Category.name)
    return list(database.scalars(statement))
