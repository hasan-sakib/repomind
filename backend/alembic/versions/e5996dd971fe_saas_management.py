"""saas_management

Revision ID: e5996dd971fe
Revises: 1a1b14c2ef64
Create Date: 2026-09-12 09:37:59.065959

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5996dd971fe"
down_revision: str | Sequence[str] | None = "1a1b14c2ef64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Unlike api_key_role below (created implicitly as part of op.create_table),
# a Postgres enum type used in a bare op.add_column on an *existing* table
# has to be created explicitly first — op.create_table's DDL sequence
# handles that automatically, ADD COLUMN doesn't.
organization_plan_enum = postgresql.ENUM(
    "free", "pro", "team", name="organization_plan", create_type=False
)


def upgrade() -> None:
    organization_plan_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "api_keys",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "developer", "viewer", name="api_key_role"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)

    # server_default so existing organizations backfill to "free" rather
    # than failing the NOT NULL constraint — kept permanently (not dropped
    # after backfill) as a DB-level safety net, matching CreatedAtMixin's
    # own server_default=func.now() elsewhere in this codebase, alongside
    # the ORM-level default=Plan.FREE on the model for new rows.
    op.add_column(
        "organizations",
        sa.Column("plan", organization_plan_enum, server_default="free", nullable=False),
    )

    # NOTE: autogenerate also proposed dropping and recreating
    # ix_code_embeddings_embedding_hnsw — the same recurring false positive
    # documented in every migration since 0005-0008 (autogenerate doesn't
    # understand the hand-written raw-SQL HNSW index), removed here too.


def downgrade() -> None:
    op.drop_column("organizations", "plan")
    organization_plan_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")
    sa.Enum(name="api_key_role").drop(op.get_bind(), checkfirst=True)
