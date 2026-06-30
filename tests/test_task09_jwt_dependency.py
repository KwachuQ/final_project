import time

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, UserModel
from app.deps import get_current_user
from app.settings import get_settings

_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine)


@pytest.fixture
def db():
    Base.metadata.create_all(_engine)
    session = _Session()
    yield session
    session.close()
    Base.metadata.drop_all(_engine)


def _token(payload: dict) -> str:
    return jwt.encode(payload, get_settings().SECRET_KEY, algorithm="HS256")


def test_valid_token_returns_user(db):
    db.add(UserModel(id=1, username="test", password_hash="x"))
    db.commit()
    token = _token({"sub": "1", "exp": int(time.time()) + 3600})
    assert get_current_user(token=token, db=db).username == "test"


def test_expired_token_raises_401(db):
    token = _token({"sub": "1", "exp": int(time.time()) - 10})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db)
    assert exc.value.status_code == 401


def test_invalid_token_raises_401(db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="garbage", db=db)
    assert exc.value.status_code == 401