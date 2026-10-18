import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test_database"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.modules.registry  # noqa: F401
from app.database import Base
from app.main import app
from app.shared.dependencies import get_db


@pytest.fixture
def database() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(database: Session) -> TestClient:
    def get_test_database():
        yield database

    app.dependency_overrides[get_db] = get_test_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
