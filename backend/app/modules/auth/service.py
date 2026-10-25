"""Authentication use cases without HTTP, ORM or external-provider details."""

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.modules.auth.contracts import AuthResult, AuthUser, GoogleIdentity
from app.modules.auth.errors import (
    AccountConflictError,
    AccountDisabledError,
    AuthenticationRejectedError,
    OAuthAttemptError,
)
from app.modules.auth.repository import AuthRepository
from app.modules.auth.tokens import create_access_token
from app.shared.crypto import (
    decrypt_personal_data,
    encrypt_personal_data,
    lookup_digest,
    token_digest,
)
from app.shared.exceptions import PersistenceConflictError
from app.shared.transactions import UnitOfWork, atomic

_PASSWORD_HASHER = PasswordHasher()
_DUMMY_PASSWORD_HASH = _PASSWORD_HASHER.hash("expenses-invalid-account-check")
_ALLOWED_DESTINATIONS = {
    "/despesas",
    "/gastos",
    "/consolidado",
    "/configuracoes",
}


class AuthService:
    def __init__(self, repository: AuthRepository, unit_of_work: UnitOfWork) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    def register(self, email: str, password: str) -> AuthResult:
        normalized_email = email.strip().casefold()
        email_lookup = lookup_digest(normalized_email)
        if self._repository.find_user_by_email(email_lookup) is not None:
            raise AccountConflictError("Já existe uma conta com este e-mail.")
        try:
            with atomic(self._unit_of_work):
                user = self._create_user(normalized_email)
                self._repository.save_password_hash(user.id, _PASSWORD_HASHER.hash(password))
                result = self._new_session(user)
            return result
        except PersistenceConflictError as error:
            if self._repository.find_user_by_email(email_lookup) is not None:
                raise AccountConflictError("Já existe uma conta com este e-mail.") from error
            raise

    def login(self, email: str, password: str) -> AuthResult:
        user = self._repository.find_user_by_email(lookup_digest(email.strip().casefold()))
        password_hash = self._repository.password_hash(user.id) if user else None
        valid = False
        try:
            valid = _PASSWORD_HASHER.verify(password_hash or _DUMMY_PASSWORD_HASH, password)
        except (VerifyMismatchError, VerificationError):
            valid = False
        if not valid or user is None or not user.is_active:
            raise AuthenticationRejectedError(
                "E-mail ou senha incorretos.",
                challenge=True,
            )

        with atomic(self._unit_of_work):
            if password_hash and _PASSWORD_HASHER.check_needs_rehash(password_hash):
                self._repository.save_password_hash(user.id, _PASSWORD_HASHER.hash(password))
            return self._new_session(user)

    def refresh(self, token: str | None) -> AuthResult:
        if not token:
            raise AuthenticationRejectedError("Sessão expirada. Entre novamente.")
        session = self._repository.find_refresh_session(token_digest(token))
        now = datetime.now(timezone.utc)
        if session is None:
            raise AuthenticationRejectedError("Sessão inválida. Entre novamente.")
        if session.revoked_at is not None:
            with atomic(self._unit_of_work):
                self._repository.revoke_refresh_family(session.family_id, now)
            raise AuthenticationRejectedError("Sessão inválida. Entre novamente.")
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now or not session.user.is_active:
            with atomic(self._unit_of_work):
                self._repository.revoke_refresh_session(session.id, now)
            raise AuthenticationRejectedError("Sessão expirada. Entre novamente.")

        with atomic(self._unit_of_work):
            result = self._new_session(session.user, family_id=session.family_id)
            replacement_id = self._repository.find_refresh_session(
                token_digest(result.refresh_token)
            ).id
            self._repository.replace_refresh_session(
                session.id,
                now=now,
                replacement_id=replacement_id,
            )
            return result

    def logout(self, token: str | None) -> None:
        if not token:
            return
        session = self._repository.find_refresh_session(token_digest(token))
        if session is None or session.revoked_at is not None:
            return
        with atomic(self._unit_of_work):
            self._repository.revoke_refresh_session(session.id, datetime.now(timezone.utc))

    def current_user(self, user_id: UUID) -> dict:
        user = self._repository.find_user(user_id)
        if user is None or not user.is_active:
            raise AuthenticationRejectedError(
                "Sessão inválida ou expirada. Entre novamente.",
                challenge=True,
            )
        return user_payload(user)

    def google_login(self, identity: GoogleIdentity) -> AuthResult:
        # One retry handles a concurrent first login or session-token collision.
        for attempt in range(2):
            try:
                with atomic(self._unit_of_work):
                    user = self._find_or_create_google_user(identity)
                    if not user.is_active:
                        raise AccountDisabledError("Esta conta está desativada.")
                    return self._new_session(user)
            except PersistenceConflictError:
                if attempt:
                    raise
        raise AccountConflictError("Não foi possível concluir o login Google.")

    def _find_or_create_google_user(self, identity: GoogleIdentity) -> AuthUser:
        subject_hash = lookup_digest(identity.subject, namespace="google")
        user = self._repository.find_google_identity(subject_hash)
        if user is not None:
            return user

        normalized_email = identity.email.strip().casefold()
        email_lookup = lookup_digest(normalized_email)
        user = self._repository.find_user_by_email(email_lookup)
        if user is not None and not google_controls_email(normalized_email, identity.hosted_domain):
            raise AccountConflictError(
                "Este e-mail já está associado a uma conta. Entre em contato com o suporte para vinculá-la com segurança."
            )
        if user is None:
            user = self._create_user(normalized_email, identity.name)
        self._repository.create_google_identity(
            user.id,
            encrypt_personal_data(identity.subject),
            subject_hash,
        )
        return user

    def _create_user(self, email: str, name: str | None = None) -> AuthUser:
        return self._repository.create_user(
            email_ciphertext=encrypt_personal_data(email),
            email_lookup=lookup_digest(email),
            name_ciphertext=encrypt_personal_data(name) if name else None,
            encryption_key_version=int(os.getenv("AUTH_ENCRYPTION_KEY_VERSION", "1")),
        )

    def _new_session(
        self,
        user: AuthUser,
        *,
        family_id: UUID | None = None,
    ) -> AuthResult:
        refresh_token = secrets.token_urlsafe(48)
        family_id = family_id or uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30"))
        )
        self._repository.create_refresh_session(
            user.id,
            family_id,
            token_digest(refresh_token),
            expires_at,
        )
        access_token, expires_in = create_access_token(user.id)
        return AuthResult(
            user=user_payload(user),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )


