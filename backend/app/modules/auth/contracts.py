"""Application results returned by authentication use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email_ciphertext: bytes
    name_ciphertext: bytes | None
    is_active: bool


@dataclass(frozen=True)
class RefreshSessionState:
    id: UUID
    user_id: UUID
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    user: AuthUser


@dataclass(frozen=True)
class AuthResult:
    user: dict
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str | None
    hosted_domain: str | None
