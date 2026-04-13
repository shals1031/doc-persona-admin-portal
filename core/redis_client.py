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
    client = get_redis()
    value = await client.get(key)
    if value is None:
        return None
    return json.loads(value)


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    client = get_redis()
    await client.setex(key, ttl_seconds, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    client = get_redis()
    await client.delete(key)


async def publish_event(channel: str, message: dict) -> None:
    client = get_redis()
    await client.publish(channel, json.dumps(message, default=str))
