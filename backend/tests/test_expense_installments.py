from datetime import date
from decimal import Decimal

import pytest
from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.payment_methods.model import PaymentMethod
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def create_references(database: Session) -> tuple[Category, PaymentMethod]:
    user_id = database.info["test_user_id"]
    category = Category(name="Eletrônicos", user_id=user_id)
    payment_method = PaymentMethod(name="Cartão", user_id=user_id)
    database.add_all([category, payment_method])
    database.commit()
    return category, payment_method


def expense_payload(
    category_id: int,
    payment_method_id: int,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "description": "Notebook",
        "amount": "1200.00",
        "expense_date": "2026-10-18",
        "category_id": category_id,
        "payment_method_id": payment_method_id,
    }
    payload.update(overrides)
    return payload


def test_total_and_installment_amounts_generate_same_monthly_charges(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    total_response = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            amount_type="total",
            payment_type="installments",
            installment_count=6,
            first_installment_date="2026-11-10",
        ),
    )
    installment_response = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            description="Notebook por parcela",
            amount="200.00",
            amount_type="installment",
            payment_type="installments",
            installment_count=6,
            first_installment_date="2026-11-10",
        ),
    )

    assert total_response.status_code == installment_response.status_code == 201
    assert total_response.json()["total_amount"] == "1200.00"
    assert installment_response.json()["total_amount"] == "1200.00"
    assert total_response.json()["installment_count"] == 6
    for month in ("2026-11", "2026-12", "2027-04"):
        response = client.get("/expenses", params={"month": month, "search": "Notebook"})
        assert response.status_code == 200
        assert response.json()["total"] == 2
        assert all(item["amount_due"] == "200.00" for item in response.json()["items"])


def test_monthly_read_returns_only_the_charge_due_in_that_month(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    created = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            amount_type="total",
            payment_type="installments",
            installment_count=3,
            first_installment_date="2026-11-30",
        ),
    )
    expense_id = created.json()["id"]

    november = client.get("/expenses?month=2026-11").json()
    december = client.get("/expenses?month=2026-12").json()
    january = client.get("/expenses?month=2027-01").json()
    february = client.get("/expenses?month=2027-02").json()

    assert created.status_code == 201
    assert november["total"] == december["total"] == january["total"] == 1
    assert february["total"] == 0
    assert [
        november["items"][0]["due_date"],
        december["items"][0]["due_date"],
        january["items"][0]["due_date"],
    ] == ["2026-11-30", "2026-12-30", "2027-01-30"]
    for number, month_data in enumerate((november, december, january), start=1):
        item = month_data["items"][0]
        assert item["id"] == expense_id
        assert item["installment_number"] == number
        assert item["amount_due"] == "400.00"
        assert item["total_amount"] == "1200.00"
        assert item["installment_id"] > 0


def test_first_installment_receives_remainder_and_dates_keep_original_day(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    response = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            amount="100.01",
            amount_type="total",
            payment_type="installments",
            installment_count=3,
            expense_date="2026-01-01",
            first_installment_date="2026-01-31",
        ),
    )
    expense_id = response.json()["id"]
    installments = list(
        database.scalars(
            select(ExpenseInstallment)
            .where(ExpenseInstallment.expense_id == expense_id)
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    assert response.status_code == 201
    assert [row.amount for row in installments] == [
        Decimal("33.35"),
        Decimal("33.33"),
        Decimal("33.33"),
    ]
    assert [row.due_date for row in installments] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]
    assert sum((row.amount for row in installments), Decimal("0.00")) == Decimal("100.01")


def test_1300_over_seven_uses_185_71_for_later_installments(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    response = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            amount="1300.00",
            payment_type="installments",
            installment_count=7,
        ),
    )
    installments = list(
        database.scalars(
            select(ExpenseInstallment)
            .where(ExpenseInstallment.expense_id == response.json()["id"])
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    assert response.status_code == 201
    assert [row.amount for row in installments] == [
        Decimal("185.74"),
        Decimal("185.71"),
        Decimal("185.71"),
        Decimal("185.71"),
        Decimal("185.71"),
        Decimal("185.71"),
        Decimal("185.71"),
    ]
    assert sum((row.amount for row in installments), Decimal("0.00")) == Decimal("1300.00")


def test_installment_dates_handle_leap_years(client: TestClient, database: Session) -> None:
    category, payment_method = create_references(database)
    response = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            expense_date="2028-01-01",
            payment_type="installments",
            installment_count=3,
            first_installment_date="2028-01-31",
        ),
    )
    installments = list(
        database.scalars(
            select(ExpenseInstallment)
            .where(ExpenseInstallment.expense_id == response.json()["id"])
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    assert response.status_code == 201
    assert [row.due_date for row in installments] == [
        date(2028, 1, 31),
        date(2028, 2, 29),
        date(2028, 3, 31),
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"payment_type": "installments", "installment_count": 1},
        {"payment_type": "one_time", "installment_count": 2},
        {"payment_type": "one_time", "amount_type": "installment"},
        {"payment_type": "installments", "installment_count": 3, "amount": "0.02"},
        {"payment_type": "installments", "installment_count": 1201},
        {
            "payment_type": "installments",
            "installment_count": 2,
            "amount_type": "installment",
            "amount": "9999999999.99",
        },
        {
            "payment_type": "installments",
            "installment_count": 2,
            "first_installment_date": "2026-10-17",
        },
        {
            "payment_type": "installments",
            "installment_count": 2,
            "first_installment_date": "9999-12-31",
        },
    ],
)
def test_invalid_installment_combinations_return_422(
    client: TestClient,
    database: Session,
    overrides: dict[str, object],
) -> None:
    category, payment_method = create_references(database)
    response = client.post(
        "/expenses", json=expense_payload(category.id, payment_method.id, **overrides)
    )
    assert response.status_code == 422


