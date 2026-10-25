from datetime import date
from decimal import Decimal

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.payment_methods.model import PaymentMethod
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def create_references(database: Session) -> tuple[Category, PaymentMethod]:
    user_id = database.info["test_user_id"]
    category = Category(name="Alimentação", user_id=user_id)
    payment_method = PaymentMethod(name="Cartão de crédito", user_id=user_id)
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
        user_id=database.info["test_user_id"],
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


def test_expense_history_combines_charges_and_reimbursements_with_global_pagination(
    client: TestClient, database: Session
) -> None:
    category, payment_method = create_references(database)
    older_expense = create_expense(
        database, category.id, payment_method.id, "Compra", date(2026, 10, 3)
    )
    newer_expense = create_expense(
        database, category.id, payment_method.id, "Outra compra", date(2026, 10, 25)
    )
    database.query(ExpenseInstallment).filter_by(expense_id=older_expense.id).update(
        {"due_date": date(2026, 10, 8)}
    )
    database.query(ExpenseInstallment).filter_by(expense_id=newer_expense.id).update(
        {"due_date": date(2026, 10, 20)}
    )
    user_id = database.info["test_user_id"]
    reimbursement_category = IncomeCategory(
        name="Reembolso", user_id=user_id, requires_expense_category=True
    )
    salary_category = IncomeCategory(
        name="Salário", user_id=user_id, requires_expense_category=False
    )
    database.add_all([reimbursement_category, salary_category])
    database.flush()
    reimbursement = IncomeEntry(
        description="Devolução",
        amount=Decimal("10.00"),
        received_date=date(2026, 10, 15),
        income_category_id=reimbursement_category.id,
        expense_category_id=category.id,
        user_id=user_id,
    )
    database.add_all(
        [
            reimbursement,
            IncomeEntry(
                description="Salário",
                amount=Decimal("1000.00"),
                received_date=date(2026, 10, 28),
                income_category_id=salary_category.id,
                user_id=user_id,
            ),
        ]
    )
    database.commit()

    first_page = client.get("/expenses/history", params={"month": "2026-10", "page_size": 2})
    second_page = client.get(
        "/expenses/history", params={"month": "2026-10", "page_size": 2, "page": 2}
    )

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["total_pages"] == 2
    assert first_page.json()["gross_expense_amount"] == "51.00"
    assert first_page.json()["reimbursement_amount"] == "10.00"
    assert first_page.json()["net_expense_amount"] == "41.00"
    assert [(item["kind"], item["event_date"]) for item in first_page.json()["items"]] == [
        ("expense", "2026-10-20"),
        ("reimbursement", "2026-10-15"),
    ]
    assert [(item["kind"], item["event_date"]) for item in second_page.json()["items"]] == [
        ("expense", "2026-10-08"),
    ]
    payment_filtered = client.get(
        "/expenses/history",
        params={
            "month": "2026-10",
            "category_id": category.id,
            "payment_method_id": payment_method.id,
        },
    )
    reimbursement_search = client.get(
        "/expenses/history", params={"month": "2026-10", "search": "Devolução"}
    )
    assert payment_filtered.json()["total"] == 3
    assert [
        (item["kind"], item["description"]) for item in reimbursement_search.json()["items"]
    ] == [
        ("reimbursement", "Devolução"),
    ]


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
    expense = create_expense(database, category.id, payment_method.id, "Ônibus", date(2026, 10, 18))

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
