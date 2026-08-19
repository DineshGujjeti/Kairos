"""
Shared SQLAlchemy declarative base.

Every model in app/db/models/ inherits from `Base`. Keeping this in its
own module (rather than defining Base inside models/user.py, say) avoids
circular imports and gives Alembic one canonical place to import
metadata from (see alembic/env.py).
"""
import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class GUID(TypeDecorator):
    """Platform-independent UUID column (Postgres native UUID / SQLite CHAR(36))."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model that inherits it."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """
    UUID primary keys instead of auto-increment integers.

    Chosen because: (1) IDs are safe to expose in URLs/APIs without
    leaking record counts or enabling enumeration attacks, and (2) it
    matches how a real multi-tenant SaaS product would be built, since
    IDs may eventually need to be generated client-side or merged across
    environments.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
