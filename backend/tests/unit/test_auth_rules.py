from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from app.modules.auth.contracts import AuthUser, RefreshSessionState
from app.modules.auth.errors import AuthenticationRejectedError
from app.modules.auth.service import (
    AuthService,
    create_pkce_pair,
    google_controls_email,
    oauth_state_cookie,
    read_oauth_state_cookie,
    safe_oauth_destination,
)

pytestmark = pytest.mark.unit


def test_google_email_policy_only_allows_gmail_or_matching_hosted_domain():
    assert google_controls_email("person@gmail.com", None)
    assert google_controls_email("person@example.com", "EXAMPLE.COM")
    assert not google_controls_email("person@example.com", None)
    assert not google_controls_email("person@other.com", "example.com")


def test_oauth_return_destination_is_limited_to_internal_routes():
    assert safe_oauth_destination("/gastos?month=2026-10") == "/gastos?month=2026-10"
    assert safe_oauth_destination("https://evil.example/despesas") == "/despesas"
    assert safe_oauth_destination("//evil.example/despesas") == "/despesas"
    assert safe_oauth_destination("/nao-permitida") == "/despesas"


def test_pkce_pair_uses_s256_and_state_cookie_is_signed(auth_environment):
    import base64
    import hashlib

    verifier, challenge = create_pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    assert challenge == expected.rstrip(b"=").decode()

    state = {
        "state": "state-value",
        "nonce": "nonce-value",
        "verifier": verifier,
        "request_id": "a" * 24,
        "mode": "popup",
        "next": "/despesas",
    }
    encoded = oauth_state_cookie(state)
    assert read_oauth_state_cookie(encoded)["state"] == "state-value"


def test_refresh_reuse_commits_family_revocation_before_rejecting(auth_environment):
    now = datetime.now(timezone.utc)
    user = AuthUser(uuid4(), b"ciphertext", None, True)
    session = RefreshSessionState(
        id=uuid4(),
        user_id=user.id,
        family_id=uuid4(),
        expires_at=now + timedelta(days=1),
        revoked_at=now,
        user=user,
    )

    class FakeRepository:
        revoked_family = None

        def find_refresh_session(self, _token_hash):
            return session

        def revoke_refresh_family(self, family_id, revoked_at):
            self.revoked_family = (family_id, revoked_at)

    class FakeUnitOfWork:
        commits = 0
        rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    repository = FakeRepository()
    unit_of_work = FakeUnitOfWork()
    service = AuthService(repository, unit_of_work)

    with pytest.raises(AuthenticationRejectedError, match="Sessão inválida"):
        service.refresh("reused-refresh-token")

    assert repository.revoked_family[0] == session.family_id
    assert unit_of_work.commits == 1
    assert unit_of_work.rollbacks == 0
