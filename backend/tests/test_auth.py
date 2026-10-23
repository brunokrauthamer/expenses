from sqlalchemy import select

import base64

from app.modules.auth.model import LocalCredential, RefreshSession, User
from app.modules.categories.model import Category
from app.modules.payment_methods.model import PaymentMethod
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


def test_distinct_authenticated_users_share_business_records(auth_client, database):
    category = Category(name="Casa")
    payment_method = PaymentMethod(name="Cartão")
    database.add_all([category, payment_method])
    database.commit()

    first = auth_client.post(
        "/auth/register",
        json={"email": "primeira@example.com", "password": "senha-segura-com-12"},
    ).json()
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
    assert [item["description"] for item in visible.json()] == ["Compra compartilhada"]


def test_personal_data_ciphertext_keeps_readable_key_version(monkeypatch):
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY_VERSION", "2")
    monkeypatch.setenv(
        "AUTH_ENCRYPTION_KEY_V2",
        base64.b64encode(b"second-version-encryption-key-32").decode(),
    )
    original = encrypt_personal_data("perfil confidencial")
    assert original[0] == 2
    assert decrypt_personal_data(original) == "perfil confidencial"
