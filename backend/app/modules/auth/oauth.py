"""Google OAuth transport adapter and use cases."""

import os
import re
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from app.modules.auth.contracts import AuthResult, GoogleIdentity
from app.modules.auth.errors import (
    GoogleLoginUnavailableError,
    GoogleProviderError,
    OAuthModeError,
)
from app.modules.auth.service import (
    AuthService,
    create_pkce_pair,
    oauth_state_cookie,
    safe_oauth_destination,
)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,64}$")


@dataclass(frozen=True)
class OAuthStart:
    authorization_url: str
    state_cookie: str
    request_id: str
    mode: str


class GoogleIdentityProvider:
    async def authenticate(
        self,
        *,
        code: str,
        verifier: str,
        expected_nonce: str,
    ) -> GoogleIdentity:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        if not client_id or not client_secret or not redirect_uri:
            raise GoogleLoginUnavailableError

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": verifier,
                    },
                )
            response.raise_for_status()
            id_token = response.json()["id_token"]
        except httpx.HTTPStatusError as error:
            raise GoogleProviderError("token_exchange", code=_google_error_code(error)) from error
        except httpx.HTTPError as error:
            raise GoogleProviderError("token_exchange") from error
        except (KeyError, ValueError, TypeError) as error:
            raise GoogleProviderError("token_exchange") from error

        try:
            signing_key = (
                PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")
                .get_signing_key_from_jwt(id_token)
                .key
            )
        except (httpx.HTTPError, jwt.PyJWTError, ValueError) as error:
            raise GoogleProviderError("signing_key") from error

        try:
            claims = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=client_id,
                issuer=["https://accounts.google.com", "accounts.google.com"],
                options={
                    "require": [
                        "sub",
                        "email",
                        "email_verified",
                        "nonce",
                        "iss",
                        "aud",
                        "exp",
                    ]
                },
            )
            if claims["nonce"] != expected_nonce or claims["email_verified"] is not True:
                raise ValueError("invalid claims")
            email = claims["email"].strip().casefold()
            if not email:
                raise ValueError("missing email")
            return GoogleIdentity(
                subject=claims["sub"],
                email=email,
                name=claims.get("name"),
                hosted_domain=claims.get("hd"),
            )
        except (KeyError, ValueError, TypeError, jwt.PyJWTError) as error:
            raise GoogleProviderError("id_token_validation") from error


class GoogleOAuthService:
    def __init__(
        self,
        auth_service: AuthService,
        provider: GoogleIdentityProvider,
    ) -> None:
        self._auth_service = auth_service
        self._provider = provider

    @staticmethod
    def enabled() -> bool:
        return bool(
            os.getenv("GOOGLE_CLIENT_ID", "").strip()
            and os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
            and os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        )

    @staticmethod
    def begin(
        *,
        mode: str,
        request_id: str | None,
        destination: str | None,
    ) -> OAuthStart:
        if not GoogleOAuthService.enabled():
            raise GoogleLoginUnavailableError
        if mode not in {"popup", "redirect"}:
            raise OAuthModeError
        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        safe_request_id = (
            request_id
            if request_id and REQUEST_ID_PATTERN.fullmatch(request_id)
            else secrets.token_urlsafe(24)
        )
        safe_destination = safe_oauth_destination(destination)
        verifier, challenge = create_pkce_pair()
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        cookie = oauth_state_cookie(
            {
                "state": state,
                "nonce": nonce,
                "verifier": verifier,
                "request_id": safe_request_id,
                "mode": mode,
                "next": safe_destination,
            }
        )
        return OAuthStart(
            authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
            state_cookie=cookie,
            request_id=safe_request_id,
            mode=mode,
        )

    async def authenticate(self, code: str, saved_state: dict) -> AuthResult:
        identity = await self._provider.authenticate(
            code=code,
            verifier=saved_state["verifier"],
            expected_nonce=saved_state["nonce"],
        )
        return self._auth_service.google_login(identity)


def _google_error_code(error: httpx.HTTPStatusError) -> str:
    try:
        candidate = error.response.json().get("error")
    except (ValueError, TypeError, AttributeError):
        return "unknown"
    if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate):
        return candidate
    return "unknown"
