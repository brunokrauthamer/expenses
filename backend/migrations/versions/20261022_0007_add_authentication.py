"""add user accounts and refresh sessions

Revision ID: 20261022_0007
Revises: 20261022_0006
Create Date: 2026-10-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261022_0007"
down_revision: str | None = "20261022_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    user_id = sa.Uuid(as_uuid=True)
    op.create_table(
        "users",
        sa.Column("id", user_id, primary_key=True, nullable=False),
        sa.Column("email_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("email_lookup", sa.String(length=64), nullable=False),
        sa.Column("name_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("encryption_key_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email_lookup", name="users_email_lookup_unique"),
    )
    op.create_table(
        "local_credentials",
        sa.Column("user_id", user_id, nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "external_identities",
        sa.Column("id", user_id, nullable=False),
        sa.Column("user_id", user_id, nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("subject_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("subject_lookup", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject_lookup", name="external_identities_subject_unique"),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", user_id, nullable=False),
        sa.Column("user_id", user_id, nullable=False),
        sa.Column("family_id", user_id, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", user_id, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="refresh_sessions_token_hash_unique"),
    )
    op.create_index("refresh_sessions_family_id_index", "refresh_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_index("refresh_sessions_family_id_index", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_table("external_identities")
    op.drop_table("local_credentials")
    op.drop_table("users")
