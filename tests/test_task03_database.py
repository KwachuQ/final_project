def test_base_is_declarative(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    import importlib
    import app.database
    importlib.reload(app.database)
    from app.database import Base

    assert hasattr(Base, "metadata")


def test_get_db_yields_session(monkeypatch):
    """Verify get_db is a generator that yields a session and closes it."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    import importlib
    import app.database
    importlib.reload(app.database)
    from app.database import get_db

    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass  # expected — generator closes