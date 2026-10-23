import os
import secrets
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.auth.schema import AuthResponse, CredentialsInput, RegistrationInput, UserResponse
from app.modules.auth.service import (
    create_pkce_pair,
    google_login,
    login,
    oauth_state_cookie,
    read_oauth_state_cookie,
    register,
    revoke_refresh,
    rotate_refresh,
    user_payload,
)
from app.shared.auth import get_current_user
from app.shared.dependencies import get_db

router = APIRouter(tags=["AutenticaÃ§Ã£o"])
REFRESH_COOKIE = "expenses_refresh"
OAUTH_COOKIE = "expenses_google_oauth"


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


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_account(data: RegistrationInput, response: Response, database: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh, expires = register(database, data.email, data.password)
    return _auth_response(response, user, access, refresh, expires)


@router.post("/login", response_model=AuthResponse)
def login_account(data: CredentialsInput, response: Response, database: Session = Depends(get_db)) -> AuthResponse:
    user, access, refresh, expires = login(database, data.email, data.password)
    return _auth_response(response, user, access, refresh, expires)


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
def google_start(response: Response):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if not client_id or not os.getenv("GOOGLE_CLIENT_SECRET", "").strip() or not redirect_uri:
        raise HTTPException(status_code=503, detail="Login Google ainda nÃ£o estÃ¡ configurado.")
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
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302)
    response.set_cookie(
        OAUTH_COOKIE,
        oauth_state_cookie({"state": state, "nonce": nonce, "verifier": verifier}),
        max_age=600,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path=f"{os.getenv('AUTH_COOKIE_PATH', '/api/auth')}/google",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    database: Session = Depends(get_db),
):
    if error or not code or not state:
        raise HTTPException(status_code=400, detail="NÃ£o foi possÃ­vel concluir o login Google.")
    saved_state = read_oauth_state_cookie(request.cookies.get(OAUTH_COOKIE, ""))
    if not secrets.compare_digest(state, saved_state.get("state", "")):
        raise HTTPException(status_code=400, detail="A validaÃ§Ã£o do login Google falhou.")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
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
        signing_key = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs").get_signing_key_from_jwt(id_token).key
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
    except (httpx.HTTPError, KeyError, ValueError, jwt.PyJWTError) as error:
        raise HTTPException(status_code=401, detail="NÃ£o foi possÃ­vel validar a conta Google.") from error

    user, access, refresh, _ = google_login(database, claims["sub"], claims["email"].strip().casefold(), claims.get("name"))
    frontend_url = os.getenv("AUTH_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    response = RedirectResponse(f"{frontend_url}/auth/complete", status_code=303)
    response.set_cookie(value=refresh, **_cookie_options(int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30")) * 86400))
    response.delete_cookie(OAUTH_COOKIE, path=f"{os.getenv('AUTH_COOKIE_PATH', '/api/auth')}/google", httponly=True, samesite="lax")
    return response
