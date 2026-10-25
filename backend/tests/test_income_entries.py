from datetime import date
from decimal import Decimal

from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseInstallment
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.payment_methods.model import PaymentMethod
from sqlalchemy.orm import Session


def test_reimbursement_requires_expense_category_and_salary_does_not(client, database: Session):
    user_id = database.info["test_user_id"]
    market = Category(name="Mercado", user_id=user_id)
    pix = PaymentMethod(name="PIX", user_id=user_id)
    salary = IncomeCategory(name="Salário", user_id=user_id, requires_expense_category=False)
    refund = IncomeCategory(name="Reembolso", user_id=user_id, requires_expense_category=True)
    database.add_all([market, pix, salary, refund])
    database.commit()
    category_response = client.get("/income-categories")
    assert category_response.status_code == 200
    assert {item["name"] for item in category_response.json()} == {"Salário", "Reembolso"}

    invalid = client.post(
        "/income-entries",
        json={
            "description": "Reembolso do churrasco",
            "amount": "200.00",
            "received_date": "2026-10-22",
            "income_category_id": refund.id,
        },
    )
    assert invalid.status_code == 422

    salary_response = client.post(
        "/income-entries",
        json={
            "description": "Salário de outubro",
            "amount": "8500.00",
            "received_date": "2026-10-05",
            "income_category_id": salary.id,
        },
    )
    assert salary_response.status_code == 201
    assert salary_response.json()["expense_category_id"] is None

    reimbursement = client.post(
        "/income-entries",
        json={
            "description": "Reembolso da Ana",
            "amount": "200.00",
            "received_date": "2026-10-22",
            "income_category_id": refund.id,
            "expense_category_id": market.id,
        },
    )
    assert reimbursement.status_code == 201


def test_summary_subtracts_reimbursements_by_expense_category(client, database: Session):
    user_id = database.info["test_user_id"]
    market = Category(name="Mercado", user_id=user_id)
    salary = IncomeCategory(name="Salário", user_id=user_id, requires_expense_category=False)
    refund = IncomeCategory(name="Reembolso", user_id=user_id, requires_expense_category=True)
    database.add_all([market, salary, refund])
    database.flush()
    pix = PaymentMethod(name="PIX", user_id=user_id)
    database.add(pix)
    database.flush()
    expense = Expense(
        description="Churrasco",
        amount=Decimal("600.00"),
        expense_date=date(2026, 10, 22),
        installment_count=1,
        first_installment_date=date(2026, 10, 22),
        category_id=market.id,
        payment_method_id=pix.id,
        user_id=user_id,
    )
    database.add(expense)
    database.flush()
    database.add(
        ExpenseInstallment(
            expense_id=expense.id,
            installment_number=1,
            amount=Decimal("600.00"),
            due_date=date(2026, 10, 22),
        )
    )
    database.add_all(
        [
            IncomeEntry(
                description="Devolução 1",
                amount=Decimal("200.00"),
                received_date=date(2026, 10, 22),
                income_category_id=refund.id,
                expense_category_id=market.id,
                user_id=user_id,
            ),
            IncomeEntry(
                description="Devolução 2",
                amount=Decimal("200.00"),
                received_date=date(2026, 10, 22),
                income_category_id=refund.id,
                expense_category_id=market.id,
                user_id=user_id,
            ),
            IncomeEntry(
                description="Salário",
                amount=Decimal("8500.00"),
                received_date=date(2026, 10, 5),
                income_category_id=salary.id,
                user_id=user_id,
            ),
        ]
    )
    database.commit()

    response = client.get(
        "/expenses/summary", params={"start_month": "2026-10", "end_month": "2026-10"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gross_expense_amount"] == "600.00"
    assert body["reimbursement_amount"] == "400.00"
    assert body["net_expense_amount"] == "200.00"
    assert body["category_totals"][0]["net_expense_amount"] == "200.00"


def test_income_entry_update_delete_and_list(client, database: Session):
    salary = IncomeCategory(
        name="Salário", user_id=database.info["test_user_id"], requires_expense_category=False
    )
    database.add(salary)
    database.commit()
    created = client.post(
        "/income-entries",
        json={
            "description": "Salário",
            "amount": "100.00",
            "received_date": "2026-10-05",
            "income_category_id": salary.id,
        },
    )
    entry_id = created.json()["id"]
    assert (
        client.get(
            "/income-entries", params={"start_month": "2026-10", "end_month": "2026-10"}
        ).json()["total"]
        == 1
    )
    updated = client.put(
        f"/income-entries/{entry_id}",
        json={
            "description": "Salário corrigido",
            "amount": "101.25",
            "received_date": "2026-10-05",
            "income_category_id": salary.id,
        },
    )
    assert updated.json()["amount"] == "101.25"
    assert client.delete(f"/income-entries/{entry_id}").status_code == 204
    assert client.get("/income-entries").json()["total"] == 0
