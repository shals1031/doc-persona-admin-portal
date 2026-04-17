import json
from typing import Any

import redis.asyncio as aioredis

from core.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def cache_get(key: str) -> Any | None:
    try:
        client = get_redis()
        value = await client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        # Fallback to None if Redis is down or JSON is invalid
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    try:
        client = get_redis()
        await client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        # Ignore cache setting errors
        pass


async def cache_delete(key: str) -> None:
    try:
        client = get_redis()
        await client.delete(key)
    except Exception:
        # Ignore cache deletion errors
        pass


async def publish_event(channel: str, message: dict) -> None:
    try:
        client = get_redis()
        await client.publish(channel, json.dumps(message, default=str))
    except Exception:
        # Ignore publishing errors
        pass
