from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import app
from app.modules.auth.model import User
from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseImportSource, ExpenseInstallment
from app.modules.income_entries.model import IncomeCategory, IncomeEntry
from app.modules.payment_methods.model import PaymentMethod
from app.shared.auth import get_current_user
from app.shared.reference_data import initialize_user_reference_data


def _owner(database: Session) -> User:
    return database.get(User, database.info["test_user_id"])


def _category(database: Session, name: str, user_id=None) -> Category:
    item = Category(name=name, user_id=user_id or database.info["test_user_id"])
    database.add(item)
    database.commit()
    database.refresh(item)
    return item


def _method(database: Session, name: str, user_id=None) -> PaymentMethod:
    item = PaymentMethod(name=name, user_id=user_id or database.info["test_user_id"])
    database.add(item)
    database.commit()
    database.refresh(item)
    return item


def test_financial_queries_and_ids_are_scoped_to_the_authenticated_user(client: TestClient, database: Session):
    first_user = _owner(database)
    second_user = User(email_ciphertext=b"second", email_lookup="second-user")
    database.add(second_user)
    database.commit()
    category_a = _category(database, "Mercado", first_user.id)
    method_a = _method(database, "Cartão", first_user.id)
    category_b = _category(database, "Mercado", second_user.id)
    method_b = _method(database, "Cartão", second_user.id)

    created = client.post("/expenses", json={
        "description": "Despesa da primeira conta", "amount": "42.00",
        "expense_date": "2026-10-22", "category_id": category_a.id,
        "payment_method_id": method_a.id,
    })
    assert created.status_code == 201
    expense_id = created.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: second_user
    assert client.get("/categories").json() == [{"id": category_b.id, "name": "Mercado", "deleted_at": None}]
    assert client.get("/payment-methods").json() == [{"id": method_b.id, "name": "Cartão", "deleted_at": None}]
    assert client.get("/expenses/month", params={"month": "2026-10"}).json() == []
    assert client.get("/expenses/history", params={"month": "2026-10"}).json()["total"] == 0
    assert client.get("/income-entries").json()["total"] == 0
    assert client.get("/expenses/summary", params={"start_month": "2026-10", "end_month": "2026-10"}).json()["gross_expense_amount"] == "0.00"
    assert client.put(f"/expenses/{expense_id}", json={
        "description": "Acesso alheio", "amount": "42.00", "expense_date": "2026-10-22",
        "category_id": category_b.id, "payment_method_id": method_b.id,
    }).status_code == 404
    assert client.delete(f"/expenses/{expense_id}").status_code == 404
    assert client.post("/expenses", json={
        "description": "Vínculo de outra conta", "amount": "10.00", "expense_date": "2026-10-22",
        "category_id": category_a.id, "payment_method_id": method_b.id,
    }).status_code == 404
    assert client.post("/expenses", json={
        "description": "Proprietário no corpo", "amount": "10.00", "expense_date": "2026-10-22",
        "category_id": category_b.id, "payment_method_id": method_b.id, "user_id": str(second_user.id),
    }).status_code == 422


