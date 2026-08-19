"""add datasets table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12

Follows the same enum-lifecycle pattern established (and fixed) in
0001: each enum TYPE is created explicitly and exactly once via
`.create(bind, checkfirst=True)`, and referenced inside the table's
column definitions with `create_type=False` so create_table's DDL
does not attempt to create it a second time.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DATASET_TYPE_VALUES = ("orders", "products", "inventory", "warehouses", "suppliers", "deliveries")
DATASET_TYPE_ENUM_NAME = "dataset_type"

DATASET_STATUS_VALUES = ("uploaded", "validating", "valid", "invalid", "failed")
DATASET_STATUS_ENUM_NAME = "dataset_status"


def upgrade() -> None:
    bind = op.get_bind()

    dataset_type_enum = postgresql.ENUM(
        *DATASET_TYPE_VALUES, name=DATASET_TYPE_ENUM_NAME, create_type=True
    )
    dataset_type_enum.create(bind, checkfirst=True)

    dataset_status_enum = postgresql.ENUM(
        *DATASET_STATUS_VALUES, name=DATASET_STATUS_ENUM_NAME, create_type=True
    )
    dataset_status_enum.create(bind, checkfirst=True)

    dataset_type_column = postgresql.ENUM(
        *DATASET_TYPE_VALUES, name=DATASET_TYPE_ENUM_NAME, create_type=False
    )
    dataset_status_column = postgresql.ENUM(
        *DATASET_STATUS_VALUES, name=DATASET_STATUS_ENUM_NAME, create_type=False
    )

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dataset_type", dataset_type_column, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("schema_json", postgresql.JSONB(), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status", dataset_status_column, nullable=False, server_default="uploaded"
        ),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_datasets_org_id", "datasets", ["org_id"])
    op.create_index("ix_datasets_dataset_type", "datasets", ["dataset_type"])


def downgrade() -> None:
    op.drop_index("ix_datasets_dataset_type", table_name="datasets")
    op.drop_index("ix_datasets_org_id", table_name="datasets")
    op.drop_table("datasets")

    postgresql.ENUM(name=DATASET_STATUS_ENUM_NAME, create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name=DATASET_TYPE_ENUM_NAME, create_type=False).drop(
        op.get_bind(), checkfirst=True
    )
