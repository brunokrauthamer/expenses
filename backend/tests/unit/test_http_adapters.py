import asyncio
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.modules.auth.contracts import AuthResult
from app.modules.auth.errors import (
    AccountConflictError,
    AuthenticationRejectedError,
    OAuthAttemptError,
)
from app.modules.auth.schema import CredentialsInput, RegistrationInput
from app.modules.categories.schema import CategoryCreate, CategoryUpdate
from app.modules.expenses.schema import ExpenseCreate, ExpenseUpdate
from app.modules.income_entries.schema import (
    IncomeCategoryCreate,
    IncomeCategoryUpdate,
    IncomeEntryCreate,
)
from app.modules.payment_methods.schema import PaymentMethodCreate, PaymentMethodUpdate
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError
from fastapi import HTTPException, Response
from starlette.requests import Request

pytestmark = pytest.mark.unit


def _request(cookie: str | None = None) -> Request:
    headers = [] if cookie is None else [(b"cookie", cookie.encode())]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 1),
        }
    )


@pytest.mark.parametrize(
    ("controller", "create_data", "update_data", "create_name", "update_name"),
    [
        (
            "categories",
            CategoryCreate(name="Casa"),
            CategoryUpdate(name="Moradia"),
            "post_category",
            "put_category",
        ),
        (
            "payment_methods",
            PaymentMethodCreate(name="PIX"),
            PaymentMethodUpdate(name="Cartão"),
            "post_payment_method",
            "put_payment_method",
        ),
    ],
)
def test_catalog_controllers_forward_account_and_map_errors(
    controller, create_data, update_data, create_name, update_name
):
    from importlib import import_module

    module = import_module(f"app.modules.{controller}.controller")
    user_id = uuid4()

    class Service:
        def __init__(self):
            self.calls = []
            self.failure = None

        def list(self, *args):
            self.calls.append(("list", args))
            return []

        def create(self, *args):
            self.calls.append(("create", args))
            if self.failure:
                raise self.failure
            return {"id": 1, "name": args[-1]}

        def update(self, *args):
            self.calls.append(("update", args))
            if self.failure:
                raise self.failure
            return {"id": args[0], "name": args[-1]}

        def delete(self, *args):
            self.calls.append(("delete", args))
            if self.failure:
                raise self.failure

    service = Service()
    assert getattr(module, f"get_{controller}")(True, service, user_id) == []
    assert getattr(module, create_name)(create_data, service, user_id)["name"] == create_data.name
    assert (
        getattr(module, update_name)(12, update_data, service, user_id)["name"] == update_data.name
    )
    assert (
        getattr(module, f"remove_{'category' if controller == 'categories' else 'payment_method'}")(
            12, service, user_id
        ).status_code
        == 204
    )
    assert service.calls[0] == ("list", (user_id, True))
    assert service.calls[1] == ("create", (user_id, create_data.name))
    assert service.calls[2] == ("update", (12, user_id, update_data.name))
    assert service.calls[3] == ("delete", (12, user_id))

    service.failure = DuplicateResourceError("duplicado")
    with pytest.raises(HTTPException) as duplicate:
        getattr(module, create_name)(create_data, service, user_id)
    assert duplicate.value.status_code == 409
    service.failure = ValueError("inválido")
    with pytest.raises(HTTPException) as invalid:
        getattr(module, update_name)(12, update_data, service, user_id)
    assert invalid.value.status_code == 422
    service.failure = ResourceNotFoundError("ausente")
    with pytest.raises(HTTPException) as missing:
        getattr(module, update_name)(12, update_data, service, user_id)
    assert missing.value.status_code == 404


def test_income_category_controller_maps_conflicts_and_not_found():
    from app.modules.income_entries import controller

    user_id = uuid4()

    class Service:
        error = None

        def list(self, *_args):
            return []

        def create(self, *_args):
            if self.error:
                raise self.error
            return {"id": 1}

        def update(self, *_args):
            if self.error:
                raise self.error
            return {"id": 1}

        def delete(self, *_args):
            if self.error:
                raise self.error

    service = Service()
    data = IncomeCategoryCreate(name="Reembolso", requires_expense_category=True)
    assert controller.get_income_categories(True, service, user_id) == []
    assert controller.post_income_category(data, service, user_id) == {"id": 1}
    service.error = DuplicateResourceError("duplicado")
    with pytest.raises(HTTPException) as duplicate:
        controller.post_income_category(data, service, user_id)
    assert duplicate.value.status_code == 409
    service.error = ValueError("inválido")
    with pytest.raises(HTTPException) as invalid:
        controller.post_income_category(data, service, user_id)
    assert invalid.value.status_code == 422

    update = IncomeCategoryUpdate(name="Reembolso", requires_expense_category=True)
    service.error = ResourceNotFoundError("ausente")
    with pytest.raises(HTTPException) as missing:
        controller.put_income_category(1, update, service, user_id)
    assert missing.value.status_code == 404
    assert controller.remove_income_category(1, Service(), user_id).status_code == 204


