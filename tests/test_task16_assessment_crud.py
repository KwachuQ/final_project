import pytest


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