def test_installments_history_reimbursements_and_pagination_are_scoped_to_each_user(
    client: TestClient, database: Session,
):
    first_user = _owner(database)
    second_user = User(email_ciphertext=b"second", email_lookup="second-finance-user")
    database.add(second_user)
    database.commit()

    category_a = _category(database, "Moradia", first_user.id)
    method_a = _method(database, "PIX", first_user.id)
    reimbursement_a = IncomeCategory(
        name="DevoluÃ§Ã£o", requires_expense_category=True, user_id=first_user.id,
    )
    database.add(reimbursement_a)
    database.commit()
    expense_a = client.post("/expenses", json={
        "description": "Parcela privada A", "amount": "120.00", "amount_type": "total",
        "payment_type": "installments", "installment_count": 2,
        "expense_date": "2026-10-10", "first_installment_date": "2026-10-15",
        "category_id": category_a.id, "payment_method_id": method_a.id,
    })
    assert expense_a.status_code == 201
    reimbursement_entry_a = client.post("/income-entries", json={
        "description": "Reembolso privado A", "amount": "10.00", "received_date": "2026-10-20",
        "income_category_id": reimbursement_a.id, "expense_category_id": category_a.id,
    })
    assert reimbursement_entry_a.status_code == 201

    category_b = _category(database, "Moradia", second_user.id)
    method_b = _method(database, "PIX", second_user.id)
    income_b = IncomeCategory(
        name="Outras entradas", requires_expense_category=False, user_id=second_user.id,
    )
    database.add(income_b)
    database.commit()
    app.dependency_overrides[get_current_user] = lambda: second_user
    expense_b = client.post("/expenses", json={
        "description": "Parcela privada B", "amount": "900.00", "amount_type": "total",
        "payment_type": "installments", "installment_count": 2,
        "expense_date": "2026-10-10", "first_installment_date": "2026-10-15",
        "category_id": category_b.id, "payment_method_id": method_b.id,
    })
    assert expense_b.status_code == 201
    income_entry_b = client.post("/income-entries", json={
        "description": "Entrada privada B", "amount": "900.00", "received_date": "2026-10-20",
        "income_category_id": income_b.id,
    })
    assert income_entry_b.status_code == 201

    app.dependency_overrides[get_current_user] = lambda: first_user
    paged = client.get("/expenses", params={"start_month": "2026-10", "end_month": "2026-11", "page": 1, "page_size": 1}).json()
    assert paged["total"] == 2
    assert paged["total_pages"] == 2
    assert paged["items"][0]["description"] == "Parcela privada A"
    assert client.get("/expenses", params={"search": "privada B"}).json()["total"] == 0
    assert {item["description"] for item in client.get("/expenses/recent").json()} == {"Parcela privada A"}
    assert {item["description"] for item in client.get("/expenses/month", params={"month": "2026-10"}).json()} == {"Parcela privada A"}

    history_a = client.get("/expenses/history", params={"month": "2026-10"}).json()
    assert history_a["total"] == 2
    assert {item["description"] for item in history_a["items"]} == {"Parcela privada A", "Reembolso privado A"}
    assert history_a["gross_expense_amount"] == "60.00"
    assert history_a["reimbursement_amount"] == "10.00"
    assert history_a["net_expense_amount"] == "50.00"
    summary_a = client.get("/expenses/summary", params={"start_month": "2026-10", "end_month": "2026-11"}).json()
    assert summary_a["gross_expense_amount"] == "120.00"
    assert summary_a["reimbursement_amount"] == "10.00"
    assert summary_a["net_expense_amount"] == "110.00"
    assert [month["gross_expense_amount"] for month in summary_a["monthly_totals"]] == ["60.00", "60.00"]
    income_page_a = client.get("/income-entries", params={"start_month": "2026-10", "end_month": "2026-11"}).json()
    assert income_page_a["total"] == 1
    assert income_page_a["items"][0]["description"] == "Reembolso privado A"
    assert client.put(f"/income-entries/{income_entry_b.json()['id']}", json={
        "description": "Alteração cruzada", "amount": "900.00", "received_date": "2026-10-20",
        "income_category_id": reimbursement_a.id, "expense_category_id": category_a.id,
    }).status_code == 404
    assert client.delete(f"/income-entries/{income_entry_b.json()['id']}").status_code == 404
    assert client.post("/income-entries", json={
        "description": "Referência cruzada", "amount": "5.00", "received_date": "2026-10-20",
        "income_category_id": reimbursement_a.id, "expense_category_id": category_b.id,
    }).status_code == 404

    app.dependency_overrides[get_current_user] = lambda: second_user
    history_b = client.get("/expenses/history", params={"month": "2026-10"}).json()
    assert history_b["gross_expense_amount"] == "450.00"
    assert history_b["reimbursement_amount"] == "0.00"
    assert history_b["net_expense_amount"] == "450.00"
    assert {item["description"] for item in history_b["items"]} == {"Parcela privada B"}
    assert client.get("/income-entries").json()["items"][0]["description"] == "Entrada privada B"
    assert client.put(f"/expenses/{expense_a.json()['id']}", json={
        "description": "Alteração cruzada", "amount": "120.00", "amount_type": "total",
        "payment_type": "installments", "installment_count": 2,
        "expense_date": "2026-10-10", "first_installment_date": "2026-10-15",
        "category_id": category_b.id, "payment_method_id": method_b.id,
    }).status_code == 404
    assert client.delete(f"/expenses/{expense_a.json()['id']}").status_code == 404
    assert client.post("/income-entries", json={
        "description": "Proprietário escolhido", "amount": "5.00", "received_date": "2026-10-20",
        "income_category_id": income_b.id, "user_id": str(second_user.id),
    }).status_code == 422


