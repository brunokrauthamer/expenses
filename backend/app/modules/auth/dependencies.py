"""HTTP authentication and application composition dependencies."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.modules.auth.contracts import AuthUser
from app.modules.auth.oauth import GoogleIdentityProvider, GoogleOAuthService
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.auth.tokens import InvalidAccessTokenError, decode_access_token
from app.shared.dependencies import get_db
from app.shared.sqlalchemy_uow import SqlAlchemyUnitOfWork

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    database: Session = Depends(get_db),
) -> AuthUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Entre novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidAccessTokenError:
        raise unauthorized from None
    user = AuthRepository(database).find_user(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_current_user_id(user: AuthUser = Depends(get_current_user)) -> UUID:
    """Expose the account ID rather than an ORM entity to business handlers."""
    return user if isinstance(user, UUID) else user.id


def get_auth_service(database: Session = Depends(get_db)) -> AuthService:
    return AuthService(AuthRepository(database), SqlAlchemyUnitOfWork(database))


def get_google_oauth_service(
    auth_service: AuthService = Depends(get_auth_service),
) -> GoogleOAuthService:
    return GoogleOAuthService(auth_service, GoogleIdentityProvider())
