from datetime import date
from decimal import Decimal
from pathlib import Path

from app.import_expenses import PreparedExpense, SourceRow, _persist, _prepare
from app.modules.auth.model import User
from app.modules.categories.model import Category
from app.modules.expenses.model import Expense, ExpenseImportSource
from app.modules.payment_methods.model import PaymentMethod


MONTHS = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5}
CATEGORIES = ["Itens para casa", "Mercado", "Lazer", "Moradia", "Presentes"]


def source_row(
    month: str,
    number: int,
    count: int,
    amount: str,
    *,
    category: str = "Itens para casa",
    description: str = "Compra",
    row_number: int = 2,
) -> SourceRow:
    return SourceRow(
        path=Path(f"GASTOS CARTÃO {month}_2026.xlsx"),
        row_number=row_number,
        expense_date=date(2026, MONTHS[month], 1),
        installment_number=number,
        installment_count=count,
        payment_method="BTG",
        category=category,
        description=description,
        amount=Decimal(amount),
    )


def test_new_installment_uses_first_and_second_amount_even_when_category_changes() -> None:
    prepared, issues, estimates, ignored_later = _prepare(
        [
            source_row("fev", 1, 3, "10.01"),
            source_row("mar", 2, 3, "10.00", category="Mercado"),
        ],
        CATEGORIES,
        date(2026, 1, 1),
    )

    assert not issues
    assert estimates == ignored_later == 0
    assert len(prepared) == 1
    assert prepared[0].description == "Compra"
    assert prepared[0].category_name == "Itens para casa"
    assert prepared[0].expense_date == date(2026, 2, 1)
    assert prepared[0].amounts == (
        Decimal("10.01"), Decimal("10.00"), Decimal("10.00")
    )
    assert prepared[0].total == Decimal("30.01")


def test_oldest_sheet_in_progress_installments_become_separate_expenses() -> None:
    prepared, issues, estimates, ignored_later = _prepare(
        [
            source_row("jan", 5, 6, "4.99"),
            source_row("fev", 6, 6, "4.99"),
        ],
        CATEGORIES,
        date(2026, 1, 1),
    )

    assert not issues
    assert estimates == ignored_later == 0
    assert [item.description for item in prepared] == [
        "Compra, parcela 5", "Compra, parcela 6"
    ]
    assert all(len(item.amounts) == 1 for item in prepared)
    assert [item.expense_date for item in prepared] == [
        date(2026, 1, 1), date(2026, 2, 1)
    ]


def test_orphan_later_installment_is_ignored_outside_oldest_sheet() -> None:
    prepared, issues, estimates, ignored_later = _prepare(
        [source_row("abr", 3, 6, "4.99")],
        CATEGORIES,
        date(2026, 1, 1),
    )

    assert not issues
    assert not prepared
    assert estimates == 0
    assert ignored_later == 1


def test_first_installment_alone_estimates_total_from_installment_value() -> None:
    prepared, issues, estimates, ignored_later = _prepare(
        [source_row("mai", 1, 4, "12.34")],
        CATEGORIES,
        date(2026, 1, 1),
    )

    assert not issues
    assert estimates == 1
    assert ignored_later == 0
    assert len(prepared) == 1
    assert prepared[0].amounts == (Decimal("12.34"),) * 4
    assert prepared[0].total == Decimal("49.36")


def test_import_deduplication_is_scoped_to_each_user(client, database) -> None:
    first_user_id = database.info["test_user_id"]
    second_user = User(email_ciphertext=b"second", email_lookup="second-import-user")
    database.add(second_user)
    database.flush()
    for user_id in (first_user_id, second_user.id):
        database.add_all([
            Category(name="Mercado", user_id=user_id),
            PaymentMethod(name="PIX", user_id=user_id),
        ])
    database.commit()

    row = SourceRow(
        path=Path("GASTOS CARTÃO jan_2026.xlsx"), row_number=2,
        expense_date=date(2026, 1, 1), installment_number=None, installment_count=None,
        payment_method="PIX", category="Mercado", description="Compra importada",
        amount=Decimal("12.50"),
    )
    prepared = PreparedExpense(
        description="Compra importada", category_name="Mercado", payment_method_name="PIX",
        expense_date=date(2026, 1, 1), amounts=(Decimal("12.50"),), sources=(row,),
    )
    assert _persist(database, [prepared], first_user_id) == 1
    assert _persist(database, [prepared], first_user_id) == 0
    assert _persist(database, [prepared], second_user.id) == 1
    assert database.query(Expense).count() == 2
    assert database.query(ExpenseImportSource).count() == 2
    assert {item.user_id for item in database.query(Expense).all()} == {first_user_id, second_user.id}
