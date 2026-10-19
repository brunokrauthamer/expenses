from datetime import date
from decimal import Decimal
from pathlib import Path

from app.import_expenses import SourceRow, _prepare


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
