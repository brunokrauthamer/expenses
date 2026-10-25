from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_database_url


class Base(DeclarativeBase):
    """Base compartilhada pelos modelos SQLAlchemy."""


@lru_cache(maxsize=1)
def _session_factory():
    """Create the database engine only when the application opens a session."""
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def SessionLocal() -> Session:
    """Return a session from the lazily initialized production engine."""
    return _session_factory()()


def get_db() -> Generator[Session, None, None]:
    """Disponibiliza uma sessão de banco e a fecha ao fim da requisição."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
