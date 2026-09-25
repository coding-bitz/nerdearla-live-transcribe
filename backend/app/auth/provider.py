from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from app.auth.hashing import verify_password
from app.config import settings
from app.errors import AuthError


class UserIdentity(BaseModel):
    username: str


class CredentialProvider(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional[UserIdentity]:
        """Validates credentials and returns UserIdentity if valid, None otherwise."""
        pass


class StaticUserCredentialProvider(CredentialProvider):
    """Stateless single-operator credential provider validating against Argon2id hash."""

    async def authenticate(self, username: str, password: str) -> Optional[UserIdentity]:
        configured_user = settings.auth_username
        configured_hash = settings.auth_password_hash

        if not configured_hash:
            raise AuthError("AUTH_PASSWORD_HASH is not configured on the server")

        if not username or username.strip() != configured_user:
            return None

        if not verify_password(password, configured_hash):
            return None

        return UserIdentity(username=configured_user)


# Default credential provider instance
credential_provider = StaticUserCredentialProvider()
