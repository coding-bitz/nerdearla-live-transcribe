from __future__ import annotations
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.auth.provider import UserIdentity, credential_provider
from app.auth.rate_limiter import auth_rate_limiter
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Operator username")
    password: str = Field(..., description="Operator plain password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    authenticated: bool
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request) -> Dict[str, Any]:
    """Authenticates operator credentials and returns a stateless signed JWT."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{payload.username.strip().lower()}"

    if await auth_rate_limiter.is_rate_limited(rate_limit_key):
        logger.warning(f"Rate limit exceeded for login attempt from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )

    user = await credential_provider.authenticate(payload.username, payload.password)
    if user is None:
        await auth_rate_limiter.record_failure(rate_limit_key)
        logger.info(f"Failed login attempt for username '{payload.username}' from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Authentication successful, reset failed attempts
    await auth_rate_limiter.reset_failures(rate_limit_key)
    logger.info(f"Successful login for operator '{user.username}' from {client_ip}")

    token = create_access_token(user.username, settings.auth_jwt_expires_seconds)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.auth_jwt_expires_seconds,
    }


@router.get("/me", response_model=MeResponse)
async def get_me(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    """Verifies that the provided JWT is valid and returns operator identity."""
    return {
        "authenticated": True,
        "username": user.username,
    }
