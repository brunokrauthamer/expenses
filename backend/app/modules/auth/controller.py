import logging
import os
import secrets
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_user_id,
    get_google_oauth_service,
)
from app.modules.auth.errors import (
    AccountConflictError,
    AccountDisabledError,
    AuthenticationRejectedError,
    GoogleLoginUnavailableError,
    GoogleProviderError,
    OAuthAttemptError,
    OAuthModeError,
)
from app.modules.auth.oauth import REQUEST_ID_PATTERN, GoogleOAuthService
from app.modules.auth.schema import (
    AuthResponse,
    CredentialsInput,
    RegistrationInput,
    UserResponse,
)
from app.modules.auth.service import (
    AuthService,
    read_oauth_state_cookie,
    safe_oauth_destination,
)
from app.shared.exceptions import PersistenceConflictError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Autenticação"])
REFRESH_COOKIE = "expenses_refresh"
OAUTH_COOKIE = "expenses_google_oauth"
OAUTH_PATH = f"{os.getenv('AUTH_COOKIE_PATH', '/api/auth')}/google"


def _cookie_options(max_age: int) -> dict:
    return {
        "key": REFRESH_COOKIE,
        "httponly": True,
        "secure": os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        "samesite": "lax",
        "path": os.getenv("AUTH_COOKIE_PATH", "/api/auth"),
        "max_age": max_age,
    }


def _auth_response(response: Response, result) -> AuthResponse:
    response.set_cookie(
        value=result.refresh_token,
        **_cookie_options(int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")) * 86400),
    )
    return AuthResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        user=UserResponse(**result.user),
    )


def _auth_error(error: AuthenticationRejectedError) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if error.challenge else None
    return HTTPException(status_code=401, detail=error.detail, headers=headers)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_account(
    data: RegistrationInput,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        return _auth_response(response, service.register(data.email, data.password))
    except AccountConflictError as error:
        raise HTTPException(status_code=409, detail=error.detail) from error
    except AuthenticationRejectedError as error:
        raise _auth_error(error) from error


@router.post("/login", response_model=AuthResponse)
def login_account(
    data: CredentialsInput,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        return _auth_response(response, service.login(data.email, data.password))
    except AuthenticationRejectedError as error:
        raise _auth_error(error) from error


def _delete_oauth_cookie(response: Response) -> None:
    response.delete_cookie(
        OAUTH_COOKIE,
        path=OAUTH_PATH,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )


def _completion_redirect(
    *,
    request_id: str | None,
    mode: str,
    reason: str | None = None,
    destination: str = "/despesas",
) -> RedirectResponse:
    frontend_url = os.getenv("AUTH_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    values = {"result": "error" if reason else "success"}
    if request_id:
        values["request_id"] = request_id
    if reason:
        values["reason"] = reason
    if mode == "redirect" and not reason:
        values["next"] = safe_oauth_destination(destination)
    response = RedirectResponse(
        f"{frontend_url}/auth/complete?{urlencode(values)}",
        status_code=303,
    )
    _delete_oauth_cookie(response)
    return response


def _failure(
    request_id: str | None,
    mode: str = "popup",
    reason: str = "failed",
    *,
    stage: str = "callback",
) -> RedirectResponse:
    safe_id = (
        request_id if request_id and REQUEST_ID_PATTERN.fullmatch(request_id) else "unavailable"
    )
    logger.warning(
        "Google OAuth failed: request_id=%s stage=%s reason=%s",
        safe_id,
        stage,
        reason,
    )
    return _completion_redirect(request_id=request_id, mode=mode, reason=reason)


@router.post("/refresh", response_model=AuthResponse)
def refresh_session(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        return _auth_response(
            response,
            service.refresh(request.cookies.get(REFRESH_COOKIE)),
        )
    except AuthenticationRejectedError as error:
        raise _auth_error(error) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    service.logout(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(
        REFRESH_COOKIE,
        path=os.getenv("AUTH_COOKIE_PATH", "/api/auth"),
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(
    user_id: UUID = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        return UserResponse(**service.current_user(user_id))
    except AuthenticationRejectedError as error:
        raise _auth_error(error) from error


@router.get("/google/status")
def google_status() -> dict[str, bool]:
    return {"enabled": GoogleOAuthService.enabled()}


@router.get("/google/start")
def google_start(
    mode: str = "popup",
    request_id: str | None = None,
    next: str | None = None,
):
    try:
        attempt = GoogleOAuthService.begin(
            mode=mode,
            request_id=request_id,
            destination=next,
        )
    except GoogleLoginUnavailableError as error:
        raise HTTPException(
            status_code=503,
            detail="Login Google ainda não está configurado.",
        ) from error
    except OAuthModeError as error:
        raise HTTPException(status_code=400, detail="Modo de login Google inválido.") from error

    login_response = RedirectResponse(attempt.authorization_url, status_code=302)
    login_response.set_cookie(
        OAUTH_COOKIE,
        attempt.state_cookie,
        max_age=600,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path=OAUTH_PATH,
    )
    return login_response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    service: GoogleOAuthService = Depends(get_google_oauth_service),
):
    cookie = request.cookies.get(OAUTH_COOKIE)
    if not cookie:
        return _failure(None, reason="expired", stage="cookie_missing")
    try:
        saved_state = read_oauth_state_cookie(cookie)
    except OAuthAttemptError:
        return _failure(None, reason="expired", stage="cookie_invalid")

    request_id = saved_state.get("request_id")
    mode = saved_state.get("mode", "popup")
    if not REQUEST_ID_PATTERN.fullmatch(request_id or "") or mode not in {"popup", "redirect"}:
        return _failure(None, reason="expired", stage="attempt_invalid")
    if not state or not secrets.compare_digest(state, saved_state.get("state", "")):
        return _failure(request_id, mode, "expired", stage="state_mismatch")
    if error:
        reason = "cancelled" if error == "access_denied" else "failed"
        return _failure(request_id, mode, reason, stage="google_authorization")
    if not code:
        return _failure(request_id, mode, "expired", stage="code_missing")

    try:
        result = await service.authenticate(code, saved_state)
    except GoogleProviderError as failure:
        logger.warning(
            "Google OAuth provider failed: stage=%s code=%s",
            failure.stage,
            failure.code,
        )
        return _failure(request_id, mode, "failed", stage=failure.stage)
    except AccountConflictError:
        return _failure(request_id, mode, "account_conflict", stage="account_link")
    except AccountDisabledError:
        return _failure(request_id, mode, "failed", stage="account_status")
    except (PersistenceConflictError, AuthenticationRejectedError):
        return _failure(request_id, mode, "failed", stage="session_creation")

    completion = _completion_redirect(
        request_id=request_id,
        mode=mode,
        destination=saved_state.get("next", "/despesas"),
    )
    completion.set_cookie(
        value=result.refresh_token,
        **_cookie_options(int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")) * 86400),
    )
    return completion