def test_expense_controller_maps_reads_commands_and_write_errors():
    from app.modules.expenses import controller

    user_id = uuid4()

    class Service:
        error = None

        def list(self, *args):
            self.list_args = args
            return [], 0

        def history(self, *args):
            self.history_args = args
            return [], 0, Decimal("0"), Decimal("0"), Decimal("0")

        def recent(self, *_args):
            return []

        def in_month(self, *_args):
            return []

        def summary(self, *_args):
            return {
                "total_amount_due": Decimal("0"),
                "gross_expense_amount": Decimal("0"),
                "reimbursement_amount": Decimal("0"),
                "net_expense_amount": Decimal("0"),
                "monthly_totals": [],
                "category_totals": [],
            }

        def create(self, _user_id, command):
            self.command = command
            if self.error:
                raise self.error
            return _expense_response_data()

        def update(self, _user_id, _expense_id, command):
            self.command = command
            if self.error:
                raise self.error
            return _expense_response_data()

        def delete(self, *_args):
            if self.error:
                raise self.error

    service = Service()
    assert (
        controller.get_expenses(
            2, 15, "2026-01", "2025-12", "2026-01", "texto", 3, 4, service, user_id
        ).total_pages
        == 0
    )
    assert service.list_args == (user_id, 2, 15, "2026-01", "texto", "2025-12", "2026-01", 3, 4)
    assert (
        controller.get_expense_history("2026-01", 1, 20, None, None, None, service, user_id).total
        == 0
    )
    assert controller.get_recent_expenses(5, service, user_id) == []
    assert controller.get_expenses_paid_in_month("2026-01", service, user_id) == []
    assert (
        controller.get_expenses_summary(
            "2026-01", "2026-01", None, None, None, service, user_id
        ).total_amount_due
        == 0
    )

    data = ExpenseCreate(
        description=" Compra ",
        amount="12.50",
        expense_date=date(2026, 1, 4),
        category_id=3,
        payment_method_id=4,
    )
    assert controller.post_expense(data, service, user_id).id == 1
    assert service.command.description == "Compra"
    assert service.command.amount == Decimal("12.50")
    assert service.command.expense_date == date(2026, 1, 4)
    assert controller.put_expense(1, ExpenseUpdate(**data.model_dump()), service, user_id).id == 1
    assert controller.delete_expense_route(1, service, user_id).status_code == 204

    service.error = ResourceNotFoundError("ausente")
    with pytest.raises(HTTPException) as missing:
        controller.post_expense(data, service, user_id)
    assert missing.value.status_code == 404
    service.error = ValueError("inválido")
    with pytest.raises(HTTPException) as invalid:
        controller.put_expense(1, data, service, user_id)
    assert invalid.value.status_code == 422
    service.error = ResourceNotFoundError("ausente")
    with pytest.raises(HTTPException) as delete_missing:
        controller.delete_expense_route(1, service, user_id)
    assert delete_missing.value.status_code == 404


def _expense_response_data():
    return {
        "id": 1,
        "description": "Compra",
        "amount": Decimal("12.50"),
        "expense_date": date(2026, 1, 4),
        "payment_type": "one_time",
        "installment_count": 1,
        "first_installment_date": date(2026, 1, 4),
        "category_id": 3,
        "payment_method_id": 4,
        "created_at": datetime(2026, 1, 4),
    }


def test_income_entry_controller_maps_paging_commands_and_errors():
    from app.modules.income_entries import controller

    user_id = uuid4()
    response_data = {
        "id": 7,
        "description": "Entrada",
        "amount": Decimal("9.00"),
        "received_date": date(2026, 2, 4),
        "income_category_id": 2,
        "expense_category_id": None,
        "created_at": datetime(2026, 2, 4),
    }

    class Service:
        error = None

        def list(self, *args):
            self.list_args = args
            return [], 0

        def create(self, _user_id, command):
            self.command = command
            if self.error:
                raise self.error
            return response_data

        def update(self, _user_id, _entry_id, command):
            self.command = command
            if self.error:
                raise self.error
            return response_data

        def delete(self, *_args):
            if self.error:
                raise self.error

    service = Service()
    assert (
        controller.get_income_entries(
            2, 10, "2026-01", "2026-03", 2, None, "query", service, user_id
        ).total_pages
        == 0
    )
    assert service.list_args == (user_id, 2, 10, "2026-01", "2026-03", 2, None, "query")
    data = IncomeEntryCreate(
        description=" Entrada ",
        amount="9.00",
        received_date=date(2026, 2, 4),
        income_category_id=2,
    )
    assert controller.post_income_entry(data, service, user_id).id == 7
    assert service.command.description == "Entrada"
    assert controller.put_income_entry(7, data, service, user_id).id == 7
    assert controller.remove_income_entry(7, service, user_id).status_code == 204
    service.error = ResourceNotFoundError("ausente")
    with pytest.raises(HTTPException) as missing:
        controller.put_income_entry(7, data, service, user_id)
    assert missing.value.status_code == 404
    service.error = ValueError("inválido")
    with pytest.raises(HTTPException) as invalid:
        controller.post_income_entry(data, service, user_id)
    assert invalid.value.status_code == 422


