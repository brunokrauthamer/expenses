import os
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test_database"
)
os.environ.setdefault("AUTH_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("AUTH_LOOKUP_KEY", "YWJjZGVmMDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODk=")
os.environ.setdefault("AUTH_TOKEN_SECRET", "dGhpcy1pcy1vbmx5LWEtZmFrZS10ZXN0LWtleS0zMiE=")
_test_jwt_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ.setdefault(
    "AUTH_JWT_PRIVATE_KEY_B64",
    base64.b64encode(_test_jwt_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )).decode(),
)
os.environ.setdefault(
    "AUTH_JWT_PUBLIC_KEY_B64",
    base64.b64encode(_test_jwt_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )).decode(),
)
os.environ.setdefault("AUTH_COOKIE_PATH", "/auth")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.modules.registry  # noqa: F401
from app.database import Base
from app.main import app
from app.modules.auth.service import google_login
from app.shared.dependencies import get_db
from app.shared.auth import get_current_user
from app.modules.auth.model import User
from uuid import uuid4


@pytest.fixture
def database() -> Session:
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
    app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid4(), email_ciphertext=b"test", email_lookup="test-user"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(database: Session) -> TestClient:
    def get_test_database():
        yield database

    app.dependency_overrides[get_db] = get_test_database
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def google_session(database: Session):
    def create(client: TestClient, email: str = "pessoa@gmail.com", subject: str | None = None):
        account = google_login(
            database,
            subject or f"google-subject-{email}",
            email,
            "Pessoa de Teste",
        )
        user, access_token, refresh_token, expires_in = account
        client.cookies.set("expenses_refresh", refresh_token, path="/auth")
        return {
            "access_token": access_token,
            "expires_in": expires_in,
            "user": {"id": str(user.id), "email": email, "name": "Pessoa de Teste"},
        }

    return create
