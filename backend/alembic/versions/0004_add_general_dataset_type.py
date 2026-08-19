"""add GENERAL dataset type and column_profile

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05

Two changes to support dataset-agnostic uploads:

1. Adds "general" as a new value to the existing dataset_type Postgres
   ENUM. Postgres enums require ALTER TYPE ... ADD VALUE for this (it
   cannot run inside the same transaction as other DDL on some Postgres
   versions, so it is issued as its own statement with autocommit).

2. Adds the column_profile JSON column to datasets, populated by
   app.services.dataset_intelligence.profile_dataset() at upload time
   for every dataset regardless of dataset_type.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

DATASET_TYPE_ENUM_NAME = "dataset_type"
NEW_VALUE = "general"


def upgrade() -> None:
    bind = op.get_bind()

    # ALTER TYPE ... ADD VALUE must run outside an explicit transaction
    # block on Postgres < 12; Alembic's default connection is already
    # transactional, so we defensively commit first, run in autocommit,
    # then let Alembic continue as normal for the rest of this migration.
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                f"ALTER TYPE {DATASET_TYPE_ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'"
            )

    op.add_column(
        "datasets",
        sa.Column("column_profile", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("datasets", "column_profile")
    # Postgres does not support removing a value from an existing enum
    # type without recreating it; intentionally left as a no-op on
    # downgrade since the old application code simply never writes
    # dataset_type='general' again.
