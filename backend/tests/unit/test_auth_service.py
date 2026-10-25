from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.modules.auth.contracts import AuthUser, GoogleIdentity, RefreshSessionState
from app.modules.auth.errors import (
    AccountConflictError,
    AccountDisabledError,
    AuthenticationRejectedError,
)
from app.modules.auth.service import AuthService
from app.shared.crypto import encrypt_personal_data, lookup_digest, token_digest

pytestmark = pytest.mark.unit


class FakeUnitOfWork:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakePasswordHasher:
    def __init__(self, *, needs_rehash=False):
        self._needs_rehash = needs_rehash

    def hash(self, password):
        return f"hash:{password}"

    def verify(self, password_hash, password):
        return password_hash == self.hash(password) or (
            password_hash == "old-hash" and password == "correct"
        )

    def check_needs_rehash(self, _password_hash):
        return self._needs_rehash


class FakeAuthRepository:
    def __init__(self):
        self.users_by_email = {}
        self.users_by_id = {}
        self.password_hashes = {}
        self.refresh_sessions = {}
        self.google_users = {}
        self.created_google_identities = []

    def add_user(self, user, email, password_hash=None):
        self.users_by_email[lookup_digest(email)] = user
        self.users_by_id[user.id] = user
        if password_hash is not None:
            self.password_hashes[user.id] = password_hash

    def find_user_by_email(self, email_lookup):
        return self.users_by_email.get(email_lookup)

    def create_user(self, **attributes):
        user = AuthUser(
            id=uuid4(),
            email_ciphertext=attributes["email_ciphertext"],
            name_ciphertext=attributes["name_ciphertext"],
            is_active=True,
        )
        self.users_by_email[attributes["email_lookup"]] = user
        self.users_by_id[user.id] = user
        return user

    def save_password_hash(self, user_id, password_hash):
        self.password_hashes[user_id] = password_hash

    def password_hash(self, user_id):
        return self.password_hashes.get(user_id)

    def create_refresh_session(self, user_id, family_id, refresh_hash, expires_at):
        session = RefreshSessionState(
            id=uuid4(),
            user_id=user_id,
            family_id=family_id,
            expires_at=expires_at,
            revoked_at=None,
            user=self.users_by_id[user_id],
        )
        self.refresh_sessions[refresh_hash] = session
        return session

    def find_refresh_session(self, refresh_hash):
        return self.refresh_sessions.get(refresh_hash)

    def replace_refresh_session(self, session_id, *, now, replacement_id):
        for refresh_hash, session in self.refresh_sessions.items():
            if session.id == session_id:
                self.refresh_sessions[refresh_hash] = replace(session, revoked_at=now)
                self.replacement = (session_id, replacement_id)
                return

    def revoke_refresh_session(self, session_id, revoked_at):
        for refresh_hash, session in self.refresh_sessions.items():
            if session.id == session_id:
                self.refresh_sessions[refresh_hash] = replace(session, revoked_at=revoked_at)
                return

    def revoke_refresh_family(self, family_id, revoked_at):
        self.revoked_family = (family_id, revoked_at)

    def find_user(self, user_id):
        return self.users_by_id.get(user_id)

    def find_google_identity(self, subject_hash):
        return self.google_users.get(subject_hash)

    def create_google_identity(self, user_id, _subject_ciphertext, subject_hash):
        user = self.users_by_id[user_id]
        self.google_users[subject_hash] = user
        self.created_google_identities.append((user_id, subject_hash))


def make_user(email, *, is_active=True):
    return AuthUser(
        id=uuid4(),
        email_ciphertext=encrypt_personal_data(email),
        name_ciphertext=None,
        is_active=is_active,
    )


def configure_auth(monkeypatch, *, needs_rehash=False):
    from app.modules.auth import service as auth_service_module

    monkeypatch.setattr(
        auth_service_module,
        "_PASSWORD_HASHER",
        FakePasswordHasher(needs_rehash=needs_rehash),
    )
    monkeypatch.setattr(
        auth_service_module, "create_access_token", lambda _user_id: ("access", 900)
    )


def test_register_normalizes_email_and_commits_user_password_and_refresh_session(
    auth_environment, monkeypatch
):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    unit = FakeUnitOfWork()

    result = AuthService(repository, unit).register("  Person@Example.com ", "long-password")

    assert result.user["email"] == "person@example.com"
    assert result.access_token == "access"
    assert result.expires_in == 900
    assert repository.password_hashes[result.user["id"]] == "hash:long-password"
    assert len(repository.refresh_sessions) == 1
    assert (unit.commits, unit.rollbacks) == (1, 0)


def test_register_rejects_existing_account_before_opening_transaction(
    auth_environment, monkeypatch
):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    repository.add_user(make_user("person@example.com"), "person@example.com")
    unit = FakeUnitOfWork()

    with pytest.raises(AccountConflictError, match="Já existe uma conta"):
        AuthService(repository, unit).register("person@example.com", "long-password")

    assert (unit.commits, unit.rollbacks) == (0, 0)


