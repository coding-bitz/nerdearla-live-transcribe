from __future__ import annotations
import logging
from app.config import settings
from app.redis import get_redis_client

logger = logging.getLogger(__name__)


class AuthRateLimiter:
    """Manages distributed brute-force protection for login attempts using Redis."""

    def _redis_key(self, identifier: str) -> str:
        safe_id = identifier.strip().lower()
        return f"nerdearla:auth:ratelimit:{safe_id}"

    async def is_rate_limited(self, identifier: str) -> bool:
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            attempts = await redis.get(key)
            if attempts is not None and int(attempts) >= settings.auth_rate_limit_attempts:
                return True
        except Exception as exc:
            logger.debug(f"Redis rate limiter check bypassed: {exc}")
        return False

    async def record_failure(self, identifier: str) -> int:
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            attempts = await redis.incr(key)
            if attempts == 1:
                await redis.expire(key, settings.auth_rate_limit_window_seconds)
            return attempts
        except Exception as exc:
            logger.debug(f"Redis rate limiter increment bypassed: {exc}")
            return 0

    async def reset_failures(self, identifier: str) -> None:
        try:
            redis = get_redis_client()
            key = self._redis_key(identifier)
            await redis.delete(key)
        except Exception as exc:
            logger.debug(f"Redis rate limiter reset bypassed: {exc}")


auth_rate_limiter = AuthRateLimiter()
