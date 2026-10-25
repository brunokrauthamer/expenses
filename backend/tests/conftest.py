from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify the existing API/database suite separately from pure unit tests."""
    for item in items:
        if "tests/unit/" not in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def auth_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use synthetic authentication keys only in tests that exercise auth."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    test_jwt_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    monkeypatch.setenv("AUTH_LOOKUP_KEY", "YWJjZGVmMDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODk=")
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "dGhpcy1pcy1vbmx5LWEtZmFrZS10ZXN0LWtleS0zMiE=")
    monkeypatch.setenv(
        "AUTH_JWT_PRIVATE_KEY_B64",
        base64.b64encode(
            test_jwt_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode(),
    )
    monkeypatch.setenv(
        "AUTH_JWT_PUBLIC_KEY_B64",
        base64.b64encode(
            test_jwt_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ).decode(),
    )
    monkeypatch.setenv("AUTH_COOKIE_PATH", "/auth")


@pytest.fixture
def database() -> Generator:
    """Create a disposable SQLite database for API and persistence integration tests."""
    import app.modules.registry  # noqa: F401
    from app.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(database, auth_environment):
    import app.modules.registry  # noqa: F401
    from app.main import app
    from app.modules.auth.dependencies import get_current_user
    from app.modules.auth.model import User
    from app.shared.dependencies import get_db
    from fastapi.testclient import TestClient

    user = User(id=uuid4(), email_ciphertext=b"test", email_lookup="test-user")
    database.add(user)
    database.commit()
    database.info["test_user_id"] = user.id

    def get_test_database():
        yield database

    app.dependency_overrides[get_db] = get_test_database
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(database, auth_environment):
    import app.modules.registry  # noqa: F401
    from app.main import app
    from app.modules.auth.dependencies import get_current_user
    from app.shared.dependencies import get_db
    from fastapi.testclient import TestClient

    def get_test_database():
        yield database

    app.dependency_overrides[get_db] = get_test_database
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
