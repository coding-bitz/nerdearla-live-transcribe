import pytest
from app.auth.hashing import hash_password, verify_password
from app.auth.provider import StaticUserCredentialProvider, UserIdentity
from app.auth.rate_limiter import AuthRateLimiter
from app.config import settings
from app.errors import AuthError


def test_argon2_hashing_and_verification() -> None:
    password = "SuperSecurePassword123!"
    pw_hash = hash_password(password)

    assert pw_hash.startswith("$argon2id$")
    assert verify_password(password, pw_hash) is True
    assert verify_password("WrongPassword!", pw_hash) is False
    assert verify_password("", pw_hash) is False
    assert verify_password(password, "") is False


def test_hash_empty_password_fails() -> None:
    with pytest.raises(ValueError):
        hash_password("")


@pytest.mark.asyncio
async def test_static_credential_provider_success() -> None:
    provider = StaticUserCredentialProvider()
    original_user = settings.auth_username
    original_hash = settings.auth_password_hash

    test_pass = "NerdearlaConference2026!"
    test_hash = hash_password(test_pass)

    try:
        settings.auth_username = "test-operator"
        settings.auth_password_hash = test_hash

        user = await provider.authenticate("test-operator", test_pass)
        assert isinstance(user, UserIdentity)
        assert user.username == "test-operator"

        # Wrong password
        assert await provider.authenticate("test-operator", "wrong") is None
        # Wrong username
        assert await provider.authenticate("wrong-user", test_pass) is None
    finally:
        settings.auth_username = original_user
        settings.auth_password_hash = original_hash


@pytest.mark.asyncio
async def test_static_credential_provider_missing_hash_raises_error() -> None:
    provider = StaticUserCredentialProvider()
    original_hash = settings.auth_password_hash
    try:
        settings.auth_password_hash = ""
        with pytest.raises(AuthError, match="AUTH_PASSWORD_HASH is not configured"):
            await provider.authenticate("admin", "any")
    finally:
        settings.auth_password_hash = original_hash
