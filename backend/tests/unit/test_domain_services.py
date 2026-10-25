from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from app.modules.categories.service import CategoryService
from app.modules.expenses.contracts import ExpenseCommand, ExpenseState
from app.modules.expenses.service import ExpenseService
from app.modules.income_entries.contracts import IncomeEntryCommand, IncomeEntryState
from app.modules.income_entries.repository import ReferenceState
from app.modules.income_entries.service import IncomeCategoryService, IncomeEntryService
from app.modules.payment_methods.service import PaymentMethodService
from app.shared.catalog_repository import CatalogRecord
from app.shared.exceptions import (
    DomainValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)

pytestmark = pytest.mark.unit


class FakeUnitOfWork:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeCatalogRepository:
    def __init__(self):
        self.records: dict[int, CatalogRecord] = {}
        self.duplicate = False

    def list(self, _user_id, include_deleted=False):
        return [
            item for item in self.records.values() if include_deleted or item.deleted_at is None
        ]

    def get(self, item_id, _user_id):
        return self.records.get(item_id)

    def name_exists(self, _user_id, _name, *, exclude_id=None):
        return self.duplicate or any(item_id != exclude_id for item_id in self.records)

    def create(self, _user_id, name, **attributes):
        item_id = max(self.records, default=0) + 1
        item = CatalogRecord(item_id, name, None, attributes.get("requires_expense_category"))
        self.records[item_id] = item
        return item

    def update(self, item_id, _user_id, name, **attributes):
        item = CatalogRecord(item_id, name, None, attributes.get("requires_expense_category"))
        self.records[item_id] = item
        return item

    def soft_delete(self, item_id, _user_id):
        item = self.records[item_id]
        deleted = CatalogRecord(item.id, item.name, datetime.now(timezone.utc))
        self.records[item_id] = deleted
        return deleted


def _expense_command(**overrides):
    values = {
        "description": "Compra",
        "amount": Decimal("50.00"),
        "amount_type": "total",
        "payment_type": "one_time",
        "installment_count": 1,
        "expense_date": date(2026, 1, 1),
        "first_installment_date": None,
        "category_id": 1,
        "payment_method_id": 2,
    }
    return ExpenseCommand(**(values | overrides))


def _income_command(**overrides):
    values = {
        "description": "Entrada",
        "amount": Decimal("25.00"),
        "received_date": date(2026, 1, 5),
        "income_category_id": 3,
        "expense_category_id": None,
    }
    return IncomeEntryCommand(**(values | overrides))


def test_expense_summary_subtracts_reimbursements_and_fills_empty_months():
    class ExpenseRepository:
        def summary(self, *_args):
            return [
                ("2026-01", 2, Decimal("40.00")),
                ("2026-03", 2, Decimal("10.00")),
                ("2026-03", 1, Decimal("5.00")),
            ]

    class IncomeService:
        def reimbursement_totals(self, *_args):
            return (
                {"2026-01": Decimal("5.00"), "2026-03": Decimal("20.00")},
                {2: Decimal("8.00"), 4: Decimal("12.00")},
            )

    summary = ExpenseService(
        ExpenseRepository(), None, None, IncomeService(), FakeUnitOfWork()
    ).summary(uuid4(), "2026-01", "2026-03")

    assert summary["total_amount_due"] == Decimal("30.00")
    assert summary["gross_expense_amount"] == Decimal("55.00")
    assert summary["reimbursement_amount"] == Decimal("25.00")
    assert summary["monthly_totals"] == [
        {
            "month": "2026-01",
            "amount_due": Decimal("35.00"),
            "gross_expense_amount": Decimal("40.00"),
            "reimbursement_amount": Decimal("5.00"),
            "net_expense_amount": Decimal("35.00"),
        },
        {
            "month": "2026-02",
            "amount_due": Decimal("0.00"),
            "gross_expense_amount": Decimal("0.00"),
            "reimbursement_amount": Decimal("0.00"),
            "net_expense_amount": Decimal("0.00"),
        },
        {
            "month": "2026-03",
            "amount_due": Decimal("-5.00"),
            "gross_expense_amount": Decimal("15.00"),
            "reimbursement_amount": Decimal("20.00"),
            "net_expense_amount": Decimal("-5.00"),
        },
    ]
    assert summary["category_totals"] == [
        {
            "category_id": 2,
            "amount_due": Decimal("42.00"),
            "gross_expense_amount": Decimal("50.00"),
            "reimbursement_amount": Decimal("8.00"),
            "net_expense_amount": Decimal("42.00"),
        },
        {
            "category_id": 1,
            "amount_due": Decimal("5.00"),
            "gross_expense_amount": Decimal("5.00"),
            "reimbursement_amount": Decimal("0.00"),
            "net_expense_amount": Decimal("5.00"),
        },
        {
            "category_id": 4,
            "amount_due": Decimal("-12.00"),
            "gross_expense_amount": Decimal("0.00"),
            "reimbursement_amount": Decimal("12.00"),
            "net_expense_amount": Decimal("-12.00"),
        },
    ]


def test_expense_summary_excludes_reimbursements_when_filtered_by_payment_method():
    class ExpenseRepository:
        def summary(self, *_args):
            return [("2026-01", 1, Decimal("20.00"))]

    class IncomeService:
        def reimbursement_totals(self, *_args):
            raise AssertionError("payment method summaries omit reimbursements")

    summary = ExpenseService(
        ExpenseRepository(), None, None, IncomeService(), FakeUnitOfWork()
    ).summary(uuid4(), "2026-01", "2026-01", payment_method_id=7)

    assert summary["total_amount_due"] == Decimal("20.00")
    assert summary["reimbursement_amount"] == Decimal("0.00")


