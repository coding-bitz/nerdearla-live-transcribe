import time
import pytest
from app.auth.jwt import create_access_token, decode_access_token
from app.config import settings
from app.errors import AppError, AuthError


def test_create_and_decode_valid_jwt() -> None:
    original_secret = settings.auth_jwt_secret
    settings.auth_jwt_secret = "super-secret-key-that-is-at-least-32-bytes-long!"
    try:
        token = create_access_token("operator-admin", expires_in_seconds=3600)
        assert isinstance(token, str)

        payload = decode_access_token(token)
        assert payload["sub"] == "operator-admin"
        assert payload["exp"] > time.time()
    finally:
        settings.auth_jwt_secret = original_secret


def test_expired_jwt_raises_auth_expired() -> None:
    original_secret = settings.auth_jwt_secret
    settings.auth_jwt_secret = "super-secret-key-that-is-at-least-32-bytes-long!"
    try:
        # Create expired token (-10 seconds)
        token = create_access_token("operator-admin", expires_in_seconds=-10)
        with pytest.raises(AppError) as exc_info:
            decode_access_token(token)
        assert exc_info.value.code == "AUTH_EXPIRED"
    finally:
        settings.auth_jwt_secret = original_secret


def test_invalid_signature_raises_auth_invalid_token() -> None:
    original_secret = settings.auth_jwt_secret
    try:
        settings.auth_jwt_secret = "secret-one-that-is-sufficiently-long-for-hmac!"
        token = create_access_token("operator-admin", expires_in_seconds=3600)

        # Switch secret to invalidate signature
        settings.auth_jwt_secret = "secret-two-that-is-sufficiently-long-for-hmac!"
        with pytest.raises(AppError) as exc_info:
            decode_access_token(token)
        assert exc_info.value.code == "AUTH_INVALID_TOKEN"
    finally:
        settings.auth_jwt_secret = original_secret


def test_empty_jwt_secret_raises_auth_error() -> None:
    original_secret = settings.auth_jwt_secret
    try:
        settings.auth_jwt_secret = ""
        with pytest.raises(AuthError, match="AUTH_JWT_SECRET is required"):
            create_access_token("admin")

        with pytest.raises(AuthError, match="AUTH_JWT_SECRET is required"):
            decode_access_token("some.fake.token")
    finally:
        settings.auth_jwt_secret = original_secret