def test_archived_payment_method_preserves_future_installments_and_totals(client: TestClient, database: Session):
    category = _category(database, "Casa")
    method = _method(database, "CartÃ£o")
    created = client.post("/expenses", json={
        "description": "Parcelas futuras", "amount": "90.00", "amount_type": "total",
        "payment_type": "installments", "installment_count": 3,
        "expense_date": "2026-10-10", "first_installment_date": "2026-10-15",
        "category_id": category.id, "payment_method_id": method.id,
    })
    assert created.status_code == 201
    before = client.get("/expenses/summary", params={"start_month": "2026-10", "end_month": "2026-12"}).json()
    assert before["gross_expense_amount"] == "90.00"

    assert client.delete(f"/payment-methods/{method.id}").status_code == 204
    assert client.delete(f"/payment-methods/{method.id}").status_code == 204
    assert all(item["id"] != method.id for item in client.get("/payment-methods").json())
    assert client.post("/expenses", json={
        "description": "Novo uso inválido", "amount": "5.00", "expense_date": "2026-10-22",
        "category_id": category.id, "payment_method_id": method.id,
    }).status_code == 422
    for month in ("2026-11", "2026-12"):
        future = client.get("/expenses/month", params={"month": month}).json()
        assert len(future) == 1
        assert future[0]["description"] == "Parcelas futuras"
        assert future[0]["payment_method_name"] == "CartÃ£o"
        assert future[0]["payment_method_deleted"] is True
    after = client.get("/expenses/summary", params={"start_month": "2026-10", "end_month": "2026-12"}).json()
    assert after == before


