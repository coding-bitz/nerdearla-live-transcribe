from __future__ import annotations
import time
from typing import Any, Dict, Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.config import settings
from app.errors import AppError, AuthError

JWT_ALGORITHM = "HS256"


def create_access_token(subject: str, expires_in_seconds: Optional[int] = None) -> str:
    """Creates a signed stateless JWT for the given subject."""
    secret = settings.auth_jwt_secret
    if not secret or not secret.strip():
        raise AuthError("AUTH_JWT_SECRET is required to sign JWT tokens")

    now = int(time.time())
    expires = now + (expires_in_seconds or settings.auth_jwt_expires_seconds)

    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expires,
    }

    return jwt.encode(payload, secret.strip(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a signed JWT token, enforcing expiration and signature."""
    secret = settings.auth_jwt_secret
    if not secret or not secret.strip():
        raise AuthError("AUTH_JWT_SECRET is required to validate JWT tokens")

    if not token or not token.strip():
        raise AppError("AUTH_INVALID_TOKEN", "Authentication token is missing or empty")

    try:
        payload = jwt.decode(
            token.strip(),
            secret.strip(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        return payload
    except ExpiredSignatureError as exc:
        raise AppError("AUTH_EXPIRED", "Authentication token expired", retryable=False) from exc
    except InvalidTokenError as exc:
        raise AppError("AUTH_INVALID_TOKEN", f"Authentication token is invalid: {exc}", retryable=False) from exc
