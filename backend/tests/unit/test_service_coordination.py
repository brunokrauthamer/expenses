from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from app.modules.categories.service import CategoryService
from app.modules.expenses.contracts import ExpenseCommand
from app.modules.expenses.import_contracts import ImportExpenseCommand
from app.modules.expenses.import_service import ExpenseImportService
from app.modules.expenses.service import ExpenseService
from app.modules.income_entries.contracts import IncomeEntryCommand
from app.modules.income_entries.repository import ReferenceState
from app.modules.income_entries.service import IncomeEntryService
from app.shared.catalog_repository import CatalogRecord
from app.shared.exceptions import DomainValidationError, DuplicateResourceError
from app.shared.reference_data_service import ReferenceDataService

pytestmark = pytest.mark.unit


class FakeUnitOfWork:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = False

    def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("commit failed")

    def rollback(self):
        self.rollbacks += 1


class FakeCatalogRepository:
    def __init__(self):
        self.records = {}
        self.next_id = 1
        self.duplicate = False

    def list(self, _user_id, _include_deleted=False):
        return list(self.records.values())

    def get(self, item_id, _user_id):
        return self.records.get(item_id)

    def name_exists(self, _user_id, _name, *, exclude_id=None):
        return self.duplicate or any(item_id != exclude_id for item_id in self.records)

    def create(self, _user_id, name, **attributes):
        record = CatalogRecord(
            self.next_id, name, None, attributes.get("requires_expense_category")
        )
        self.records[self.next_id] = record
        self.next_id += 1
        return record

    def update(self, item_id, _user_id, name, **attributes):
        record = CatalogRecord(
            item_id,
            name,
            None,
            attributes.get("requires_expense_category"),
        )
        self.records[item_id] = record
        return record

    def soft_delete(self, item_id, _user_id):
        record = self.records[item_id]
        deleted = CatalogRecord(record.id, record.name, datetime.now(timezone.utc))
        self.records[item_id] = deleted
        return deleted


def test_category_service_normalizes_name_and_commits_one_catalog_operation():
    repository = FakeCatalogRepository()
    unit_of_work = FakeUnitOfWork()
    service = CategoryService(repository, unit_of_work)

    created = service.create(uuid4(), "  Mercado  ")

    assert created.name == "Mercado"
    assert unit_of_work.commits == 1
    assert unit_of_work.rollbacks == 0


def test_category_service_surfaces_duplicate_and_rejects_deleted_item_edits():
    repository = FakeCatalogRepository()
    unit_of_work = FakeUnitOfWork()
    service = CategoryService(repository, unit_of_work)
    repository.duplicate = True
    with pytest.raises(DuplicateResourceError):
        service.create(uuid4(), "Casa")

    user_id = uuid4()
    repository.duplicate = False
    created = service.create(user_id, "Casa")
    service.delete(created.id, user_id)
    with pytest.raises(DomainValidationError, match="foi excluído"):
        service.update(created.id, user_id, "Outro nome")


def test_expense_service_builds_schedule_and_rolls_back_failed_writes():
    class ExpenseRepository:
        captured = None
        fail = False

        def create(self, user_id, command, amount, installments):
            self.captured = (user_id, command, amount, installments)
            if self.fail:
                raise RuntimeError("persistence failed")
            return {"id": 12}

    class ActiveCatalog:
        def get(self, item_id, _user_id):
            return CatalogRecord(item_id, "Ativo", None)

    user_id = uuid4()
    repository = ExpenseRepository()
    unit_of_work = FakeUnitOfWork()
    service = ExpenseService(repository, ActiveCatalog(), ActiveCatalog(), None, unit_of_work)
    command = ExpenseCommand(
        description="Compra",
        amount=Decimal("100.01"),
        amount_type="total",
        payment_type="installments",
        installment_count=3,
        expense_date=date(2024, 1, 31),
        first_installment_date=None,
        category_id=1,
        payment_method_id=2,
    )

    assert service.create(user_id, command) == {"id": 12}
    assert repository.captured[2] == Decimal("100.01")
    assert [item.amount for item in repository.captured[3]] == [
        Decimal("33.35"),
        Decimal("33.33"),
        Decimal("33.33"),
    ]
    assert unit_of_work.commits == 1

    repository.fail = True
    with pytest.raises(RuntimeError, match="persistence failed"):
        service.create(user_id, command)
    assert unit_of_work.rollbacks == 1


