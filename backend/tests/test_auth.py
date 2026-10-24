import base64
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from sqlalchemy import select

from app.modules.auth.model import ExternalIdentity, RefreshSession, User
from app.modules.auth.service import google_login, read_oauth_state_cookie
from app.modules.categories.model import Category
from app.modules.payment_methods.model import PaymentMethod
from app.shared.crypto import decrypt_personal_data, encrypt_personal_data


def test_password_authentication_endpoints_are_removed(auth_client):
    payload = {"email": "pessoa@gmail.com", "password": "senha-segura-com-12"}
    assert auth_client.post("/auth/register", json=payload).status_code == 404
    assert auth_client.post("/auth/login", json=payload).status_code == 404


def test_business_routes_require_a_valid_bearer(auth_client, google_session):
    assert auth_client.get("/categories").status_code == 401
    session = google_session(auth_client)

    assert auth_client.get("/categories", headers={"Authorization": f"Bearer {session['access_token']}"}).status_code == 200
    assert auth_client.get("/categories", headers={"Authorization": "Basic invalid"}).status_code == 401
    tampered = session["access_token"][:-1] + ("a" if session["access_token"][-1] != "a" else "b")
    assert auth_client.get("/categories", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_google_login_status_requires_all_credentials(auth_client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    assert auth_client.get("/auth/google/status").json() == {"enabled": False}
    assert auth_client.get("/auth/google/start", follow_redirects=False).status_code == 503

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    assert auth_client.get("/auth/google/status").json() == {"enabled": True}


def test_google_start_uses_pkce_and_preserves_only_an_internal_destination(auth_client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    request_id = "x" * 32
    response = auth_client.get(
        "/auth/google/start",
        params={"request_id": request_id, "next": "/consolidado?start_month=2026-01"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    authorization = parse_qs(urlparse(response.headers["location"]).query)
    assert urlparse(response.headers["location"]).netloc == "accounts.google.com"
    assert authorization["scope"] == ["openid email profile"]
    assert authorization["code_challenge_method"] == ["S256"]
    cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith("expenses_google_oauth="))
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/auth/google" in cookie
    protected_state = read_oauth_state_cookie(auth_client.cookies.get("expenses_google_oauth", path="/auth/google"))
    assert protected_state["request_id"] == request_id
    assert protected_state["next"] == "/consolidado?start_month=2026-01"
    forged = auth_client.get(
        "/auth/google/start",
        params={"request_id": request_id, "next": "https://attacker.example"},
        follow_redirects=False,
    )
    assert forged.status_code == 302
    protected_state = read_oauth_state_cookie(auth_client.cookies.get("expenses_google_oauth", path="/auth/google"))
    assert protected_state["next"] == "/despesas"


@pytest.mark.parametrize("valid_nonce", [True, False])
def test_google_callback_validates_nonce_and_creates_encrypted_identity(auth_client, database, monkeypatch, valid_nonce):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import app.modules.auth.controller as controller

    client_id = "client-id.apps.googleusercontent.com"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", client_id)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    monkeypatch.setenv("AUTH_FRONTEND_URL", "http://localhost:5173")
    started = auth_client.get(
        "/auth/google/start",
        params={"request_id": "y" * 32, "next": "/gastos?month=2026-10"},
        follow_redirects=False,
    )
    authorization = parse_qs(urlparse(started.headers["location"]).query)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    signing_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    id_token = jwt.encode({
        "sub": "stable-google-subject",
        "email": "pessoa@gmail.com",
        "email_verified": True,
        "name": "Pessoa de Teste",
        "iss": "https://accounts.google.com",
        "aud": client_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "nonce": authorization["nonce"][0] if valid_nonce else "incorrect-nonce",
    }, signing_pem, algorithm="RS256")

    class FakeTokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id_token": id_token}

    captured = {}

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, data):
            captured["data"] = data
            return FakeTokenResponse()

    class FakeJWKClient:
        def __init__(self, _url):
            pass

        def get_signing_key_from_jwt(self, _token):
            return type("SigningKey", (), {"key": public_key})()

    monkeypatch.setattr(controller.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(controller, "PyJWKClient", FakeJWKClient)
    response = auth_client.get(
        "/auth/google/callback",
        params={"code": "authorization-code", "state": authorization["state"][0]},
        follow_redirects=False,
    )

    assert response.status_code == 303
    completion = urlparse(response.headers["location"])
    assert completion.netloc == "localhost:5173" and completion.path == "/auth/complete"
    if not valid_nonce:
        assert parse_qs(completion.query)["reason"] == ["failed"]
        assert database.scalar(select(User)) is None
        return
    assert parse_qs(completion.query) == {"result": ["success"], "request_id": ["y" * 32]}
    cookies = response.headers.get_list("set-cookie")
    assert any(value.startswith("expenses_refresh=") and "HttpOnly" in value for value in cookies)
    assert any(value.startswith("expenses_google_oauth=") and "Max-Age=0" in value for value in cookies)
    assert "access_token" not in response.headers["location"]
    assert hashlib.sha256(captured["data"]["code_verifier"].encode()).digest()
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(captured["data"]["code_verifier"].encode()).digest()
    ).rstrip(b"=").decode()
    assert expected_challenge == authorization["code_challenge"][0]

    user = database.scalar(select(User))
    identity = database.scalar(select(ExternalIdentity))
    assert decrypt_personal_data(user.email_ciphertext) == "pessoa@gmail.com"
    assert user.email_lookup != "pessoa@gmail.com"
    assert identity.provider == "google"
    assert decrypt_personal_data(identity.subject_ciphertext) == "stable-google-subject"
    assert database.scalar(select(RefreshSession)) is not None


def test_google_callback_requires_matching_state_and_handles_cancellation(auth_client, database, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    first = auth_client.get("/auth/google/start", params={"request_id": "a" * 32}, follow_redirects=False)
    first_state = parse_qs(urlparse(first.headers["location"]).query)["state"][0]
    invalid = auth_client.get(
        "/auth/google/callback",
        params={"code": "unused", "state": f"{first_state}-tampered"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(invalid.headers["location"]).query)["reason"] == ["expired"]
    assert database.scalar(select(User)) is None

    second = auth_client.get("/auth/google/start", params={"request_id": "b" * 32}, follow_redirects=False)
    second_state = parse_qs(urlparse(second.headers["location"]).query)["state"][0]
    cancelled = auth_client.get(
        "/auth/google/callback",
        params={"error": "access_denied", "state": second_state},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(cancelled.headers["location"]).query) == {
        "result": ["error"], "request_id": ["b" * 32], "reason": ["cancelled"],
    }
    assert database.scalar(select(User)) is None


@pytest.mark.parametrize("cookie,stage", [(None, "cookie_missing"), ("invalid-cookie-secret", "cookie_invalid")])
def test_google_callback_logs_state_failure_without_credentials(auth_client, caplog, cookie, stage):
    if cookie:
        auth_client.cookies.set("expenses_google_oauth", cookie, path="/auth/google")
    response = auth_client.get(
        "/auth/google/callback",
        params={"code": "private-authorization-code", "state": "private-oauth-state"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(response.headers["location"]).query) == {
        "result": ["error"], "reason": ["expired"],
    }
    assert f"stage={stage}" in caplog.text
    for private_value in ("private-authorization-code", "private-oauth-state", "invalid-cookie-secret"):
        assert private_value not in caplog.text


def test_google_callback_logs_token_network_failure_safely(auth_client, database, monkeypatch, caplog):
    import httpx
    import app.modules.auth.controller as controller

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "private-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
    started = auth_client.get("/auth/google/start", params={"request_id": "n" * 32}, follow_redirects=False)
    authorization = parse_qs(urlparse(started.headers["location"]).query)

    async def fail_post(*_args, **_kwargs):
        raise httpx.ConnectError("Network failure containing private-authorization-code and private-client-secret")

    monkeypatch.setattr(controller.httpx.AsyncClient, "post", fail_post)
    response = auth_client.get(
        "/auth/google/callback",
        params={"code": "private-authorization-code", "state": authorization["state"][0]},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(response.headers["location"]).query) == {
        "result": ["error"], "request_id": ["n" * 32], "reason": ["failed"],
    }
    assert "stage=token_exchange" in caplog.text
    assert "ConnectError" in caplog.text
    assert "private-authorization-code" not in caplog.text
    assert "private-client-secret" not in caplog.text
    assert database.scalar(select(User)) is None


def test_google_login_reuses_identity_and_rejects_unverified_email_collision(database, monkeypatch):
    monkeypatch.setenv("AUTH_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    from app.modules.auth.service import _new_user

    legacy = _new_user(database, "person@custom.example", "Pessoa")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as conflict:
        google_login(database, "subject-one", "person@custom.example", "Pessoa")
    assert conflict.value.status_code == 409
    assert database.scalar(select(ExternalIdentity)) is None

    account = google_login(
        database,
        "subject-one",
        "person@custom.example",
        "Pessoa",
        hosted_domain="custom.example",
    )
    identity = database.scalar(select(ExternalIdentity))
    assert account[0].id == legacy.id == identity.user_id

    again = google_login(
        database,
        "subject-one",
        "person@custom.example",
        "Pessoa",
        hosted_domain="custom.example",
    )
    assert again[0].id == legacy.id
    assert len(database.scalars(select(ExternalIdentity)).all()) == 1


def test_refresh_rotates_token_and_rejects_reuse(auth_client, database, google_session):
    initial = google_session(auth_client)
    old_token = auth_client.cookies.get("expenses_refresh")
    assert old_token

    refreshed = auth_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != initial["access_token"]
    new_token = refreshed.cookies.get("expenses_refresh")
    assert new_token != old_token

    auth_client.cookies.clear()
    auth_client.cookies.set("expenses_refresh", old_token, path="/auth")
    reused = auth_client.post("/auth/refresh")
    assert reused.status_code == 401
    assert database.scalar(select(RefreshSession).where(RefreshSession.token_hash.is_not(None))) is not None


def test_refresh_and_logout_do_not_return_refresh_token_in_json(auth_client, google_session):
    google_session(auth_client)
    refreshed = auth_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert "expenses_refresh" not in refreshed.text
    assert auth_client.post("/auth/logout").status_code == 204
    assert auth_client.post("/auth/refresh").status_code == 401


def test_distinct_google_accounts_share_business_records(auth_client, database, google_session):
    category = Category(name="Casa")
    payment_method = PaymentMethod(name="Cartão")
    database.add_all([category, payment_method])
    database.commit()

    first = google_session(auth_client, "primeira@gmail.com")
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

    second = google_session(auth_client, "segunda@gmail.com")
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