def test_updating_description_preserves_the_installment_schedule(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    created = client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            payment_type="installments",
            installment_count=3,
            first_installment_date="2026-11-10",
        ),
    )
    expense_id = created.json()["id"]
    original_rows = list(
        database.scalars(
            select(ExpenseInstallment.id)
            .where(ExpenseInstallment.expense_id == expense_id)
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    updated = client.put(
        f"/expenses/{expense_id}",
        json=expense_payload(
            category.id,
            payment_method.id,
            description="Notebook atualizado",
            payment_type="installments",
            installment_count=3,
            first_installment_date="2026-11-10",
        ),
    )
    current_rows = list(
        database.scalars(
            select(ExpenseInstallment.id)
            .where(ExpenseInstallment.expense_id == expense_id)
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    assert updated.status_code == 200
    assert updated.json()["description"] == "Notebook atualizado"
    assert current_rows == original_rows


def test_updating_schedule_replaces_all_charges_atomically(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    created = client.post(
        "/expenses",
        json=expense_payload(
            category.id, payment_method.id, payment_type="installments", installment_count=6
        ),
    )
    expense_id = created.json()["id"]

    updated = client.put(
        f"/expenses/{expense_id}",
        json=expense_payload(
            category.id,
            payment_method.id,
            amount="1000.00",
            payment_type="installments",
            installment_count=2,
            first_installment_date="2026-12-01",
        ),
    )
    expense = database.get(Expense, expense_id)
    installments = list(
        database.scalars(
            select(ExpenseInstallment)
            .where(ExpenseInstallment.expense_id == expense_id)
            .order_by(ExpenseInstallment.installment_number)
        )
    )

    assert updated.status_code == 200
    assert updated.json()["total_amount"] == "1000.00"
    assert expense is not None and expense.installment_count == 2
    assert [row.amount for row in installments] == [Decimal("500.00"), Decimal("500.00")]
    assert [row.due_date for row in installments] == [date(2026, 12, 1), date(2027, 1, 1)]


def test_deleting_expense_cascades_to_all_installments(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    created = client.post(
        "/expenses",
        json=expense_payload(
            category.id, payment_method.id, payment_type="installments", installment_count=3
        ),
    )
    expense_id = created.json()["id"]
    assert database.query(ExpenseInstallment).filter_by(expense_id=expense_id).count() == 3

    deleted = client.delete(f"/expenses/{expense_id}")

    assert deleted.status_code == 204
    assert database.get(Expense, expense_id) is None
    assert database.query(ExpenseInstallment).filter_by(expense_id=expense_id).count() == 0


def test_pagination_counts_installments_and_one_time_expense_has_one_charge(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    client.post("/expenses", json=expense_payload(category.id, payment_method.id))
    client.post(
        "/expenses",
        json=expense_payload(
            category.id,
            payment_method.id,
            description="Celular",
            payment_type="installments",
            installment_count=3,
        ),
    )

    first_page = client.get("/expenses", params={"page": 1, "page_size": 2}).json()
    second_page = client.get("/expenses", params={"page": 2, "page_size": 2}).json()

    assert first_page["total"] == 4
    assert first_page["total_pages"] == 2
    assert len(first_page["items"]) == len(second_page["items"]) == 2
    one_time = client.get("/expenses", params={"search": "Notebook"}).json()
    assert one_time["total"] == 1
    assert one_time["items"][0]["payment_type"] == "one_time"
    assert one_time["items"][0]["installment_count"] == 1
