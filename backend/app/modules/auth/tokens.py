"""JWT access-token operations without HTTP or database dependencies."""

import base64
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt


class InvalidAccessTokenError(ValueError):
    pass


def create_access_token(user_id: UUID) -> tuple[str, int]:
    minutes = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))
    now = datetime.now(timezone.utc)
    encoded_key = os.getenv("AUTH_JWT_PRIVATE_KEY_B64", "")
    try:
        key = base64.b64decode(encoded_key, validate=True)
    except ValueError as error:
        raise RuntimeError(
            "Configure AUTH_JWT_PRIVATE_KEY_B64 com a chave privada RSA em Base64."
        ) from error
    if not key.startswith(b"-----BEGIN"):
        raise RuntimeError(
            "AUTH_JWT_PRIVATE_KEY_B64 deve conter uma chave privada PEM codificada em Base64."
        )
    claims = {
        "sub": str(user_id),
        "iss": os.getenv("AUTH_TOKEN_ISSUER", "expenses-api"),
        "aud": os.getenv("AUTH_TOKEN_AUDIENCE", "expenses-web"),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "jti": os.urandom(16).hex(),
    }
    return jwt.encode(claims, key, algorithm="RS256"), minutes * 60


def decode_access_token(token: str) -> UUID:
    try:
        key = base64.b64decode(os.getenv("AUTH_JWT_PUBLIC_KEY_B64", ""), validate=True)
        if not key.startswith(b"-----BEGIN"):
            raise ValueError("invalid PEM")
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=os.getenv("AUTH_TOKEN_AUDIENCE", "expenses-web"),
            issuer=os.getenv("AUTH_TOKEN_ISSUER", "expenses-api"),
            options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
        )
        return UUID(claims["sub"])
    except (ValueError, jwt.PyJWTError) as error:
        raise InvalidAccessTokenError("Invalid or expired access token.") from error
