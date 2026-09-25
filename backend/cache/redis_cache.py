"""
Redis cache helper — provides LLM response caching and session storage.
Falls back gracefully if Redis is unavailable.
"""
import hashlib
import json
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

_redis = None
_redis_available = False


async def _get_redis():
    """Lazy-initialize async Redis client."""
    global _redis, _redis_available
    if _redis is None:
        try:
            import redis.asyncio as aioredis
            _redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            # Test connection
            await _redis.ping()
            _redis_available = True
            logger.info("✅ Redis cache connected")
        except Exception as e:
            logger.warning(f"⚠️  Redis unavailable — caching disabled: {e}")
            _redis = None
            _redis_available = False
    return _redis if _redis_available else None


def _make_key(prefix: str, content: str) -> str:
    """Create a deterministic cache key from content hash."""
    h = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"cortexflow:{prefix}:{h}"


async def get_cached_response(query: str) -> str | None:
    """
    Look up a cached LLM response for this exact query.
    Returns None if not cached or Redis is unavailable.
    """
    client = await _get_redis()
    if not client:
        return None
    try:
        key = _make_key("llm_response", query)
        cached = await client.get(key)
        if cached:
            logger.info(f"🎯 Cache HIT: {key}")
        return cached
    except Exception:
        return None


async def set_cached_response(query: str, response: str, ttl_seconds: int = 3600) -> None:
    """
    Store an LLM response in Redis with a TTL (default 1 hour).
    Silently fails if Redis is unavailable.
    """
    client = await _get_redis()
    if not client:
        return
    try:
        key = _make_key("llm_response", query)
        await client.setex(key, ttl_seconds, response)
        logger.info(f"💾 Cache SET: {key} (TTL={ttl_seconds}s)")
    except Exception:
        pass


async def get_session_history(session_id: str) -> list[dict]:
    """
    Retrieve stored conversation turns for a session.
    Returns empty list if not found or Redis is unavailable.
    """
    client = await _get_redis()
    if not client:
        return []
    try:
        key = f"cortexflow:session:{session_id}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return []
    except Exception:
        return []


async def save_session_turn(session_id: str, role: str, content: str) -> None:
    """
    Append a conversation turn to Redis session history.
    Keeps the last 20 turns. TTL resets to 2 hours on each save.
    """
    client = await _get_redis()
    if not client:
        return
    try:
        key = f"cortexflow:session:{session_id}"
        data = await client.get(key)
        history: list[dict] = json.loads(data) if data else []
        history.append({"role": role, "content": content})
        # Keep only last 20 turns to bound context window
        history = history[-20:]
        await client.setex(key, 7200, json.dumps(history))
    except Exception:
        pass


async def invalidate_session(session_id: str) -> None:
    """Clear session history from Redis."""
    client = await _get_redis()
    if not client:
        return
    try:
        await client.delete(f"cortexflow:session:{session_id}")
    except Exception:
        pass