@pytest.mark.parametrize(
    ("endpoint", "create_extra", "update_extra"),
    [
        ("categories", {}, {}),
        ("payment-methods", {}, {}),
        (
            "income-categories",
            {"requires_expense_category": True},
            {"requires_expense_category": True},
        ),
    ],
)
def test_catalog_api_normalizes_names_scopes_ids_and_reuses_archived_names(
    client: TestClient, database: Session, endpoint: str, create_extra: dict, update_extra: dict,
):
    first_user = _owner(database)
    second_user = User(email_ciphertext=b"second", email_lookup=f"second-{endpoint}")
    database.add(second_user)
    database.commit()
    first_body = {"name": "  QA Compra  ", **create_extra}
    duplicate_body = {"name": "qa compra", **create_extra}
    first_item = client.post(f"/{endpoint}", json=first_body)
    assert first_item.status_code == 201
    first_id = first_item.json()["id"]
    assert first_item.json()["name"] == "QA Compra"
    assert client.post(f"/{endpoint}", json=duplicate_body).status_code == 409
    assert client.post(f"/{endpoint}", json={"name": "   ", **create_extra}).status_code == 422

    app.dependency_overrides[get_current_user] = lambda: second_user
    second_item = client.post(f"/{endpoint}", json=first_body)
    assert second_item.status_code == 201
    second_id = second_item.json()["id"]
    assert second_id != first_id
    assert client.put(f"/{endpoint}/{first_id}", json={"name": "Alteração cruzada", **update_extra}).status_code == 404
    assert client.delete(f"/{endpoint}/{first_id}").status_code == 404
    assert [item["id"] for item in client.get(f"/{endpoint}").json()] == [second_id]

    app.dependency_overrides[get_current_user] = lambda: first_user
    assert client.put(f"/{endpoint}/{second_id}", json={"name": "Alteração cruzada", **update_extra}).status_code == 404
    assert client.delete(f"/{endpoint}/{second_id}").status_code == 404
    renamed = client.put(f"/{endpoint}/{first_id}", json={"name": "  Casa Nova  ", **update_extra})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Casa Nova"
    assert client.put(f"/{endpoint}/{first_id}", json={"name": "Casa Nova", **update_extra}).status_code == 200
    assert client.delete(f"/{endpoint}/{first_id}").status_code == 204
    assert client.delete(f"/{endpoint}/{first_id}").status_code == 204
    assert client.put(f"/{endpoint}/999999", json={"name": "Inexistente", **update_extra}).status_code == 404
    assert client.delete(f"/{endpoint}/999999").status_code == 404
    assert all(item["id"] != first_id for item in client.get(f"/{endpoint}").json())

    reused_body = {"name": "Casa Nova", **create_extra}
    reused = client.post(f"/{endpoint}", json=reused_body)
    assert reused.status_code == 201
    assert reused.json()["id"] != first_id
    all_items = client.get(f"/{endpoint}?include_deleted=true").json()
    same_name_items = [item for item in all_items if item["name"] == "Casa Nova"]
    assert {item["id"] for item in same_name_items} == {first_id, reused.json()["id"]}
    assert next(item for item in same_name_items if item["id"] == first_id)["deleted_at"] is not None


def test_composite_foreign_keys_reject_cross_user_reference_links(client: TestClient, database: Session):
    first_user = _owner(database)
    second_user = User(email_ciphertext=b"second", email_lookup="second-user")
    database.add(second_user)
    database.commit()
    category = _category(database, "Casa", first_user.id)
    foreign_method = _method(database, "PIX", second_user.id)
    database.add(Expense(
        description="Vínculo inválido", amount=Decimal("12.00"), expense_date=date(2026, 10, 22),
        installment_count=1, first_installment_date=date(2026, 10, 22), category_id=category.id,
        payment_method_id=foreign_method.id, user_id=first_user.id,
    ))
    with pytest.raises(IntegrityError):
        database.commit()
    database.rollback()

    own_income_category = IncomeCategory(
        name="Reembolso", requires_expense_category=True, user_id=first_user.id,
    )
    foreign_category = _category(database, "Conta B", second_user.id)
    own_method = _method(database, "PIX", first_user.id)
    database.add(own_income_category)
    database.commit()
    database.add(IncomeEntry(
        description="Referência cruzada", amount=Decimal("5.00"), received_date=date(2026, 10, 22),
        income_category_id=own_income_category.id, expense_category_id=foreign_category.id,
        user_id=first_user.id,
    ))
    with pytest.raises(IntegrityError):
        database.commit()
    database.rollback()

    owned_expense = Expense(
        description="Origem A", amount=Decimal("12.00"), expense_date=date(2026, 10, 22),
        installment_count=1, first_installment_date=date(2026, 10, 22), category_id=category.id,
        payment_method_id=own_method.id, user_id=first_user.id,
    )
    database.add(owned_expense)
    database.commit()
    database.add(ExpenseImportSource(
        source_key="another-account-source", expense_id=owned_expense.id, user_id=second_user.id,
    ))
    with pytest.raises(IntegrityError):
        database.commit()
    database.rollback()