def test_auth_controller_sets_cookies_and_maps_authentication_failures(
    auth_environment, monkeypatch
):
    from app.modules.auth import controller

    user_id = uuid4()
    result = AuthResult(
        user={"id": user_id, "email": "person@example.com", "name": None},
        access_token="access",
        refresh_token="refresh",
        expires_in=900,
    )

    class Service:
        def register(self, *_args):
            return result

        def login(self, *_args):
            raise AuthenticationRejectedError("credenciais inválidas", challenge=True)

        def current_user(self, _user_id):
            return result.user

        def refresh(self, token):
            assert token == "refresh"
            return result

        def logout(self, token):
            assert token == "refresh"

    service = Service()
    response = Response()
    registered = controller.register_account(
        RegistrationInput(email="person@example.com", password="long-password"),
        response,
        service,
    )
    assert registered.access_token == "access"
    assert "httponly" in response.headers["set-cookie"].lower()
    with pytest.raises(HTTPException) as rejected:
        controller.login_account(
            CredentialsInput(email="person@example.com", password="wrong"), Response(), service
        )
    assert rejected.value.status_code == 401
    assert rejected.value.headers["WWW-Authenticate"] == "Bearer"
    assert controller.me(user_id, service).email == "person@example.com"
    assert (
        controller.refresh_session(
            _request("expenses_refresh=refresh"), Response(), service
        ).access_token
        == "access"
    )
    assert (
        controller.logout(_request("expenses_refresh=refresh"), Response(), service).status_code
        == 204
    )
    monkeypatch.setattr(controller.GoogleOAuthService, "enabled", staticmethod(lambda: True))
    assert controller.google_status() == {"enabled": True}


def test_google_controller_maps_start_errors_and_callback_success(auth_environment, monkeypatch):
    from app.modules.auth import controller
    from app.modules.auth.oauth import OAuthStart

    monkeypatch.setattr(
        controller.GoogleOAuthService,
        "begin",
        staticmethod(
            lambda **_kwargs: OAuthStart(
                "https://google.test/auth", "signed-state", "a" * 24, "popup"
            )
        ),
    )
    redirect = controller.google_start("popup", "a" * 24, "/gastos")
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://google.test/auth"
    assert "expenses_google_oauth=signed-state" in redirect.headers["set-cookie"]

    from app.modules.auth.errors import GoogleLoginUnavailableError, OAuthModeError

    monkeypatch.setattr(
        controller.GoogleOAuthService,
        "begin",
        staticmethod(lambda **_kwargs: (_ for _ in ()).throw(GoogleLoginUnavailableError())),
    )
    with pytest.raises(HTTPException) as unavailable:
        controller.google_start()
    assert unavailable.value.status_code == 503
    monkeypatch.setattr(
        controller.GoogleOAuthService,
        "begin",
        staticmethod(lambda **_kwargs: (_ for _ in ()).throw(OAuthModeError())),
    )
    with pytest.raises(HTTPException) as invalid_mode:
        controller.google_start()
    assert invalid_mode.value.status_code == 400

    state = {
        "state": "matching-state",
        "request_id": "b" * 24,
        "mode": "redirect",
        "next": "/gastos?month=2026-01",
    }
    monkeypatch.setattr(controller, "read_oauth_state_cookie", lambda _cookie: state)

    class GoogleService:
        async def authenticate(self, code, saved_state):
            assert code == "code"
            assert saved_state is state
            return AuthResult(
                user={"id": uuid4(), "email": "person@gmail.com", "name": None},
                access_token="access",
                refresh_token="refresh",
                expires_in=900,
            )

    completion = asyncio.run(
        controller.google_callback(
            _request("expenses_google_oauth=valid"),
            "code",
            "matching-state",
            None,
            GoogleService(),
        )
    )
    assert completion.status_code == 303
    assert "result=success" in completion.headers["location"]
    assert "next=%2Fgastos%3Fmonth%3D2026-01" in completion.headers["location"]
    assert any(
        "expenses_refresh=refresh" in cookie for cookie in completion.headers.getlist("set-cookie")
    )


def test_google_callback_fails_closed_for_missing_or_invalid_state(auth_environment, monkeypatch):
    from app.modules.auth import controller

    missing_cookie = asyncio.run(controller.google_callback(_request(), state="state"))
    assert missing_cookie.status_code == 303
    assert "reason=expired" in missing_cookie.headers["location"]

    def reject_cookie(_cookie):
        raise OAuthAttemptError("expired")

    monkeypatch.setattr(controller, "read_oauth_state_cookie", reject_cookie)
    invalid_cookie = asyncio.run(
        controller.google_callback(_request("expenses_google_oauth=bad"), state="state")
    )
    assert invalid_cookie.status_code == 303
    assert "result=error" in invalid_cookie.headers["location"]


def test_auth_controller_maps_registration_conflict():
    from app.modules.auth import controller

    class Service:
        def register(self, *_args):
            raise AccountConflictError("conta existente")

    with pytest.raises(HTTPException) as conflict:
        controller.register_account(
            RegistrationInput(email="person@example.com", password="long-password"),
            Response(),
            Service(),
        )
    assert conflict.value.status_code == 409
