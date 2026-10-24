from sqlalchemy import select
from uuid import UUID

import base64
import pytest
from fastapi import HTTPException

from app.modules.auth.model import ExternalIdentity, LocalCredential, RefreshSession, User
from app.modules.auth.service import _new_user, google_login
from app.modules.categories.model import Category
from app.modules.income_entries.model import IncomeCategory
from app.modules.payment_methods.model import PaymentMethod
from app.shared.reference_data import CATEGORIES, INCOME_CATEGORIES, PAYMENT_METHODS
from app.shared.reference_data import initialize_user_reference_data
from app.shared.crypto import decrypt_personal_data, encrypt_personal_data


def test_register_stores_personal_data_encrypted_and_returns_bearer_cookie(auth_client, database):
    response = auth_client.post(
        "/auth/register",
        json={"email": "Pessoa@Example.com", "password": "senha-segura-com-12"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "pessoa@example.com"
    assert "expenses_refresh=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]

    user = database.scalar(select(User))
    credential = database.scalar(select(LocalCredential))
    assert user.email_ciphertext != b"pessoa@example.com"
    assert b"pessoa@example.com" not in user.email_ciphertext
    assert credential.password_hash != "senha-segura-com-12"
    assert credential.password_hash.startswith("$argon2id$")
    assert user.reference_data_initialized_at is not None
    assert database.query(Category).filter_by(user_id=user.id).count() == len(CATEGORIES)
    assert database.query(PaymentMethod).filter_by(user_id=user.id).count() == len(PAYMENT_METHODS)
    assert database.query(IncomeCategory).filter_by(user_id=user.id).count() == len(INCOME_CATEGORIES)


def test_new_google_account_initializes_catalog_once_and_existing_link_does_not_duplicate(database):
    user, *_ = google_login(database, "google-subject", "person@gmail.com", "Person")
    initial_counts = (
        database.query(Category).filter_by(user_id=user.id).count(),
        database.query(PaymentMethod).filter_by(user_id=user.id).count(),
        database.query(IncomeCategory).filter_by(user_id=user.id).count(),
    )
    same_user, *_ = google_login(database, "google-subject", "person@gmail.com", "Person")
    assert same_user.id == user.id
    assert initial_counts == (len(CATEGORIES), len(PAYMENT_METHODS), len(INCOME_CATEGORIES))
    assert (
        database.query(Category).filter_by(user_id=user.id).count(),
        database.query(PaymentMethod).filter_by(user_id=user.id).count(),
        database.query(IncomeCategory).filter_by(user_id=user.id).count(),
    ) == initial_counts


def test_google_links_existing_gmail_user_without_recreating_catalogs(database):
    user = _new_user(database, "person@gmail.com")
    database.commit()
    initial_counts = (
        database.query(Category).filter_by(user_id=user.id).count(),
        database.query(PaymentMethod).filter_by(user_id=user.id).count(),
        database.query(IncomeCategory).filter_by(user_id=user.id).count(),
    )

    linked_user, *_ = google_login(database, "linked-google-subject", "person@gmail.com", "Person")

    assert linked_user.id == user.id
    assert initial_counts == (len(CATEGORIES), len(PAYMENT_METHODS), len(INCOME_CATEGORIES))
    assert (
        database.query(Category).filter_by(user_id=user.id).count(),
        database.query(PaymentMethod).filter_by(user_id=user.id).count(),
        database.query(IncomeCategory).filter_by(user_id=user.id).count(),
    ) == initial_counts
    assert database.query(ExternalIdentity).filter_by(user_id=user.id, provider="google").count() == 1


def test_google_link_requires_matching_verified_host_for_existing_non_gmail_user(database):
    user = _new_user(database, "person@example.com")
    database.commit()
    initial_counts = database.query(Category).filter_by(user_id=user.id).count()

    with pytest.raises(HTTPException) as failure:
        google_login(database, "company-google-subject", "person@example.com", "Person")
    assert failure.value.status_code == 409

    linked_user, *_ = google_login(
        database, "company-google-subject", "person@example.com", "Person", hosted_domain="example.com",
    )
    assert linked_user.id == user.id
    assert database.query(Category).filter_by(user_id=user.id).count() == initial_counts
    assert database.query(ExternalIdentity).filter_by(user_id=user.id, provider="google").count() == 1


def test_catalog_initialization_rolls_back_with_new_user(database):
    user = _new_user(database, "rollback@example.com")
    database.flush()
    assert database.query(Category).filter_by(user_id=user.id).count() == len(CATEGORIES)
    database.rollback()
    assert database.scalar(select(User.id).where(User.id == user.id)) is None
    assert database.query(Category).filter_by(user_id=user.id).count() == 0


def test_catalog_initialization_does_not_restore_renamed_or_deleted_defaults(database):
    user = _new_user(database, "customized@example.com")
    database.commit()
    category = database.scalar(select(Category).where(Category.user_id == user.id, Category.name == CATEGORIES[0]))
    deleted_method = database.scalar(select(PaymentMethod).where(PaymentMethod.user_id == user.id))
    deleted_income = database.scalar(select(IncomeCategory).where(IncomeCategory.user_id == user.id))
    category.name = "Compras personalizadas"
    deleted_method.deleted_at = user.reference_data_initialized_at
    deleted_income.deleted_at = user.reference_data_initialized_at
    database.commit()

    assert initialize_user_reference_data(database, user) is False
    database.commit()
    assert database.query(Category).filter_by(user_id=user.id).count() == len(CATEGORIES)
    assert database.scalar(select(Category.name).where(Category.id == category.id)) == "Compras personalizadas"
    assert database.scalar(select(Category.id).where(Category.user_id == user.id, Category.name == CATEGORIES[0])) is None
    assert database.query(PaymentMethod).filter_by(user_id=user.id).count() == len(PAYMENT_METHODS)
    assert database.scalar(select(PaymentMethod.deleted_at).where(PaymentMethod.id == deleted_method.id)) is not None
    assert database.query(IncomeCategory).filter_by(user_id=user.id).count() == len(INCOME_CATEGORIES)
    assert database.scalar(select(IncomeCategory.deleted_at).where(IncomeCategory.id == deleted_income.id)) is not None


def test_business_routes_require_a_valid_bearer(auth_client):
    assert auth_client.get("/categories").status_code == 401
    response = auth_client.post(
        "/auth/register",
        json={"email": "pessoa@example.com", "password": "senha-segura-com-12"},
    )
    token = response.json()["access_token"]

    assert auth_client.get("/categories", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert auth_client.get("/categories", headers={"Authorization": "Basic invalid"}).status_code == 401
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert auth_client.get("/categories", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_invalid_login_has_same_message_for_unknown_user_and_wrong_password(auth_client):
    register = auth_client.post(
        "/auth/register",
        json={"email": "pessoa@example.com", "password": "senha-segura-com-12"},
    )
    assert register.status_code == 201

    unknown = auth_client.post(
        "/auth/login",
        json={"email": "ausente@example.com", "password": "senha-segura-com-12"},
    )
    wrong = auth_client.post(
        "/auth/login",
        json={"email": "pessoa@example.com", "password": "outra-senha-segura"},
    )
    short_wrong = auth_client.post(
        "/auth/login",
        json={"email": "pessoa@example.com", "password": "curta"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    assert short_wrong.status_code == 401
    assert short_wrong.json()["detail"] == unknown.json()["detail"]


def test_refresh_rotates_token_and_rejects_reuse(auth_client, database):
    register = auth_client.post(
        "/auth/register",
        json={"email": "pessoa@example.com", "password": "senha-segura-com-12"},
    )
    old_token = auth_client.cookies.get("expenses_refresh")
    assert old_token

    refreshed = auth_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != register.json()["access_token"]
    new_token = auth_client.cookies.get("expenses_refresh")
    assert new_token != old_token

    auth_client.cookies.set("expenses_refresh", old_token, path="/auth")
    reused = auth_client.post("/auth/refresh")
    assert reused.status_code == 401
    assert database.scalar(select(RefreshSession).where(RefreshSession.token_hash.is_not(None))) is not None


def test_google_login_is_not_advertised_as_configured_without_credentials(auth_client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    assert auth_client.get("/auth/google/status").json() == {"enabled": False}
    response = auth_client.get("/auth/google/start")
    assert response.status_code == 503


def test_google_login_status_requires_all_credentials(auth_client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://app.example/auth/google/callback")
    assert auth_client.get("/auth/google/status").json() == {"enabled": True}


def test_refresh_and_logout_do_not_return_refresh_token_in_json(auth_client):
    auth_client.post(
        "/auth/register",
        json={"email": "pessoa@example.com", "password": "senha-segura-com-12"},
    )
    refreshed = auth_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert "expenses_refresh" not in refreshed.text
    assert auth_client.post("/auth/logout").status_code == 204
    assert auth_client.post("/auth/refresh").status_code == 401


def test_distinct_authenticated_users_are_isolated(auth_client, database):
    first = auth_client.post(
        "/auth/register",
        json={"email": "primeira@example.com", "password": "senha-segura-com-12"},
    ).json()
    first_user_id = UUID(first["user"]["id"])
    category = Category(name="Casa", user_id=first_user_id)
    payment_method = PaymentMethod(name="Cartão", user_id=first_user_id)
    database.add_all([category, payment_method])
    database.commit()

    created = auth_client.post(
        "/expenses",
        headers={"Authorization": f"Bearer {first['access_token']}"},
        json={
            "description": "Compra compartilhada",
            "amount": "25.00",
            "expense_date": "2026-10-20",
            "category_id": category.id,
            "payment_method_id": payment_method.id,
        },
    )
    assert created.status_code == 201

    second = auth_client.post(
        "/auth/register",
        json={"email": "segunda@example.com", "password": "senha-segura-com-12"},
    ).json()
    visible = auth_client.get(
        "/expenses/month?month=2026-10",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert visible.status_code == 200
    assert visible.json() == []
    second_categories = auth_client.get("/categories", headers={"Authorization": f"Bearer {second['access_token']}"}).json()
    assert second_categories and "Casa" not in {item["name"] for item in second_categories}


def test_personal_data_ciphertext_keeps_readable_key_version(monkeypatch):
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY_VERSION", "2")
    monkeypatch.setenv(
        "AUTH_ENCRYPTION_KEY_V2",
        base64.b64encode(b"second-version-encryption-key-32").decode(),
    )
    original = encrypt_personal_data("perfil confidencial")
    assert original[0] == 2
    assert decrypt_personal_data(original) == "perfil confidencial"
