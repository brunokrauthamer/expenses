import base64
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.shared.dependencies import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    minutes = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))
    now = datetime.now(timezone.utc)
    encoded_key = os.getenv("AUTH_JWT_PRIVATE_KEY_B64", "")
    try:
        key = base64.b64decode(encoded_key, validate=True)
    except ValueError as error:
        raise RuntimeError("Configure AUTH_JWT_PRIVATE_KEY_B64 com a chave privada RSA em Base64.") from error
    if not key.startswith(b"-----BEGIN"):
        raise RuntimeError("AUTH_JWT_PRIVATE_KEY_B64 deve conter uma chave privada PEM codificada em Base64.")
    claims = {
        "sub": str(user_id),
        "iss": os.getenv("AUTH_TOKEN_ISSUER", "expenses-api"),
        "aud": os.getenv("AUTH_TOKEN_AUDIENCE", "expenses-web"),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "jti": os.urandom(16).hex(),
    }
    return jwt.encode(claims, key, algorithm="RS256"), minutes * 60


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="SessÃ£o invÃ¡lida ou expirada. Entre novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        key = base64.b64decode(os.getenv("AUTH_JWT_PUBLIC_KEY_B64", ""), validate=True)
        if not key.startswith(b"-----BEGIN"):
            raise ValueError("invalid PEM")
        claims = jwt.decode(
            credentials.credentials,
            key,
            algorithms=["RS256"],
            audience=os.getenv("AUTH_TOKEN_AUDIENCE", "expenses-web"),
            issuer=os.getenv("AUTH_TOKEN_ISSUER", "expenses-api"),
            options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
        )
        user_id = UUID(claims["sub"])
    except (ValueError, jwt.PyJWTError):
        raise unauthorized from None
    user = database.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
