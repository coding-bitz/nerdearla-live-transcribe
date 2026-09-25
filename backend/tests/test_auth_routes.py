import asyncio
import pytest
from fastapi.testclient import TestClient
from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.auth.rate_limiter import auth_rate_limiter
from app.config import settings
from app.main import app

TEST_PASSWORD = "OperatorPassword2026!"
TEST_SECRET = "super-secret-key-that-is-at-least-32-bytes-long!"


@pytest.fixture(autouse=True)
def setup_auth_settings():
    orig_user = settings.auth_username
    orig_hash = settings.auth_password_hash
    orig_secret = settings.auth_jwt_secret

    settings.auth_username = "admin"
    settings.auth_password_hash = hash_password(TEST_PASSWORD)
    settings.auth_jwt_secret = TEST_SECRET
    auth_rate_limiter._local_counts.clear()
    try:
        asyncio.run(auth_rate_limiter.reset_failures("testclient:admin"))
    except Exception:
        pass

    yield

    settings.auth_username = orig_user
    settings.auth_password_hash = orig_hash
    settings.auth_jwt_secret = orig_secret
    auth_rate_limiter._local_counts.clear()
    try:
        asyncio.run(auth_rate_limiter.reset_failures("testclient:admin"))
    except Exception:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_login_success(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": TEST_PASSWORD})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 28800


def test_login_wrong_password_fails_generically(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "WrongPassword!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_wrong_username_fails_generically(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "unknown_user", "password": TEST_PASSWORD})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_get_auth_me_authenticated(client: TestClient) -> None:
    token = create_access_token("admin")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "admin"}


def test_get_auth_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_auth_me_invalid_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.string"})
    assert response.status_code == 401


def test_protected_session_endpoint_rejects_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/sessions/test-sess")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


@pytest.mark.asyncio
async def test_login_rate_limiting(client: TestClient) -> None:
    # Trigger 5 failed attempts
    for _ in range(5):
        resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    # 6th attempt should be blocked by rate limiter
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 429
    assert "Too many failed login attempts" in resp.json()["detail"]

    # Reset failure counter for test isolation
    await auth_rate_limiter.reset_failures("testclient:admin")
