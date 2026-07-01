from sqlalchemy import text
from app.s3 import get_s3_client


def test_db_fixture_provides_session(db):
    """ The db fixture should yield a working SQLAlchemy session. """
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_client_fixture_works(client):
    """The client fixture should be a TestClient that can hit /health."""
    resp = client.get("/health")
    assert resp.status_code == 200

def test_auth_client_has_auth_header(auth_client):
    """The auth_client fixture should have a pre-set Authorization header."""
    resp = auth_client.get("/assessments")
    assert resp.status_code == 200  # not 401

def test_mock_s3_fixture_isolates(mock_s3):
    """The mock_s3 fixture should provide a working mocked S3 environment."""
    client = get_s3_client()
    client.create_bucket(Bucket="test-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-central-1"})
    response = client.list_buckets()
    assert "Buckets" in response
    assert client.get_bucket_location(Bucket="test-bucket")["LocationConstraint"] == "eu-central-1"