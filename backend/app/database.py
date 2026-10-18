from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_database_url


class Base(DeclarativeBase):
    """Base compartilhada pelos modelos SQLAlchemy."""


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Disponibiliza uma sessão de banco e a fecha ao fim da requisição."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
