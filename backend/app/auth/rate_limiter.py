from __future__ import annotations
import logging
from typing import Dict
from app.config import settings
from app.redis import get_redis_client

logger = logging.getLogger(__name__)


class AuthRateLimiter:
    """Manages distributed brute-force protection for login attempts using Redis with local fallback."""

    def __init__(self) -> None:
        self._local_counts: Dict[str, int] = {}

    def _redis_key(self, identifier: str) -> str:
        safe_id = identifier.strip().lower()
        return f"nerdearla:auth:ratelimit:{safe_id}"

    async def is_rate_limited(self, identifier: str) -> bool:
        safe_id = identifier.strip().lower()
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            attempts = await redis.get(key)
            if attempts is not None:
                return int(attempts) >= settings.auth_rate_limit_attempts
        except Exception as exc:
            logger.debug(f"Redis rate limiter check offline fallback: {exc}")

        # Local fallback when Redis is offline in dev/test
        count = self._local_counts.get(safe_id, 0)
        return count >= settings.auth_rate_limit_attempts

    async def record_failure(self, identifier: str) -> int:
        safe_id = identifier.strip().lower()
        self._local_counts[safe_id] = self._local_counts.get(safe_id, 0) + 1
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            attempts = await redis.incr(key)
            if attempts == 1:
                await redis.expire(key, settings.auth_rate_limit_window_seconds)
            return attempts
        except Exception as exc:
            logger.debug(f"Redis rate limiter increment offline fallback: {exc}")
            return self._local_counts[safe_id]

    async def reset_failures(self, identifier: str) -> None:
        safe_id = identifier.strip().lower()
        self._local_counts.pop(safe_id, None)
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            await redis.delete(key)
        except Exception as exc:
            logger.debug(f"Redis rate limiter reset offline fallback: {exc}")


auth_rate_limiter = AuthRateLimiter()
