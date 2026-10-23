import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.model import ExternalIdentity, LocalCredential, RefreshSession, User
from app.shared.auth import create_access_token
from app.shared.crypto import decrypt_personal_data, encrypt_personal_data, lookup_digest, token_digest

password_hasher = PasswordHasher()
_DUMMY_PASSWORD_HASH = password_hasher.hash("expenses-invalid-account-check")


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": decrypt_personal_data(user.email_ciphertext),
        "name": decrypt_personal_data(user.name_ciphertext) if user.name_ciphertext else None,
    }


def _new_user(database: Session, email: str, name: str | None = None) -> User:
    key_version = int(os.getenv("AUTH_ENCRYPTION_KEY_VERSION", "1"))
    user = User(
        email_ciphertext=encrypt_personal_data(email),
        email_lookup=lookup_digest(email),
        name_ciphertext=encrypt_personal_data(name) if name else None,
        encryption_key_version=key_version,
    )
    database.add(user)
    database.flush()
    return user


def _create_session(database: Session, user: User) -> tuple[str, str, int]:
    refresh_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")))
    database.add(
        RefreshSession(
            user_id=user.id,
            family_id=uuid4(),
            token_hash=token_digest(refresh_token),
            expires_at=expires_at,
        )
    )
    access_token, expires_in = create_access_token(user.id)
    database.commit()
    return access_token, refresh_token, expires_in


def register(database: Session, email: str, password: str) -> tuple[User, str, str, int]:
    if database.scalar(select(User.id).where(User.email_lookup == lookup_digest(email))) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="JÃ¡ existe uma conta com este e-mail.")
    user = _new_user(database, email)
    database.add(LocalCredential(user_id=user.id, password_hash=password_hasher.hash(password)))
    access, refresh, expires = _create_session(database, user)
    return user, access, refresh, expires


def login(database: Session, email: str, password: str) -> tuple[User, str, str, int]:
    user = database.scalar(select(User).where(User.email_lookup == lookup_digest(email)))
    credential = user.credential if user else None
    valid = False
    try:
        valid = password_hasher.verify(
            credential.password_hash if credential else _DUMMY_PASSWORD_HASH,
            password,
        )
        if credential and valid and password_hasher.check_needs_rehash(credential.password_hash):
            credential.password_hash = password_hasher.hash(password)
    except (VerifyMismatchError, VerificationError):
        valid = False
    if not valid or user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.", headers={"WWW-Authenticate": "Bearer"})
    access, refresh, expires = _create_session(database, user)
    return user, access, refresh, expires


def rotate_refresh(database: Session, token: str | None) -> tuple[User, str, str, int]:
    if not token:
        raise HTTPException(status_code=401, detail="SessÃ£o expirada. Entre novamente.")
    session = database.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_digest(token)).with_for_update()
    )
    now = datetime.now(timezone.utc)
    if session is None:
        raise HTTPException(status_code=401, detail="SessÃ£o invÃ¡lida. Entre novamente.")
    if session.revoked_at is not None:
        database.query(RefreshSession).filter(RefreshSession.family_id == session.family_id).update({RefreshSession.revoked_at: now})
        database.commit()
        raise HTTPException(status_code=401, detail="SessÃ£o invÃ¡lida. Entre novamente.")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now or not session.user.is_active:
        session.revoked_at = now
        database.commit()
        raise HTTPException(status_code=401, detail="SessÃ£o expirada. Entre novamente.")

    user = session.user
    replacement = secrets.token_urlsafe(48)
    new_session = RefreshSession(
        user_id=user.id,
        family_id=session.family_id,
        token_hash=token_digest(replacement),
        expires_at=now + timedelta(days=int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30"))),
    )
    database.add(new_session)
    database.flush()
    session.revoked_at = now
    session.replaced_by_id = new_session.id
    access, expires_in = create_access_token(user.id)
    database.commit()
    return user, access, replacement, expires_in


def revoke_refresh(database: Session, token: str | None) -> None:
    if token:
        session = database.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_digest(token)))
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            database.commit()


def google_login(database: Session, subject: str, email: str, name: str | None) -> tuple[User, str, str, int]:
    subject_hash = lookup_digest(subject, namespace="google")
    identity = database.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.provider == "google",
            ExternalIdentity.subject_lookup == subject_hash,
        )
    )
    if identity:
        user = identity.user
    else:
        email_hash = lookup_digest(email)
        user = database.scalar(select(User).where(User.email_lookup == email_hash))
        if user is None:
            user = _new_user(database, email, name)
        database.add(
            ExternalIdentity(
                user_id=user.id,
                provider="google",
                subject_ciphertext=encrypt_personal_data(subject),
                subject_lookup=subject_hash,
            )
        )
        database.flush()
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Esta conta estÃ¡ desativada.")
    access, refresh, expires = _create_session(database, user)
    return user, access, refresh, expires


def oauth_state_cookie(payload: dict) -> str:
    from itsdangerous import URLSafeTimedSerializer

    return URLSafeTimedSerializer(_cookie_secret(), salt="expenses-google-oauth").dumps(payload)


def read_oauth_state_cookie(value: str) -> dict:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    try:
        result = URLSafeTimedSerializer(_cookie_secret(), salt="expenses-google-oauth").loads(value, max_age=600)
    except (BadSignature, SignatureExpired) as error:
        raise HTTPException(status_code=400, detail="A tentativa de login Google expirou. Tente novamente.") from error
    return result


def _cookie_secret() -> str:
    secret = os.getenv("AUTH_TOKEN_SECRET", "")
    try:
        decoded = base64.b64decode(secret, validate=True)
    except ValueError as error:
        raise RuntimeError("Configure AUTH_TOKEN_SECRET com uma chave Base64 aleatÃ³ria de 32 bytes.") from error
    if len(decoded) != 32:
        raise RuntimeError("Configure AUTH_TOKEN_SECRET com uma chave Base64 aleatÃ³ria de 32 bytes.")
    return secret


def create_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge
