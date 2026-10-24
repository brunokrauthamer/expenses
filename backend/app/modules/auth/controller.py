import logging
import os
import re
import secrets
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.modules.auth.model import User
from app.modules.auth.schema import AuthResponse, UserResponse
from app.modules.auth.service import (
    create_pkce_pair,
    google_login,
    oauth_state_cookie,
    read_oauth_state_cookie,
    revoke_refresh,
    rotate_refresh,
    user_payload,
)
from app.shared.auth import get_current_user
from app.shared.dependencies import get_db

router = APIRouter(tags=["Autenticação"])
REFRESH_COOKIE = "expenses_refresh"
OAUTH_COOKIE = "expenses_google_oauth"
OAUTH_PATH = f"{os.getenv('AUTH_COOKIE_PATH', '/api/auth')}/google"
ALLOWED_DESTINATIONS = {"/despesas", "/gastos", "/consolidado"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,64}$")


def _cookie_options(max_age: int) -> dict:
    return {
        "key": REFRESH_COOKIE,
        "httponly": True,
        "secure": os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        "samesite": "lax",
        "path": os.getenv("AUTH_COOKIE_PATH", "/api/auth"),
        "max_age": max_age,
    }


def _auth_response(response: Response, user: User, access: str, refresh: str, expires: int) -> AuthResponse:
    response.set_cookie(value=refresh, **_cookie_options(int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")) * 86400))
    return AuthResponse(access_token=access, expires_in=expires, user=UserResponse(**user_payload(user)))


def _delete_oauth_cookie(response: Response) -> None:
    response.delete_cookie(
        OAUTH_COOKIE,
        path=OAUTH_PATH,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )


def _safe_destination(value: str | None) -> str:
    if not value or len(value) > 2048:
        return "/despesas"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "/despesas"
    if parsed.scheme or parsed.netloc or parsed.fragment or "\\" in value or parsed.path not in ALLOWED_DESTINATIONS:
        return "/despesas"
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def _completion_redirect(*, request_id: str | None, mode: str, reason: str | None = None, destination: str = "/despesas") -> RedirectResponse:
    frontend_url = os.getenv("AUTH_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    values = {"result": "error" if reason else "success"}
    if request_id:
        values["request_id"] = request_id
    if reason:
        values["reason"] = reason
    if mode == "redirect" and not reason:
        values["next"] = _safe_destination(destination)
    response = RedirectResponse(f"{frontend_url}/auth/complete?{urlencode(values)}", status_code=303)
    _delete_oauth_cookie(response)
    return response


def _failure(request_id: str | None, mode: str = "popup", reason: str = "failed", *, stage: str = "callback") -> RedirectResponse:
    # Only controlled labels and a validated random attempt ID belong in logs.
    safe_id = request_id if request_id and REQUEST_ID_PATTERN.fullmatch(request_id) else "unavailable"
    logger.warning("Google OAuth failed: request_id=%s stage=%s reason=%s", safe_id, stage, reason)
    return _completion_redirect(request_id=request_id, mode=mode, reason=reason)


@router.post("/refresh", response_model=AuthResponse)
def refresh_session(request: Request, response: Response, database: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh, expires = rotate_refresh(database, request.cookies.get(REFRESH_COOKIE))
    return _auth_response(response, user, access, refresh, expires)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, database: Session = Depends(get_db)) -> Response:
    revoke_refresh(database, request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(REFRESH_COOKIE, path=os.getenv("AUTH_COOKIE_PATH", "/api/auth"), httponly=True, secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true", samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**user_payload(user))


@router.get("/google/status")
def google_status() -> dict[str, bool]:
    return {
        "enabled": bool(
            os.getenv("GOOGLE_CLIENT_ID", "").strip()
            and os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
            and os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        )
    }


@router.get("/google/start")
def google_start(
    mode: str = "popup",
    request_id: str | None = None,
    next: str | None = None,
):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if not client_id or not os.getenv("GOOGLE_CLIENT_SECRET", "").strip() or not redirect_uri:
        raise HTTPException(status_code=503, detail="Login Google ainda não está configurado.")
    if mode not in {"popup", "redirect"}:
        raise HTTPException(status_code=400, detail="Modo de login Google inválido.")

    safe_request_id = request_id if request_id and REQUEST_ID_PATTERN.fullmatch(request_id) else secrets.token_urlsafe(24)
    safe_next = _safe_destination(next)
    verifier, challenge = create_pkce_pair()
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    target = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    login_response = RedirectResponse(target, status_code=302)
    login_response.set_cookie(
        OAUTH_COOKIE,
        oauth_state_cookie({
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "request_id": safe_request_id,
            "mode": mode,
            "next": safe_next,
        }),
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
    database: Session = Depends(get_db),
):
    cookie = request.cookies.get(OAUTH_COOKIE)
    if not cookie:
        return _failure(None, reason="expired", stage="cookie_missing")
    try:
        saved_state = read_oauth_state_cookie(cookie)
    except HTTPException:
        return _failure(None, reason="expired", stage="cookie_invalid")
    request_id = saved_state.get("request_id")
    mode = saved_state.get("mode", "popup")
    if not REQUEST_ID_PATTERN.fullmatch(request_id or "") or mode not in {"popup", "redirect"}:
        return _failure(None, reason="expired", stage="attempt_invalid")
    if not state or not secrets.compare_digest(state, saved_state.get("state", "")):
        return _failure(request_id, mode, "expired", stage="state_mismatch")
    if error:
        return _failure(request_id, mode, "cancelled" if error == "access_denied" else "failed", stage="google_authorization")
    if not code:
        return _failure(request_id, mode, "expired", stage="code_missing")

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    stage = "token_exchange"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": saved_state["verifier"],
                },
            )
        token_response.raise_for_status()
        id_token = token_response.json()["id_token"]
        stage = "signing_key"
        signing_key = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs").get_signing_key_from_jwt(id_token).key
        stage = "id_token_validation"
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=os.getenv("GOOGLE_CLIENT_ID", ""),
            issuer=["https://accounts.google.com", "accounts.google.com"],
            options={"require": ["sub", "email", "email_verified", "nonce", "iss", "aud", "exp"]},
        )
        if claims["nonce"] != saved_state["nonce"] or claims["email_verified"] is not True:
            raise ValueError("invalid Google claims")
        stage = "session_creation"
        user, _, refresh, _ = google_login(
            database,
            claims["sub"],
            claims["email"].strip().casefold(),
            claims.get("name"),
            hosted_domain=claims.get("hd"),
        )
    except IntegrityError:
        database.rollback()
        logger.warning("Google OAuth identity/session database conflict")
        try:
            user, _, refresh, _ = google_login(
                database,
                claims["sub"],
                claims["email"].strip().casefold(),
                claims.get("name"),
                hosted_domain=claims.get("hd"),
            )
        except HTTPException as exc:
            database.rollback()
            logger.warning("Google OAuth account rejected with status %s", exc.status_code)
            return _failure(request_id, mode, "account_conflict" if exc.status_code == 409 else "failed", stage=stage)
        except IntegrityError:
            database.rollback()
            logger.warning("Google OAuth identity/session database conflict after retry")
            return _failure(request_id, mode, "failed", stage=stage)
    except HTTPException as exc:
        database.rollback()
        logger.warning("Google OAuth account rejected with status %s", exc.status_code)
        return _failure(request_id, mode, "account_conflict" if exc.status_code == 409 else "failed", stage=stage)
    except httpx.HTTPStatusError as exc:
        database.rollback()
        error_code = "unknown"
        try:
            candidate = exc.response.json().get("error")
            if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate):
                error_code = candidate
        except (ValueError, TypeError, AttributeError):
            pass
        logger.warning("Google OAuth token exchange rejected: HTTP %s, code %s", exc.response.status_code, error_code)
        return _failure(request_id, mode, "failed", stage=stage)
    except httpx.HTTPError as exc:
        database.rollback()
        logger.warning("Google OAuth network/JWK request failed: %s", type(exc).__name__)
        return _failure(request_id, mode, "failed", stage=stage)
    except KeyError as exc:
        database.rollback()
        missing = exc.args[0] if exc.args else "unknown"
        if missing not in {"id_token", "sub", "email", "email_verified", "nonce", "iss", "aud", "exp"}:
            missing = "unknown"
        logger.warning("Google OAuth response/claims missing field: %s", missing)
        return _failure(request_id, mode, "failed", stage=stage)
    except ValueError:
        database.rollback()
        logger.warning("Google OAuth claims validation failed")
        return _failure(request_id, mode, "failed", stage=stage)
    except jwt.PyJWTError as exc:
        database.rollback()
        logger.warning("Google OAuth ID token validation failed: %s", type(exc).__name__)
        return _failure(request_id, mode, "failed", stage=stage)

    completion = _completion_redirect(
        request_id=request_id,
        mode=mode,
        destination=saved_state.get("next", "/despesas"),
    )
    completion.set_cookie(value=refresh, **_cookie_options(int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")) * 86400))
    return completion
