"""
Optional Redis cache layer for Enterprise tier.
Implements Cache-Aside pattern for high-frequency vault lookups.
Only activates when REDIS_URL environment variable is configured.
"""
import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "")

if REDIS_URL:
    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(REDIS_URL)
        logger.info(f"Redis cache enabled: {REDIS_URL}")
        REDIS_AVAILABLE = True
    except ImportError:
        logger.warning("redis package not installed. Redis cache disabled.")
        _redis_client = None
        REDIS_AVAILABLE = False
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        _redis_client = None
        REDIS_AVAILABLE = False
else:
    _redis_client = None
    REDIS_AVAILABLE = False


class RedisCache:
    """Cache-Aside implementation for vault mappings and stats."""

    def __init__(self) -> None:
        self._available = REDIS_AVAILABLE

    @property
    def available(self) -> bool:
        return self._available and _redis_client is not None

    async def get_mapping(self, placeholder: str) -> Optional[str]:
        """Get a mapping from cache."""
        if not self.available:
            return None
        try:
            value = await _redis_client.get(f"vault:{placeholder}")
            return value.decode() if value else None
        except Exception as e:
            logger.debug(f"Redis get_mapping error: {e}")
            return None

    async def set_mapping(self, placeholder: str, original: str, ttl: int = 3600) -> bool:
        """Cache a mapping with TTL in seconds."""
        if not self.available:
            return False
        try:
            await _redis_client.setex(f"vault:{placeholder}", ttl, original)
            return True
        except Exception as e:
            logger.debug(f"Redis set_mapping error: {e}")
            return False

    async def get_stats(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get cached stats for a team."""
        if not self.available:
            return None
        try:
            data = await _redis_client.get(f"stats:{team_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.debug(f"Redis get_stats error: {e}")
            return None

    async def set_stats(self, team_id: str, stats: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache stats for a team."""
        if not self.available:
            return False
        try:
            await _redis_client.setex(f"stats:{team_id}", ttl, json.dumps(stats))
            return True
        except Exception as e:
            logger.debug(f"Redis set_stats error: {e}")
            return False

    async def invalidate(self, placeholder: str) -> None:
        """Remove a cached mapping."""
        if not self.available:
            return
        try:
            await _redis_client.delete(f"vault:{placeholder}")
        except Exception as e:
            logger.debug(f"Redis invalidate error: {e}")

    async def health_check(self) -> bool:
        """Check if Redis is responsive."""
        if not self.available:
            return False
        try:
            await _redis_client.ping()
            return True
        except Exception:
            return False


# Global cache instance
_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """Get or create the Redis cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