def test_login_rehashes_a_valid_password_and_rejects_invalid_password(
    auth_environment, monkeypatch
):
    configure_auth(monkeypatch, needs_rehash=True)
    repository = FakeAuthRepository()
    user = make_user("person@example.com")
    repository.add_user(user, "person@example.com", "old-hash")
    unit = FakeUnitOfWork()
    service = AuthService(repository, unit)

    result = service.login(" PERSON@example.com ", "correct")

    assert result.user["id"] == user.id
    assert repository.password_hashes[user.id] == "hash:correct"
    assert unit.commits == 1
    with pytest.raises(AuthenticationRejectedError) as rejected:
        service.login("person@example.com", "incorrect")
    assert rejected.value.challenge is True
    assert unit.commits == 1


def test_refresh_rotates_token_in_the_same_family(auth_environment, monkeypatch):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    user = make_user("person@example.com")
    repository.add_user(user, "person@example.com")
    family_id = uuid4()
    old_token = "old-refresh-token"
    repository.refresh_sessions[token_digest(old_token)] = RefreshSessionState(
        id=uuid4(),
        user_id=user.id,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=None,
        user=user,
    )
    old_session_id = repository.refresh_sessions[token_digest(old_token)].id
    unit = FakeUnitOfWork()

    result = AuthService(repository, unit).refresh(old_token)

    new_session = repository.find_refresh_session(token_digest(result.refresh_token))
    assert new_session.family_id == family_id
    assert repository.refresh_sessions[token_digest(old_token)].revoked_at is not None
    assert repository.replacement == (old_session_id, new_session.id)
    assert unit.commits == 1


def test_refresh_of_expired_session_commits_revocation_before_rejecting(
    auth_environment, monkeypatch
):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    user = make_user("person@example.com")
    repository.add_user(user, "person@example.com")
    token = "expired-refresh-token"
    session = RefreshSessionState(
        id=uuid4(),
        user_id=user.id,
        family_id=uuid4(),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        revoked_at=None,
        user=user,
    )
    repository.refresh_sessions[token_digest(token)] = session
    unit = FakeUnitOfWork()

    with pytest.raises(AuthenticationRejectedError, match="Sessão expirada"):
        AuthService(repository, unit).refresh(token)

    assert repository.refresh_sessions[token_digest(token)].revoked_at is not None
    assert unit.commits == 1


def test_logout_and_current_user_preserve_session_rules(auth_environment, monkeypatch):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    user = make_user("person@example.com")
    repository.add_user(user, "person@example.com")
    token = "active-refresh-token"
    session = RefreshSessionState(
        id=uuid4(),
        user_id=user.id,
        family_id=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=None,
        user=user,
    )
    repository.refresh_sessions[token_digest(token)] = session
    unit = FakeUnitOfWork()
    service = AuthService(repository, unit)

    assert service.current_user(user.id) == {
        "id": user.id,
        "email": "person@example.com",
        "name": None,
    }
    service.logout(token)
    service.logout(None)
    assert repository.refresh_sessions[token_digest(token)].revoked_at is not None
    assert unit.commits == 1

    repository.users_by_id[user.id] = replace(user, is_active=False)
    with pytest.raises(AuthenticationRejectedError, match="Sessão inválida ou expirada"):
        service.current_user(user.id)


def test_google_login_creates_account_and_refuses_unverified_existing_email(
    auth_environment, monkeypatch
):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    unit = FakeUnitOfWork()
    service = AuthService(repository, unit)
    identity = GoogleIdentity("google-subject", "Person@gmail.com", "Person", None)

    result = service.google_login(identity)

    assert result.user["email"] == "person@gmail.com"
    assert len(repository.created_google_identities) == 1
    assert unit.commits == 1

    existing_repository = FakeAuthRepository()
    existing_repository.add_user(make_user("person@example.com"), "person@example.com")
    with pytest.raises(AccountConflictError, match="suporte"):
        AuthService(existing_repository, FakeUnitOfWork()).google_login(
            GoogleIdentity("another-subject", "person@example.com", "Person", None)
        )


def test_google_login_rejects_disabled_account_and_rolls_back(auth_environment, monkeypatch):
    configure_auth(monkeypatch)
    repository = FakeAuthRepository()
    disabled = AuthUser(uuid4(), b"email", None, False)
    repository.google_users[lookup_digest("google-subject", namespace="google")] = disabled
    unit = FakeUnitOfWork()

    with pytest.raises(AccountDisabledError, match="desativada"):
        AuthService(repository, unit).google_login(
            GoogleIdentity("google-subject", "person@gmail.com", "Person", None)
        )

    assert (unit.commits, unit.rollbacks) == (0, 1)
