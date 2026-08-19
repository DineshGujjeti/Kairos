"""initial schema: organizations, users

Revision ID: 0001
Revises:
Create Date: 2026-07-12

NOTE: hand-authored to match app/db/models exactly so Module 1 ships
with a working migration without requiring a live Postgres instance at
generation time. Once the DB is running, verify it matches by running:
    alembic upgrade head
    alembic revision --autogenerate -m "check drift"
The second command should produce an EMPTY migration -- if it doesn't,
this file has drifted from the models and needs reconciling.

ENUM LIFECYCLE NOTE: postgresql.ENUM defaults to create_type=True,
which means SQLAlchemy will try to emit CREATE TYPE for it any time
that ENUM instance appears in DDL -- including implicitly, as part of
op.create_table's column definition. If the same enum is *also*
created explicitly beforehand (as an earlier version of this migration
did), Postgres raises `DuplicateObject: type "user_role" already
exists` because the type gets created twice.

The fix: create the type explicitly and exactly once via
`user_role_enum.create(bind, checkfirst=True)`, then pass
`create_type=False` on the separate ENUM instance used inside the
column definition so create_table treats the type as already existing
and does not attempt to create it again. Symmetrically, on downgrade
the table is dropped first, then the type is dropped explicitly and
exactly once.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

USER_ROLE_VALUES = ("admin", "analyst", "viewer")
USER_ROLE_ENUM_NAME = "user_role"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
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

    # Step 1: create the enum TYPE explicitly, exactly once.
    user_role_enum = postgresql.ENUM(
        *USER_ROLE_VALUES, name=USER_ROLE_ENUM_NAME, create_type=True
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: reference that same type in the column definition with
    # create_type=False, so create_table's DDL for the "role" column
    # does NOT attempt to CREATE TYPE again -- it just uses the
    # already-existing type by name.
    role_column_type = postgresql.ENUM(
        *USER_ROLE_VALUES, name=USER_ROLE_ENUM_NAME, create_type=False
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", role_column_type, nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
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
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop the enum type explicitly, exactly once, after the table
    # that depends on it is gone (Postgres won't drop a type that's
    # still referenced by a column).
    user_role_enum = postgresql.ENUM(
        *USER_ROLE_VALUES, name=USER_ROLE_ENUM_NAME, create_type=False
    )
    user_role_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_table("organizations")