def user_payload(user: AuthUser) -> dict:
    return {
        "id": user.id,
        "email": decrypt_personal_data(user.email_ciphertext),
        "name": decrypt_personal_data(user.name_ciphertext) if user.name_ciphertext else None,
    }


def google_controls_email(email: str, hosted_domain: str | None) -> bool:
    domain = email.rpartition("@")[2].casefold()
    return domain == "gmail.com" or bool(hosted_domain and domain == hosted_domain.casefold())


def create_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    return verifier, challenge


def oauth_state_cookie(payload: dict) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **payload,
        "iss": "expenses-api",
        "aud": "expenses-google-oauth-state",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    key = base64.b64decode(_cookie_secret(), validate=True)
    return jwt.encode(claims, key, algorithm="HS256")


def read_oauth_state_cookie(value: str) -> dict:
    try:
        key = base64.b64decode(_cookie_secret(), validate=True)
        return jwt.decode(
            value,
            key,
            algorithms=["HS256"],
            audience="expenses-google-oauth-state",
            issuer="expenses-api",
            options={
                "require": [
                    "iat",
                    "exp",
                    "iss",
                    "aud",
                    "state",
                    "nonce",
                    "verifier",
                    "request_id",
                    "mode",
                    "next",
                ]
            },
        )
    except (ValueError, jwt.PyJWTError) as error:
        raise OAuthAttemptError("A tentativa de login Google expirou. Tente novamente.") from error


def safe_oauth_destination(value: str | None) -> str:
    from urllib.parse import urlsplit

    if not value or len(value) > 2048:
        return "/despesas"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "/despesas"
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or "\\" in value
        or parsed.path not in _ALLOWED_DESTINATIONS
    ):
        return "/despesas"
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def _cookie_secret() -> str:
    secret = os.getenv("AUTH_TOKEN_SECRET", "")
    try:
        decoded = base64.b64decode(secret, validate=True)
    except ValueError as error:
        raise RuntimeError(
            "Configure AUTH_TOKEN_SECRET com uma chave Base64 aleatória de 32 bytes."
        ) from error
    if len(decoded) != 32:
        raise RuntimeError(
            "Configure AUTH_TOKEN_SECRET com uma chave Base64 aleatória de 32 bytes."
        )
    return secret
