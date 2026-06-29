import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecret"

import time  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, UserModel, get_db  # noqa: E402
from app.deps import get_current_user  # noqa: E402
from app.settings import get_settings  # noqa: E402

# Shared in-memory engine for the whole test module.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = sessionmaker(bind=_engine)

# Override dependencies BEFORE importing the app
from app.main import app  # noqa: E402


def _override_get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
Base.metadata.create_all(bind=_engine)


@pytest.fixture
def db():
    """Yield a fresh session with clean tables per test."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_valid_token_returns_user(db):
    """A valid JWT should return the corresponding user."""
    user = UserModel(id=1, username="test", password_hash="x")
    db.add(user)
    db.commit()

    token = jwt.encode(
        {"sub": 1, "exp": int(time.time()) + 3600},
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
    result = get_current_user(token=token, db=db)
    assert result.username == "test"


def test_expired_token_raises_401(db):
    """An expired JWT should raise HTTPException(401)."""
    token = jwt.encode(
        {"sub": 1, "exp": int(time.time()) - 10},
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db)
    assert exc_info.value.status_code == 401


def test_invalid_token_raises_401(db):
    """A garbage/invalid JWT should raise HTTPException(401)."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="garbage", db=db)
    assert exc_info.value.status_code == 401