def test_reference_crud_normalizes_names_and_keeps_archived_history(client: TestClient, database: Session):
    category = _category(database, "Mercado")
    method = _method(database, "PIX")
    expense = client.post("/expenses", json={
        "description": "Compra mantida", "amount": "80.00", "expense_date": "2026-10-22",
        "category_id": category.id, "payment_method_id": method.id,
    })
    assert expense.status_code == 201

    duplicate = client.post("/categories", json={"name": "  mercado  "})
    assert duplicate.status_code == 409
    renamed = client.put(f"/categories/{category.id}", json={"name": "  Casa  "})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Casa"
    assert client.delete(f"/categories/{category.id}").status_code == 204
    assert client.delete(f"/categories/{category.id}").status_code == 204
    assert all(item["id"] != category.id for item in client.get("/categories").json())

    history = client.get("/expenses/history", params={"month": "2026-10"}).json()
    row = history["items"][0]
    assert row["category_name"] == "Casa"
    assert row["category_deleted"] is True
    assert history["gross_expense_amount"] == "80.00"
    assert client.post("/expenses", json={
        "description": "Nova despesa inválida", "amount": "5.00", "expense_date": "2026-10-22",
        "category_id": category.id, "payment_method_id": method.id,
    }).status_code == 422

    reused_name = client.post("/categories", json={"name": "Casa"})
    assert reused_name.status_code == 201
    assert reused_name.json()["id"] != category.id
    references = client.get("/categories?include_deleted=true").json()
    assert len([item for item in references if item["name"] == "Casa"]) == 2
    assert {item["id"] for item in references if item["name"] == "Casa"} == {category.id, reused_name.json()["id"]}


def test_deleted_reference_can_stay_on_its_old_record_but_cannot_be_reused(client: TestClient, database: Session):
    category = _category(database, "Casa")
    method = _method(database, "PIX")
    created = client.post("/expenses", json={
        "description": "Registro antigo", "amount": "20.00", "expense_date": "2026-10-22",
        "category_id": category.id, "payment_method_id": method.id,
    }).json()
    client.delete(f"/categories/{category.id}")
    retained = client.put(f"/expenses/{created['id']}", json={
        "description": "Registro editado", "amount": "20.00", "expense_date": "2026-10-22",
        "category_id": category.id, "payment_method_id": method.id,
    })
    assert retained.status_code == 200
    other_archived = _category(database, "Outra antiga")
    client.delete(f"/categories/{other_archived.id}")
    rejected = client.put(f"/expenses/{created['id']}", json={
        "description": "Troca inválida", "amount": "20.00", "expense_date": "2026-10-22",
        "category_id": other_archived.id, "payment_method_id": method.id,
    })
    assert rejected.status_code == 422


def test_income_category_reimbursement_rule_and_archived_reference_are_preserved(client: TestClient, database: Session):
    category = _category(database, "Mercado")
    reimbursement = client.post("/income-categories", json={"name": "Devolução", "requires_expense_category": True})
    assert reimbursement.status_code == 201
    category_id = reimbursement.json()["id"]
    entry = client.post("/income-entries", json={
        "description": "Devolução recebida", "amount": "15.00", "received_date": "2026-10-22",
        "income_category_id": category_id, "expense_category_id": category.id,
    })
    assert entry.status_code == 201
    assert client.put(f"/income-categories/{category_id}", json={
        "name": "Devolução", "requires_expense_category": False,
    }).status_code == 422
    assert client.delete(f"/income-categories/{category_id}").status_code == 204
    assert client.post("/income-entries", json={
        "description": "Uso de categoria excluída", "amount": "15.00", "received_date": "2026-10-22",
        "income_category_id": category_id, "expense_category_id": category.id,
    }).status_code == 422
    listed = client.get("/income-entries").json()["items"][0]
    assert listed["income_category_name"] == "Devolução"
    assert listed["income_category_deleted"] is True
    updated = client.put(f"/income-entries/{entry.json()['id']}", json={
        "description": "Devolução corrigida", "amount": "15.00", "received_date": "2026-10-22",
        "income_category_id": category_id, "expense_category_id": category.id,
    })
    assert updated.status_code == 200
