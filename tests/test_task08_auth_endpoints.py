
def test_register_returns_201(client):
    resp = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123", "password_repeat": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "user_id" in data


def test_register_duplicate_returns_409(client):
    payload = {"username": "dup", "password": "secret123", "password_repeat": "secret123"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_returns_token(client):
    client.post(
        "/auth/register",
        json={"username": "bob", "password": "secret123", "password_repeat": "secret123"},
    )
    resp = client.post("/auth/login", data={"username": "bob", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client):
    client.post(
        "/auth/register",
        json={"username": "carol", "password": "secret123", "password_repeat": "secret123"},
    )
    resp = client.post("/auth/login", data={"username": "carol", "password": "wrong"})
    assert resp.status_code == 401
