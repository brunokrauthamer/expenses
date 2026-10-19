from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.payment_methods.model import PaymentMethod


def add_installment_purchase(
    database: Session,
    category: Category,
    payment_method: PaymentMethod,
    description: str,
    amount: Decimal,
    installment_amounts: list[tuple[date, Decimal]],
) -> Expense:
    expense = Expense(
        description=description,
        amount=amount,
        expense_date=date(2026, 1, 15),
        installment_count=len(installment_amounts),
        first_installment_date=installment_amounts[0][0],
        category_id=category.id,
        payment_method_id=payment_method.id,
    )
    database.add(expense)
    database.flush()
    database.add_all(
        ExpenseInstallment(
            expense_id=expense.id,
            installment_number=number,
            amount=installment_amount,
            due_date=due_date,
        )
        for number, (due_date, installment_amount) in enumerate(installment_amounts, start=1)
    )
    database.commit()
    database.refresh(expense)
    return expense


def create_references(database: Session) -> tuple[Category, Category, PaymentMethod, PaymentMethod]:
    groceries = Category(name="Mercado")
    leisure = Category(name="Lazer")
    pix = PaymentMethod(name="PIX")
    card = PaymentMethod(name="Cartão de Crédito")
    database.add_all([groceries, leisure, pix, card])
    database.commit()
    for reference in (groceries, leisure, pix, card):
        database.refresh(reference)
    return groceries, leisure, pix, card


def test_lookup_routes_return_sorted_database_values(client: TestClient, database: Session) -> None:
    groceries, leisure, _, _ = create_references(database)

    assert client.get("/categories").json() == [
        {"id": leisure.id, "name": "Lazer"},
        {"id": groceries.id, "name": "Mercado"},
    ]
    assert [item["name"] for item in client.get("/payment-methods").json()] == [
        "Cartão de Crédito",
        "PIX",
    ]


def test_recent_purchases_returns_one_item_per_purchase_in_registration_order(
    client: TestClient, database: Session
) -> None:
    groceries, _, pix, _ = create_references(database)
    old_purchase = add_installment_purchase(
        database,
        groceries,
        pix,
        "Compra antiga parcelada",
        Decimal("600.00"),
        [(date(2026, 2, 10), Decimal("200.00"))] * 3,
    )
    new_purchase = add_installment_purchase(
        database,
        groceries,
        pix,
        "Compra recente",
        Decimal("35.50"),
        [(date(2026, 6, 1), Decimal("35.50"))],
    )

    response = client.get("/expenses/recent", params={"limit": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == new_purchase.id
    assert response.json()[0]["id"] != old_purchase.id


def test_summary_aggregates_due_amounts_by_month_and_category(
    client: TestClient, database: Session
) -> None:
    groceries, leisure, pix, card = create_references(database)
    add_installment_purchase(
        database,
        groceries,
        pix,
        "Mercado parcelado",
        Decimal("600.00"),
        [
            (date(2026, 2, 10), Decimal("200.00")),
            (date(2026, 3, 10), Decimal("200.00")),
            (date(2026, 4, 10), Decimal("200.00")),
        ],
    )
    add_installment_purchase(
        database,
        leisure,
        card,
        "Cinema",
        Decimal("50.01"),
        [(date(2026, 4, 15), Decimal("50.01"))],
    )

    response = client.get(
        "/expenses/summary",
        params={"start_month": "2026-01", "end_month": "2026-06"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_amount_due": "650.01",
        "monthly_totals": [
            {"month": "2026-01", "amount_due": "0.00"},
            {"month": "2026-02", "amount_due": "200.00"},
            {"month": "2026-03", "amount_due": "200.00"},
            {"month": "2026-04", "amount_due": "250.01"},
            {"month": "2026-05", "amount_due": "0.00"},
            {"month": "2026-06", "amount_due": "0.00"},
        ],
        "category_totals": [
            {"category_id": groceries.id, "amount_due": "600.00"},
            {"category_id": leisure.id, "amount_due": "50.01"},
        ],
    }

    market_response = client.get(
        "/expenses/summary",
        params={
            "start_month": "2026-01",
            "end_month": "2026-06",
            "category_id": groceries.id,
            "payment_method_id": pix.id,
            "search": "mercado",
        },
    )
    assert market_response.status_code == 200
    assert market_response.json()["total_amount_due"] == "600.00"
    assert sum(
        Decimal(month["amount_due"])
        for month in market_response.json()["monthly_totals"]
    ) == Decimal("600.00")


def test_month_range_filters_are_validated_and_applied_to_installments(
    client: TestClient, database: Session
) -> None:
    groceries, leisure, pix, card = create_references(database)
    add_installment_purchase(
        database,
        groceries,
        pix,
        "Mercado",
        Decimal("30.00"),
        [(date(2026, 3, 10), Decimal("30.00"))],
    )
    out_of_range = add_installment_purchase(
        database,
        leisure,
        card,
        "Cinema",
        Decimal("40.00"),
        [(date(2026, 7, 10), Decimal("40.00"))],
    )

    response = client.get(
        "/expenses",
        params={"start_month": "2026-03", "end_month": "2026-03", "category_id": groceries.id},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1

    assert client.get(
        "/expenses/summary", params={"start_month": "2026-07", "end_month": "2026-03"}
    ).status_code == 422
    assert client.get(
        "/expenses/summary", params={"start_month": "2026-00", "end_month": "2026-01"}
    ).status_code == 422
    assert client.get(
        "/expenses/summary", params={"start_month": "2020-01", "end_month": "2030-01"}
    ).status_code == 422
    assert client.get("/expenses", params={"start_month": "2026-03"}).status_code == 422
    assert out_of_range.description == "Cinema"
