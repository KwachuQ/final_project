import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Single shared in-memory engine for the whole test module.
# StaticPool ensures all connections (create_all + get_db) see the same DB.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = sessionmaker(bind=_engine)


def _override_get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
Base.metadata.create_all(bind=_engine)


@pytest.fixture(autouse=True)
def _reset_db():
    """Drop and recreate all tables between tests for isolation."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield


def test_register_returns_201():
    client = TestClient(app)
    resp = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123", "password_repeat": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "user_id" in data


def test_register_duplicate_returns_409():
    client = TestClient(app)
    payload = {"username": "dup", "password": "secret123", "password_repeat": "secret123"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_returns_token():
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={"username": "bob", "password": "secret123", "password_repeat": "secret123"},
    )
    resp = client.post("/auth/login", data={"username": "bob", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password_returns_401():
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={"username": "carol", "password": "secret123", "password_repeat": "secret123"},
    )
    resp = client.post("/auth/login", data={"username": "carol", "password": "wrong"})
    assert resp.status_code == 401