def test_expense_service_keeps_deleted_reference_when_editing_existing_expense():
    class ExpenseRepository:
        def get_state(self, _user_id, _expense_id):
            return type(
                "State",
                (),
                {
                    "amount": Decimal("50.00"),
                    "expense_date": date(2026, 1, 1),
                    "installment_count": 1,
                    "first_installment_date": date(2026, 1, 1),
                    "category_id": 1,
                    "payment_method_id": 2,
                },
            )()

        def update(self, *args):
            self.args = args
            return {"id": args[1]}

    class DeletedCatalog:
        def get(self, item_id, _user_id):
            return CatalogRecord(item_id, "Antigo", datetime.now(timezone.utc))

    repository = ExpenseRepository()
    service = ExpenseService(repository, DeletedCatalog(), DeletedCatalog(), None, FakeUnitOfWork())
    command = ExpenseCommand(
        description="Compra revisada",
        amount=Decimal("50.00"),
        amount_type="total",
        payment_type="one_time",
        installment_count=1,
        expense_date=date(2026, 1, 1),
        first_installment_date=None,
        category_id=1,
        payment_method_id=2,
    )

    assert service.update(uuid4(), 12, command) == {"id": 12}
    assert repository.args[-1] is False
    assert repository.args[-2] == []


def test_income_service_requires_expense_category_for_reimbursement():
    class IncomeRepository:
        def get_income_category(self, _category_id, _user_id):
            return ReferenceState(1, None, requires_expense_category=True)

        def get_expense_category(self, _category_id, _user_id):
            raise AssertionError("missing category must be rejected before lookup")

    unit_of_work = FakeUnitOfWork()
    service = IncomeEntryService(IncomeRepository(), unit_of_work)
    command = IncomeEntryCommand(
        description="Reembolso",
        amount=Decimal("10.00"),
        received_date=date(2026, 1, 2),
        income_category_id=1,
        expense_category_id=None,
    )

    with pytest.raises(DomainValidationError, match="Selecione a categoria"):
        service.create(uuid4(), command)
    assert unit_of_work.commits == 0


def test_reference_data_service_uses_one_transaction():
    class Repository:
        def initialize_for_user(self, _user_id):
            return True

    unit_of_work = FakeUnitOfWork()
    service = ReferenceDataService(Repository(), unit_of_work)

    assert service.initialize_for_user(uuid4()) is True
    assert (unit_of_work.commits, unit_of_work.rollbacks) == (1, 0)


def test_import_service_preserves_observed_values_and_builds_month_dates():
    class ImportRepository:
        saved = None

        def existing_source_keys(self, _user_id, _source_keys):
            return set()

        def active_catalog_ids(self, _user_id):
            return {"Mercado": 3}, {"PIX": 4}

        def save_all(self, *args):
            self.saved = args

    repository = ImportRepository()
    unit_of_work = FakeUnitOfWork()
    service = ExpenseImportService(repository, unit_of_work)
    command = ImportExpenseCommand(
        description="Compra",
        category_name="Mercado",
        payment_method_name="PIX",
        expense_date=date(2024, 1, 31),
        amounts=(Decimal("10.01"), Decimal("9.98")),
        source_keys=("jan|2",),
    )

    assert service.apply(uuid4(), [command]) == 1
    saved_installments = repository.saved[2][0]
    assert [(item.amount, item.due_date) for item in saved_installments] == [
        (Decimal("10.01"), date(2024, 1, 31)),
        (Decimal("9.98"), date(2024, 2, 29)),
    ]
    assert unit_of_work.commits == 1


def test_import_service_rejects_partial_duplicates_and_rolls_back_write_failure():
    class ImportRepository:
        existing = set()
        fail_save = False

        def existing_source_keys(self, _user_id, _source_keys):
            return self.existing

        def active_catalog_ids(self, _user_id):
            return {"Mercado": 3}, {"PIX": 4}

        def save_all(self, *_args):
            if self.fail_save:
                raise RuntimeError("save failed")

    repository = ImportRepository()
    unit_of_work = FakeUnitOfWork()
    service = ExpenseImportService(repository, unit_of_work)
    command = ImportExpenseCommand(
        description="Compra",
        category_name="Mercado",
        payment_method_name="PIX",
        expense_date=date(2026, 1, 1),
        amounts=(Decimal("10.00"),),
        source_keys=("jan|2", "fev|3"),
    )
    repository.existing = {"jan|2"}
    with pytest.raises(DomainValidationError, match="Importação parcial"):
        service.apply(uuid4(), [command])

    repository.existing = set()
    repository.fail_save = True
    with pytest.raises(RuntimeError, match="save failed"):
        service.apply(uuid4(), [command])
    assert unit_of_work.rollbacks == 1
