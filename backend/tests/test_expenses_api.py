from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense
from app.modules.expenses.model import ExpenseInstallment
from app.modules.payment_methods.model import PaymentMethod


def create_references(database: Session) -> tuple[Category, PaymentMethod]:
    category = Category(name="Alimentação")
    payment_method = PaymentMethod(name="Cartão de crédito")
    database.add_all([category, payment_method])
    database.commit()
    database.refresh(category)
    database.refresh(payment_method)
    return category, payment_method


def create_expense(
    database: Session,
    category_id: int,
    payment_method_id: int,
    description: str,
    expense_date: date,
) -> Expense:
    expense = Expense(
        description=description,
        amount=Decimal("25.50"),
        expense_date=expense_date,
        installment_count=1,
        first_installment_date=expense_date,
        category_id=category_id,
        payment_method_id=payment_method_id,
    )
    database.add(expense)
    database.flush()
    database.add(
        ExpenseInstallment(
            expense_id=expense.id,
            installment_number=1,
            amount=expense.amount,
            due_date=expense_date,
        )
    )
    database.commit()
    database.refresh(expense)
    return expense


def test_list_expenses_paginates_and_filters_by_month_and_search(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    matching_expense = create_expense(
        database,
        category.id,
        payment_method.id,
        "Almoço de sábado",
        date(2026, 10, 18),
    )
    create_expense(
        database,
        category.id,
        payment_method.id,
        "Cinema",
        date(2026, 11, 1),
    )

    for search in ("almoço", "alimentação", "cartão"):
        response = client.get(
            "/expenses",
            params={"month": "2026-10", "search": search, "page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["total_pages"] == 1
        assert response.json()["items"][0]["id"] == matching_expense.id


def test_recent_month_lists_every_purchase_paid_in_month_ordered_by_expense_date(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    earlier_purchase = create_expense(
        database, category.id, payment_method.id, "Compra anterior", date(2026, 10, 3)
    )
    later_purchase = create_expense(
        database, category.id, payment_method.id, "Compra posterior", date(2026, 10, 8)
    )
    outside_month = create_expense(
        database, category.id, payment_method.id, "Compra futura", date(2026, 11, 1)
    )
    # The payment dates deliberately disagree with the purchase date order.
    database.query(ExpenseInstallment).filter_by(expense_id=earlier_purchase.id).update(
        {"due_date": date(2026, 10, 31)}
    )
    database.query(ExpenseInstallment).filter_by(expense_id=later_purchase.id).update(
        {"due_date": date(2026, 10, 2), "amount": Decimal("25.00"), "installment_number": 2}
    )
    later_purchase.amount = Decimal("75.00")
    later_purchase.installment_count = 3
    database.commit()

    response = client.get("/expenses/month", params={"month": "2026-10"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [later_purchase.id, earlier_purchase.id]
    assert outside_month.id not in [item["id"] for item in response.json()]
    payment = response.json()[0]
    assert payment["installment_number"] == 2
    assert payment["installment_count"] == 3
    assert payment["installment_amount"] == "25.00"


def test_create_expense(client: TestClient, database: Session) -> None:
    category, payment_method = create_references(database)

    response = client.post(
        "/expenses",
        json={
            "description": "Padaria",
            "amount": "18.75",
            "expense_date": "2026-10-18",
            "category_id": category.id,
            "payment_method_id": payment_method.id,
        },
    )

    assert response.status_code == 201
    created = database.get(Expense, response.json()["id"])
    assert created is not None
    assert created.description == "Padaria"
    assert created.amount == Decimal("18.75")
    assert response.json()["total_amount"] == "18.75"
    assert response.json()["payment_type"] == "one_time"


def test_update_expense(client: TestClient, database: Session) -> None:
    category, payment_method = create_references(database)
    expense = create_expense(
        database, category.id, payment_method.id, "Mercado", date(2026, 10, 18)
    )

    response = client.put(
        f"/expenses/{expense.id}",
        json={
            "description": "Mercado semanal",
            "amount": "153.40",
            "expense_date": "2026-10-19",
            "category_id": category.id,
            "payment_method_id": payment_method.id,
        },
    )

    assert response.status_code == 200
    updated = database.get(Expense, expense.id)
    assert updated is not None
    assert updated.description == "Mercado semanal"
    assert updated.amount == Decimal("153.40")


def test_delete_expense(client: TestClient, database: Session) -> None:
    category, payment_method = create_references(database)
    expense = create_expense(
        database, category.id, payment_method.id, "Ônibus", date(2026, 10, 18)
    )

    response = client.delete(f"/expenses/{expense.id}")

    assert response.status_code == 204
    assert database.get(Expense, expense.id) is None
    assert database.query(ExpenseInstallment).filter_by(expense_id=expense.id).count() == 0


def test_create_expense_returns_not_found_for_invalid_references(client: TestClient) -> None:
    response = client.post(
        "/expenses",
        json={
            "description": "Teste",
            "amount": "10.00",
            "expense_date": "2026-10-18",
            "category_id": 999,
            "payment_method_id": 999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Categoria não encontrada."


def test_create_expense_rejects_blank_description(client: TestClient, database: Session) -> None:
    category, payment_method = create_references(database)

    response = client.post(
        "/expenses",
        json={
            "description": "   ",
            "amount": "10.00",
            "expense_date": "2026-10-18",
            "category_id": category.id,
            "payment_method_id": payment_method.id,
        },
    )

    assert response.status_code == 422
