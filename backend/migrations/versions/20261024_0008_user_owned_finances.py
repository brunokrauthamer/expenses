"""scope financial data to users and add personal reference catalogs

Revision ID: 20261024_0008
Revises: 20261022_0007
Create Date: 2026-10-24
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0008"
down_revision: str | None = "20261022_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REFERENCE_DEFAULTS = {
    "categories": (
        "Mercado", "Lazer", "Restaurante", "Transporte", "Carro", "Presentes",
        "Faxina", "Serviços", "Cuidados Pessoais", "Saúde", "Viagem", "Boletos",
        "Moradia", "Itens para casa",
    ),
    "payment_methods": ("PIX", "Cartão de Crédito"),
    "income_categories": (("Salário", False), ("Reembolso", True)),
}


def _table_count(connection, table: str) -> int:
    return int(connection.scalar(sa.text(f'SELECT count(*) FROM "{table}"')) or 0)


def _financial_snapshot(connection) -> dict[str, tuple]:
    snapshot = {}
    for table, amount_column in (
        ("expenses", "amount"),
        ("expense_installments", "amount"),
        ("income_entries", "amount"),
        ("expense_import_sources", None),
    ):
        amount = f", coalesce(sum({amount_column}), 0)" if amount_column else ""
        row = connection.execute(sa.text(
            f'SELECT count(*), coalesce(sum(id), 0){amount} FROM "{table}"'
        )).one()
        snapshot[table] = tuple(row)
    return snapshot


def _assert_owned_links(connection) -> None:
    statements = (
        ("expenses", "SELECT count(*) FROM expenses e LEFT JOIN categories c ON c.id = e.category_id WHERE c.id IS NULL OR c.user_id <> e.user_id"),
        ("expenses", "SELECT count(*) FROM expenses e LEFT JOIN payment_methods p ON p.id = e.payment_method_id WHERE p.id IS NULL OR p.user_id <> e.user_id"),
        ("income_entries", "SELECT count(*) FROM income_entries i LEFT JOIN income_categories c ON c.id = i.income_category_id WHERE c.id IS NULL OR c.user_id <> i.user_id"),
        ("income_entries", "SELECT count(*) FROM income_entries i JOIN categories c ON c.id = i.expense_category_id WHERE c.user_id <> i.user_id"),
        ("expense_import_sources", "SELECT count(*) FROM expense_import_sources s LEFT JOIN expenses e ON e.id = s.expense_id WHERE e.id IS NULL OR e.user_id <> s.user_id"),
    )
    for table, statement in statements:
        invalid = int(connection.scalar(sa.text(statement)) or 0)
        if invalid:
            raise RuntimeError(f"Migração interrompida: {table} contém {invalid} vínculo(s) sem o mesmo proprietário.")


def _assert_no_active_name_conflicts(connection, table: str) -> None:
    conflict = connection.execute(sa.text(
        f'''SELECT lower(trim(name)) AS normalized, array_agg(id ORDER BY id) AS ids
            FROM "{table}" GROUP BY lower(trim(name)) HAVING count(*) > 1 LIMIT 1'''
    )).first()
    if conflict:
        raise RuntimeError(
            f"Migração interrompida: {table} tem nomes duplicados após remover espaços e ignorar caixa "
            f"({conflict.normalized!r}, IDs {conflict.ids}). Resolva os registros manualmente e repita."
        )


def _drop_unique_constraints_by_columns(table: str, columns: tuple[str, ...]) -> None:
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_unique_constraints(table):
        if tuple(constraint.get("column_names") or ()) == columns:
            op.drop_constraint(constraint["name"], table, type_="unique")


def _add_catalog_user_columns() -> None:
    for table in ("categories", "payment_methods", "income_categories"):
        op.add_column(table, sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    for table in ("expenses", "income_entries", "expense_import_sources"):
        op.add_column(table, sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))


def _fill_legacy_catalog(connection, owner_id) -> None:
    for table in (
        "categories", "payment_methods", "income_categories", "expenses",
        "income_entries", "expense_import_sources",
    ):
        connection.execute(sa.text(f'UPDATE "{table}" SET user_id = :owner WHERE user_id IS NULL'), {"owner": owner_id})


def _add_defaults_for_legacy_owner(connection, owner_id) -> None:
    for name in REFERENCE_DEFAULTS["categories"]:
        connection.execute(sa.text(
            "INSERT INTO categories (name, user_id) "
            "SELECT :name, :owner WHERE NOT EXISTS "
            "(SELECT 1 FROM categories WHERE user_id = :owner AND lower(trim(name)) = lower(trim(CAST(:name AS varchar))))"
        ), {"name": name, "owner": owner_id})
    for name in REFERENCE_DEFAULTS["payment_methods"]:
        connection.execute(sa.text(
            "INSERT INTO payment_methods (name, user_id) "
            "SELECT :name, :owner WHERE NOT EXISTS "
            "(SELECT 1 FROM payment_methods WHERE user_id = :owner AND lower(trim(name)) = lower(trim(CAST(:name AS varchar))))"
        ), {"name": name, "owner": owner_id})
    for name, requires_expense_category in REFERENCE_DEFAULTS["income_categories"]:
        connection.execute(sa.text(
            "INSERT INTO income_categories (name, requires_expense_category, user_id) "
            "SELECT :name, :requires, :owner WHERE NOT EXISTS "
            "(SELECT 1 FROM income_categories WHERE user_id = :owner AND lower(trim(name)) = lower(trim(CAST(:name AS varchar))))"
        ), {"name": name, "requires": requires_expense_category, "owner": owner_id})


def upgrade() -> None:
    connection = op.get_bind()
    financial_before = _financial_snapshot(connection)
    legacy_tables = (
        "categories", "payment_methods", "income_categories", "expenses",
        "income_entries", "expense_installments", "expense_import_sources",
    )
    has_legacy_data = any(_table_count(connection, table) for table in legacy_tables)
    users = list(connection.scalars(sa.text("SELECT id FROM users ORDER BY id")))
    owner_id = None
    if has_legacy_data:
        if len(users) != 1:
            raise RuntimeError(
                "Migração interrompida: há dados financeiros ou de referência sem proprietário "
                f"inequívoco e foram encontrados {len(users)} usuários. Mantenha exatamente um usuário "
                "ou defina manualmente o proprietário antes de repetir. Nenhum dado foi alterado."
            )
        owner_id = users[0]
        for table in ("categories", "payment_methods", "income_categories"):
            _assert_no_active_name_conflicts(connection, table)

    _add_catalog_user_columns()
    op.add_column("users", sa.Column("reference_data_initialized_at", sa.DateTime(timezone=True), nullable=True))
    if owner_id is not None:
        _fill_legacy_catalog(connection, owner_id)
        _add_defaults_for_legacy_owner(connection, owner_id)
        connection.execute(sa.text(
            "UPDATE users SET reference_data_initialized_at = :now WHERE id = :owner"
        ), {"now": datetime.now(timezone.utc), "owner": owner_id})

    # Fail before installing constraints if the backfill did not cover every legacy row.
    for table in ("categories", "payment_methods", "income_categories", "expenses", "income_entries", "expense_import_sources"):
        missing = _table_count(connection, table) - int(connection.scalar(sa.text(f'SELECT count(*) FROM "{table}" WHERE user_id IS NOT NULL')) or 0)
        if missing:
            raise RuntimeError(f"Migração interrompida: {table} ainda tem {missing} registros sem proprietário.")
    _assert_owned_links(connection)

    for table in ("categories", "payment_methods", "income_categories"):
        _drop_unique_constraints_by_columns(table, ("name",))
        op.create_unique_constraint(f"{table}_id_user_unique", table, ["id", "user_id"])
        op.create_foreign_key(f"{table}_user_fk", table, "users", ["user_id"], ["id"], ondelete="RESTRICT")
        op.alter_column(table, "user_id", nullable=False)
        op.create_index(
            f"{table}_user_active_name_unique", table,
            ["user_id", sa.text("lower(trim(name))")], unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
        op.create_index(f"{table}_user_id_index", table, ["user_id"])

    _drop_unique_constraints_by_columns("expense_import_sources", ("source_key",))
    op.drop_constraint("expenses_category_id_fkey", "expenses", type_="foreignkey")
    op.drop_constraint("expenses_payment_method_id_fkey", "expenses", type_="foreignkey")
    op.drop_constraint("income_entries_income_category_id_fkey", "income_entries", type_="foreignkey")
    op.drop_constraint("income_entries_expense_category_id_fkey", "income_entries", type_="foreignkey")
    op.drop_constraint("expense_import_sources_expense_id_fkey", "expense_import_sources", type_="foreignkey")

    op.create_unique_constraint("expenses_id_user_unique", "expenses", ["id", "user_id"])
    op.create_foreign_key("expenses_user_fk", "expenses", "users", ["user_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("expenses_category_user_fk", "expenses", "categories", ["category_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT")
    op.create_foreign_key("expenses_payment_method_user_fk", "expenses", "payment_methods", ["payment_method_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT")
    op.alter_column("expenses", "user_id", nullable=False)
    op.create_index("expenses_user_expense_date_index", "expenses", ["user_id", "expense_date"])

    op.create_foreign_key("income_entries_user_fk", "income_entries", "users", ["user_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("income_entries_income_category_user_fk", "income_entries", "income_categories", ["income_category_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT")
    op.create_foreign_key("income_entries_expense_category_user_fk", "income_entries", "categories", ["expense_category_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT")
    op.alter_column("income_entries", "user_id", nullable=False)
    op.create_index("income_entries_user_received_date_index", "income_entries", ["user_id", "received_date"])

    op.create_foreign_key("expense_import_sources_expense_user_fk", "expense_import_sources", "expenses", ["expense_id", "user_id"], ["id", "user_id"], ondelete="CASCADE")
    op.create_unique_constraint("expense_import_sources_user_source_unique", "expense_import_sources", ["user_id", "source_key"])
    op.alter_column("expense_import_sources", "user_id", nullable=False)
    op.create_index("expense_installments_expense_due_date_index", "expense_installments", ["expense_id", "due_date"])
    financial_after = _financial_snapshot(connection)
    if financial_after != financial_before:
        raise RuntimeError("Migração interrompida: as contagens, IDs ou totais financeiros mudaram durante a atribuição dos proprietários.")


def downgrade() -> None:
    connection = op.get_bind()
    user_count = _table_count(connection, "users")
    if user_count > 1:
        raise RuntimeError("Downgrade interrompido: a estrutura anterior não preserva isolamento entre múltiplas contas. Restaure um backup.")
    for table in ("categories", "payment_methods", "income_categories"):
        duplicate = connection.execute(sa.text(
            f'''SELECT lower(trim(name)) FROM "{table}" GROUP BY lower(trim(name)) HAVING count(*) > 1 LIMIT 1'''
        )).first()
        if duplicate:
            raise RuntimeError(f"Downgrade interrompido: {table} tem nomes incompatíveis com a unicidade global. Restaure um backup.")

    op.drop_index("expense_installments_expense_due_date_index", table_name="expense_installments")
    op.drop_constraint("expense_import_sources_user_source_unique", "expense_import_sources", type_="unique")
    op.drop_constraint("expense_import_sources_expense_user_fk", "expense_import_sources", type_="foreignkey")
    op.drop_constraint("income_entries_expense_category_user_fk", "income_entries", type_="foreignkey")
    op.drop_constraint("income_entries_income_category_user_fk", "income_entries", type_="foreignkey")
    op.drop_constraint("income_entries_user_fk", "income_entries", type_="foreignkey")
    op.drop_constraint("expenses_payment_method_user_fk", "expenses", type_="foreignkey")
    op.drop_constraint("expenses_category_user_fk", "expenses", type_="foreignkey")
    op.drop_constraint("expenses_user_fk", "expenses", type_="foreignkey")
    op.drop_constraint("expenses_id_user_unique", "expenses", type_="unique")
    op.create_foreign_key("expenses_category_id_fkey", "expenses", "categories", ["category_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("expenses_payment_method_id_fkey", "expenses", "payment_methods", ["payment_method_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("income_entries_income_category_id_fkey", "income_entries", "income_categories", ["income_category_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("income_entries_expense_category_id_fkey", "income_entries", "categories", ["expense_category_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("expense_import_sources_expense_id_fkey", "expense_import_sources", "expenses", ["expense_id"], ["id"], ondelete="CASCADE")
    op.create_unique_constraint("expense_import_sources_source_key_unique", "expense_import_sources", ["source_key"])

    op.drop_index("income_entries_user_received_date_index", table_name="income_entries")
    op.drop_index("expenses_user_expense_date_index", table_name="expenses")
    for table in ("categories", "payment_methods", "income_categories"):
        op.drop_index(f"{table}_user_active_name_unique", table_name=table)
        op.drop_index(f"{table}_user_id_index", table_name=table)
        op.drop_constraint(f"{table}_user_fk", table, type_="foreignkey")
        op.drop_constraint(f"{table}_id_user_unique", table, type_="unique")
        op.create_unique_constraint(f"{table}_name_unique" if table != "income_categories" else "income_categories_name_key", table, ["name"])
    op.drop_column("expense_import_sources", "user_id")
    op.drop_column("income_entries", "user_id")
    op.drop_column("expenses", "user_id")
    for table in ("categories", "payment_methods", "income_categories"):
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "user_id")
    op.drop_column("users", "reference_data_initialized_at")
