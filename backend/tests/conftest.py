import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DATASET_STORAGE_DIR", "./test_uploads")
os.environ.setdefault("DUCKDB_PATH", "./test_uploads/test_analytics.duckdb")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.db.session import get_db
from app.main import app

# Tests run against SQLite in-memory rather than Postgres so the suite
# is fast and has zero external dependencies -- acceptable because the
# tables here don't use Postgres-specific features beyond the UUID/ENUM
# types, which SQLAlchemy transparently emulates for SQLite in tests.
engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email, org="Acme Corp", password="supersecret123"):
    """
    Shared helper (not a fixture itself, since tests need different
    emails/orgs/roles) used across test_auth.py, test_datasets.py, and
    test_eda.py to avoid every test file reimplementing register-then-
    login boilerplate. Returns the auth headers dict, ready to pass to
    client calls.
    """
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "password": password,
            "organization_name": org,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    """First user registered in a fresh org -- Admin by default (see auth_service.py)."""
    return register_and_login(client, "admin@kairos.dev", org="Acme Corp")


@pytest.fixture
def viewer_headers(client):
    """Second user in the same org -- Viewer by default, used for RBAC tests."""
    register_and_login(client, "admin@kairos.dev", org="Acme Corp")  # ensures org + admin exist first
    return register_and_login(client, "viewer@kairos.dev", org="Acme Corp")


@pytest.fixture
def other_org_headers(client):
    """A user in a completely different org, used for cross-tenant isolation tests."""
    return register_and_login(client, "outsider@other.dev", org="Other Org")
