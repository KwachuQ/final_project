from unittest.mock import patch
from sqlalchemy.orm import Session

from app.s3 import get_s3_client
from app.settings import get_settings

def test_list_assessments_empty(auth_client, mock_s3):
    resp = auth_client.get("/assessments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_assessment_detail(auth_client, mock_s3, sample_inventory_csv):
    create = auth_client.post(
        "/assessments",
        files={"inventory": ("t.csv", sample_inventory_csv.read_bytes(), "text/csv")},
    )
    aid = create.json()["id"]
    resp = auth_client.get(f"/assessments/{aid}")
    assert resp.status_code == 200
    assert "scored_systems" in resp.json()


def test_delete_assessment(auth_client, mock_s3, sample_inventory_csv):
    create = auth_client.post(
        "/assessments",
        files={"inventory": ("t.csv", sample_inventory_csv.read_bytes(), "text/csv")},
    )
    aid = create.json()["id"]
    resp = auth_client.delete(f"/assessments/{aid}")
    assert resp.status_code == 204
    assert auth_client.get(f"/assessments/{aid}").status_code == 404


def test_get_nonexistent_assessment_returns_404(auth_client, mock_s3):
    resp = auth_client.get("/assessments/9999")
    assert resp.status_code == 404

def test_delete_nonexistent_assessment_returns_404(auth_client, mock_s3):
    resp = auth_client.delete("/assessments/9999")
    assert resp.status_code == 404

def test_delete_other_users_assessment_returns_403(auth_client, client, mock_s3, sample_inventory_csv):
    create = auth_client.post(
        "/assessments",
        files={"inventory": ("t.csv", sample_inventory_csv.read_bytes(), "text/csv")},
    )
    aid = create.json()["id"]
    client.post("/auth/register", json={
        "username": "lukasz", 
        "password" : "testpassword123", 
        "password_repeat": "testpassword123"})
    login = client.post("/auth/login", data={
        "username": "lukasz",
        "password": "testpassword123"
    })
    client.headers['Authorization'] = f"Bearer {login.json()['access_token']}"
    resp = client.delete(f"/assessments/{aid}")
    assert resp.status_code == 403

def test_compensating_transaction(auth_client, mock_s3, sample_inventory_csv):
    with patch.object(Session, "commit", side_effect=Exception('db error')):
        resp = auth_client.post(
            "/assessments",
            files={"inventory": ("t.csv", sample_inventory_csv.read_bytes(), "text/csv")},
        )
    assert resp.status_code >= 400

    contents = get_s3_client().list_objects_v2(Bucket=get_settings().AWS_BUCKET_NAME).get("Contents", [])
    assert contents == []
