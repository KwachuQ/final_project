def test_settings_loads_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import Settings

    s = Settings()
    assert s.AWS_REGION == "eu-central-1"
    assert s.DATABASE_URL == "postgresql://test:test@localhost/test"


def test_settings_aws_endpoint_url_optional(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import Settings

    s = Settings()
    assert s.AWS_ENDPOINT_URL is None


def test_settings_allowed_origins_optional(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import Settings

    s = Settings()
    assert s.ALLOWED_ORIGINS is None


def test_settings_allowed_origins_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
    from app.settings import Settings

    s = Settings()
    assert s.ALLOWED_ORIGINS == "http://localhost:3000,http://localhost:8000"


def test_settings_aws_endpoint_url_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localstack:4566")
    from app.settings import Settings

    s = Settings()
    assert s.AWS_ENDPOINT_URL == "http://localstack:4566"


def test_get_settings_returns_cached(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2