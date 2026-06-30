import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from moto import mock_aws

from app.main import app
from app.database import Base, get_db, UserModel
from app.deps import get_current_user
from app.settings import get_settings


# 1. Setup an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
def override_get_current_user():
    return UserModel(id=1, username="test_user")


# Swap out the real dependencies for our test ones
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
@pytest.fixture
def auth_client():
    """Returns a TestClient with the dependencies already overridden."""
    return TestClient(app)
@pytest.fixture
def mock_s3(monkeypatch):
    """Intercepts AWS calls and uses an in-memory mock."""
    get_settings.cache_clear()
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_BUCKET_NAME", "test-bucket")
    
    with mock_aws():
        yield


VALID_CSV = (
    "system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    "erp,web_app,linux,python,100,10.0,high,false,false\n"
)

def test_list_assessments_empty(auth_client, mock_s3):
    resp = auth_client.get("/assessments")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_assessment_detail(auth_client, mock_s3):
    create = auth_client.post("/assessments", files={"inventory": ("t.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")})
    aid = create.json()["id"]
    resp = auth_client.get(f"/assessments/{aid}")
    assert resp.status_code == 200
    assert "scored_systems" in resp.json()

def test_delete_assessment(auth_client, mock_s3):
    create = auth_client.post("/assessments", files={"inventory": ("t.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")})
    aid = create.json()["id"]
    resp = auth_client.delete(f"/assessments/{aid}")
    assert resp.status_code == 204
    assert auth_client.get(f"/assessments/{aid}").status_code == 404

def test_get_nonexistent_assessment_returns_404(auth_client, mock_s3):
    resp = auth_client.get("/assessments/9999")
    assert resp.status_code == 404