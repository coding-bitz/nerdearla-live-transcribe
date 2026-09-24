import logging
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
    return _redis_client


async def ping_redis() -> bool:
    """Verifies Redis connectivity."""
    try:
        client = get_redis_client()
        return await client.ping()
    except Exception as exc:
        logger.warning(f"Redis ping failed: {exc}")
        return False


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
