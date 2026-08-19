"""
PostgreSQL engine + session management (transactional store).

This is the ONLY place a SQLAlchemy engine is constructed. Every service
that needs a DB session gets one via `get_db`, injected by FastAPI --
never by importing a global session directly. This keeps sessions
request-scoped, which is what makes the app safe under concurrent load.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,  # detects stale connections before use
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped DB session, always closed after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
