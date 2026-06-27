import os

# Set env vars before any app imports to satisfy pydantic-settings
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "testsecret")

from fastapi.testclient import TestClient  # noqa: E402


def test_health_endpoint():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_cors_middleware_present():
    from app.main import app
    middleware_classes = [type(m).__name__ for m in app.user_middleware]
    # CORS middleware should be registered
    assert any("CORS" in name or "cors" in name for name in middleware_classes) or \
        any("CORSMiddleware" in str(m) for m in app.user_middleware)
