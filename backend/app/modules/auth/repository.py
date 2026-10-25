"""SQLAlchemy persistence adapter for accounts, identities and refresh sessions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.contracts import AuthUser, RefreshSessionState
from app.modules.auth.model import ExternalIdentity, LocalCredential, RefreshSession, User
from app.shared.exceptions import PersistenceConflictError
from app.shared.reference_data import initialize_user_reference_data


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_user_by_email(self, email_lookup: str) -> AuthUser | None:
        user = self._session.scalar(select(User).where(User.email_lookup == email_lookup))
        return self._user_record(user) if user is not None else None

    def find_user(self, user_id: UUID) -> AuthUser | None:
        user = self._session.get(User, user_id)
        return self._user_record(user) if user is not None else None

    def user_is_active(self, user_id: UUID) -> bool:
        return self._session.scalar(select(User.is_active).where(User.id == user_id)) is True

    def create_user(
        self,
        *,
        email_ciphertext: bytes,
        email_lookup: str,
        name_ciphertext: bytes | None,
        encryption_key_version: int,
    ) -> AuthUser:
        user = User(
            email_ciphertext=email_ciphertext,
            email_lookup=email_lookup,
            name_ciphertext=name_ciphertext,
            encryption_key_version=encryption_key_version,
        )
        self._session.add(user)
        self._flush()
        initialize_user_reference_data(self._session, user)
        self._session.flush()
        return self._user_record(user)

    def password_hash(self, user_id: UUID) -> str | None:
        return self._session.scalar(
            select(LocalCredential.password_hash).where(LocalCredential.user_id == user_id)
        )

    def save_password_hash(self, user_id: UUID, password_hash: str) -> None:
        credential = self._session.get(LocalCredential, user_id)
        if credential is None:
            self._session.add(LocalCredential(user_id=user_id, password_hash=password_hash))
        else:
            credential.password_hash = password_hash
        self._flush()

    def create_refresh_session(
        self,
        user_id: UUID,
        family_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        session = RefreshSession(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(session)
        self._flush()
        return session.id

    def find_refresh_session(self, token_hash: str) -> RefreshSessionState | None:
        session = self._session.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
        )
        if session is None:
            return None
        return RefreshSessionState(
            id=session.id,
            user_id=session.user_id,
            family_id=session.family_id,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            user=self._user_record(session.user),
        )

    def replace_refresh_session(
        self,
        session_id: UUID,
        *,
        now: datetime,
        replacement_id: UUID,
    ) -> None:
        session = self._session.get(RefreshSession, session_id)
        if session is not None:
            session.revoked_at = now
            session.replaced_by_id = replacement_id
        self._flush()

    def revoke_refresh_family(self, family_id: UUID, now: datetime) -> None:
        self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id)
            .values(revoked_at=now)
        )
        self._flush()

    def revoke_refresh_session(self, session_id: UUID, now: datetime) -> None:
        session = self._session.get(RefreshSession, session_id)
        if session is not None and session.revoked_at is None:
            session.revoked_at = now
            self._flush()

    def find_google_identity(self, subject_lookup: str) -> AuthUser | None:
        identity = self._session.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == "google",
                ExternalIdentity.subject_lookup == subject_lookup,
            )
        )
        return self._user_record(identity.user) if identity is not None else None

    def create_google_identity(
        self,
        user_id: UUID,
        subject_ciphertext: bytes,
        subject_lookup: str,
    ) -> None:
        self._session.add(
            ExternalIdentity(
                user_id=user_id,
                provider="google",
                subject_ciphertext=subject_ciphertext,
                subject_lookup=subject_lookup,
            )
        )
        self._flush()

    @staticmethod
    def _user_record(user: User) -> AuthUser:
        return AuthUser(
            id=user.id,
            email_ciphertext=user.email_ciphertext,
            name_ciphertext=user.name_ciphertext,
            is_active=user.is_active,
        )

    def _flush(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflictError(
                "A database uniqueness constraint was violated."
            ) from error