def test_expense_update_rebuilds_changed_schedule_and_delete_checks_ownership():
    class ExpenseRepository:
        state = ExpenseState(9, Decimal("50.00"), date(2026, 1, 1), 1, date(2026, 1, 1), 1, 2)

        def get_state(self, _user_id, _expense_id):
            return self.state

        def update(self, *_args):
            self.update_args = _args
            return {"id": 9}

        def delete(self, *_args):
            self.deleted = True

    class ActiveCatalog:
        def get(self, item_id, _user_id):
            return CatalogRecord(item_id, "Ativo", None)

    repository = ExpenseRepository()
    unit = FakeUnitOfWork()
    service = ExpenseService(repository, ActiveCatalog(), ActiveCatalog(), None, unit)
    updated = service.update(
        uuid4(),
        9,
        _expense_command(
            amount=Decimal("100.00"), installment_count=2, payment_type="installments"
        ),
    )
    assert updated == {"id": 9}
    assert repository.update_args[-1] is True
    assert len(repository.update_args[-2]) == 2
    service.delete(uuid4(), 9)
    assert repository.deleted is True
    assert unit.commits == 2


def test_expense_update_and_delete_report_missing_owned_expense():
    class MissingExpenseRepository:
        def get_state(self, *_args):
            return None

    service = ExpenseService(MissingExpenseRepository(), None, None, None, FakeUnitOfWork())
    with pytest.raises(ResourceNotFoundError, match="Despesa não encontrada"):
        service.update(uuid4(), 77, _expense_command())
    with pytest.raises(ResourceNotFoundError, match="Despesa não encontrada"):
        service.delete(uuid4(), 77)


@pytest.mark.parametrize("service_type", [CategoryService, PaymentMethodService])
def test_catalog_service_updates_and_soft_deletes_owned_record(service_type):
    repository = FakeCatalogRepository()
    unit = FakeUnitOfWork()
    service = service_type(repository, unit)
    user_id = uuid4()
    created = service.create(user_id, "Casa")

    updated = service.update(created.id, user_id, "Moradia")
    assert updated.name == "Moradia"
    service.delete(created.id, user_id)
    assert repository.records[created.id].deleted_at is not None
    assert unit.commits == 3


def test_catalog_service_rejects_duplicates_and_missing_records():
    repository = FakeCatalogRepository()
    service = CategoryService(repository, FakeUnitOfWork())
    repository.duplicate = True
    with pytest.raises(DuplicateResourceError):
        service.create(uuid4(), "Casa")

    with pytest.raises(ResourceNotFoundError, match="Cadastro não encontrado"):
        service.update(5, uuid4(), "Casa")
    with pytest.raises(ResourceNotFoundError, match="Cadastro não encontrado"):
        service.delete(5, uuid4())


def test_income_category_rule_cannot_change_after_first_entry_and_update_checks_duplicate():
    class IncomeCategoryRepository(FakeCatalogRepository):
        used = True

        def rule_is_used(self, _category_id, _user_id):
            return self.used

    repository = IncomeCategoryRepository()
    unit = FakeUnitOfWork()
    service = IncomeCategoryService(repository, unit)
    user_id = uuid4()
    created = service.create(user_id, "Reembolso", True)
    with pytest.raises(DomainValidationError, match="não pode mudar depois"):
        service.update(user_id, created.id, "Reembolso", False)
    repository.used = False
    repository.duplicate = True
    with pytest.raises(DuplicateResourceError):
        service.update(user_id, created.id, "Outro", True)


def test_income_entry_update_delete_and_reimbursement_filter_aggregation():
    class IncomeRepository:
        state = IncomeEntryState(4, 3, None)

        def get_state(self, _user_id, _entry_id):
            return self.state

        def get_income_category(self, category_id, _user_id):
            return ReferenceState(category_id, None, requires_expense_category=False)

        def get_expense_category(self, category_id, _user_id):
            return ReferenceState(category_id, None)

        def update(self, _user_id, entry_id, command):
            return {"id": entry_id, "description": command.description}

        def delete(self, *_args):
            return True

        def reimbursement_rows(self, *_args):
            return [(date(2026, 2, 4), 8, Decimal("12.00"))]

    unit = FakeUnitOfWork()
    service = IncomeEntryService(IncomeRepository(), unit)
    user_id = uuid4()
    assert service.update(user_id, 4, _income_command(description="Atualizada")) == {
        "id": 4,
        "description": "Atualizada",
    }
    service.delete(user_id, 4)
    assert service.reimbursement_totals(user_id, "2026-02", "2026-02") == (
        {"2026-02": Decimal("12.00")},
        {8: Decimal("12.00")},
    )
    assert unit.commits == 2


def test_income_entry_rejects_inactive_new_references_but_allows_existing_ones():
    class IncomeRepository:
        state = IncomeEntryState(4, 3, 8)

        def get_state(self, _user_id, _entry_id):
            return self.state

        def get_income_category(self, category_id, _user_id):
            return ReferenceState(category_id, datetime.now(timezone.utc), True)

        def get_expense_category(self, category_id, _user_id):
            return ReferenceState(category_id, datetime.now(timezone.utc))

        def update(self, _user_id, entry_id, _command):
            return {"id": entry_id}

    service = IncomeEntryService(IncomeRepository(), FakeUnitOfWork())
    user_id = uuid4()
    assert service.update(user_id, 4, _income_command(expense_category_id=8)) == {"id": 4}
    with pytest.raises(DomainValidationError, match="categoria de entrada ativa"):
        service.create(user_id, _income_command())
