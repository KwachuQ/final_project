import io
import pytest


def test_create_assessment_returns_201(auth_client, mock_s3, sample_inventory_csv):
    resp = auth_client.post(
        "/assessments",
        files={"inventory": ("test.csv", sample_inventory_csv.read_bytes(), "text/csv")},
        data={"name": "My Assessment"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Assessment"
    assert data["system_count"] == 1
    assert len(data["scored_systems"]) == 1


def test_create_assessment_invalid_csv_returns_400(auth_client, mock_s3):
    bad_csv = b"system_name,system_type\nfoo,INVALID\n"
    resp = auth_client.post(
        "/assessments",
        files={"inventory": ("bad.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 400