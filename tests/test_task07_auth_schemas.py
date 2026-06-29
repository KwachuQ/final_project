import pytest
from app.schemas import UserRegister, UserResponse, TokenResponse, ErrorResponse


def test_user_register_valid():
    u = UserRegister(username="alice", password="secret", password_repeat="secret")
    assert u.username == "alice"


def test_user_register_password_mismatch():
    with pytest.raises(ValueError):
        UserRegister(username="alice", password="secret", password_repeat="wrong")


def test_user_response_fields():
    r = UserResponse(user_id=1, username="alice")
    assert r.user_id == 1


def test_token_response_fields():
    t = TokenResponse(access_token="abc", token_type="bearer")
    assert t.access_token == "abc"


def test_error_response_fields():
    e = ErrorResponse(detail="not found")
    assert e.detail == "not found"