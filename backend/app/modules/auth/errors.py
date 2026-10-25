"""Authentication and external-provider failures with no HTTP dependency."""


class AuthenticationRejectedError(Exception):
    def __init__(self, detail: str, *, challenge: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.challenge = challenge


class AccountConflictError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AccountDisabledError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class OAuthAttemptError(Exception):
    pass


class GoogleLoginUnavailableError(Exception):
    pass


class OAuthModeError(Exception):
    pass


class GoogleProviderError(Exception):
    def __init__(self, stage: str, *, code: str | None = None) -> None:
        super().__init__(stage)
        self.stage = stage
        self.code = code or "unknown"
