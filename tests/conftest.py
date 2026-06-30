import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from moto import mock_aws

import app.main as app_main
from app.database import Base, get_db
from app.main import app
from app.settings import get_settings


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()


@pytest.fixture
def test_engine(pg_container):
    """Per-test Postgres engine with clean schema."""
    engine = create_engine(pg_container)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    """Provide a clean database session per test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db, test_engine, monkeypatch):
    """Provide a test client with overridden dependencies."""
    monkeypatch.setattr(app_main, "engine", test_engine)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    """Provide an authenticated client."""
    get_settings.cache_clear()

    client.post(
        "/auth/register",
        json={"username": "test_user", "password": "password", "password_repeat": "password"},
    )
    resp = client.post("/auth/login", data={"username": "test_user", "password": "password"})
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client


@pytest.fixture
def mock_s3(monkeypatch):
    """Provide a mock S3 client."""
    get_settings.cache_clear()
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_BUCKET_NAME", "test-bucket")

    with mock_aws():
        yield


@pytest.fixture
def sample_inventory_csv(tmp_path):
    """Write a valid one-row inventory CSV to a temp file and return its path."""
    csv = tmp_path / "inventory.csv"
    csv.write_text(
        "system_name,system_type,operating_system,language,num_users,"
        "data_size_gb,availability,has_compliance,is_vendor_software\n"
        "erp,web_app,linux,python,100,10.0,high,false,false\n"
    )
    return csv
