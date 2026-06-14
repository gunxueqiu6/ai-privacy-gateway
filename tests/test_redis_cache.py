"""Tests for Redis cache layer: initialization, CRUD operations, health check, and error handling."""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRedisCacheInit:
    """Tests for RedisCache initialization and availability."""

    def test_init_without_redis_available(self):
        from redis_cache import RedisCache, REDIS_AVAILABLE
        cache = RedisCache()
        assert cache._available == REDIS_AVAILABLE

    def test_available_property_false_when_no_redis(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        with patch("redis_cache._redis_client", None):
            assert cache.available is False

    def test_available_property_false_when_client_none(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        with patch("redis_cache._redis_client", None):
            assert cache.available is False

    def test_get_redis_cache_singleton(self):
        from redis_cache import get_redis_cache
        cache1 = get_redis_cache()
        cache2 = get_redis_cache()
        assert cache1 is cache2

    def test_init_sets_internal_state(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        assert hasattr(cache, "_available")

    def test_init_does_not_raise(self):
        from redis_cache import RedisCache
        try:
            RedisCache()
        except Exception:
            pytest.fail("RedisCache() raised an exception")


class TestGetMapping:
    """Tests for get_mapping operation."""

    @pytest.mark.asyncio
    async def test_get_mapping_returns_none_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        result = await cache.get_mapping("test_placeholder")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_mapping_returns_value_when_found(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"original_value"
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_mapping("test_key")
        assert result == "original_value"
        mock_redis.get.assert_called_once_with("vault:test_key")

    @pytest.mark.asyncio
    async def test_get_mapping_returns_none_when_miss(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_mapping("missing_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_mapping_handles_error_gracefully(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_mapping("error_key")
        assert result is None


class TestSetMapping:
    """Tests for set_mapping operation."""

    @pytest.mark.asyncio
    async def test_set_mapping_returns_false_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        result = await cache.set_mapping("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_mapping_success(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_mapping("key1", "value1", ttl=3600)
        assert result is True
        mock_redis.setex.assert_called_once_with("vault:key1", 3600, "value1")

    @pytest.mark.asyncio
    async def test_set_mapping_default_ttl(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_mapping("key2", "value2")
        assert result is True
        mock_redis.setex.assert_called_once_with("vault:key2", 3600, "value2")

    @pytest.mark.asyncio
    async def test_set_mapping_custom_ttl(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_mapping("key3", "value3", ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once_with("vault:key3", 60, "value3")

    @pytest.mark.asyncio
    async def test_set_mapping_handles_error(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_mapping("key_err", "val")
        assert result is False


class TestGetStats:
    """Tests for get_stats operation."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_none_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        result = await cache.get_stats("team_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict_when_found(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        expected = {"count": 42, "masked": 100}
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(expected).encode()
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_stats("team_a")
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_stats_returns_none_on_miss(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_stats("missing_team")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats_handles_error(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.get_stats("error_team")
        assert result is None


class TestSetStats:
    """Tests for set_stats operation."""

    @pytest.mark.asyncio
    async def test_set_stats_returns_false_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        result = await cache.set_stats("team_1", {"count": 10})
        assert result is False

    @pytest.mark.asyncio
    async def test_set_stats_success(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        stats_data = {"count": 42, "masked": 100, "team": "team_x"}
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_stats("team_x", stats_data, ttl=300)
        assert result is True
        mock_redis.setex.assert_called_once_with(
            "stats:team_x", 300, json.dumps(stats_data)
        )

    @pytest.mark.asyncio
    async def test_set_stats_default_ttl(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_stats("team_y", {"count": 5})
        assert result is True
        mock_redis.setex.assert_called_once_with(
            "stats:team_y", 300, json.dumps({"count": 5})
        )

    @pytest.mark.asyncio
    async def test_set_stats_handles_error(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.set_stats("team_e", {"count": 0})
        assert result is False


class TestInvalidate:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_does_nothing_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        mock_redis = MagicMock()
        with patch("redis_cache._redis_client", mock_redis):
            await cache.invalidate("some_key")
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_calls_delete(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        with patch("redis_cache._redis_client", mock_redis):
            await cache.invalidate("key_to_remove")
        mock_redis.delete.assert_called_once_with("vault:key_to_remove")

    @pytest.mark.asyncio
    async def test_invalidate_handles_error(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            await cache.invalidate("error_key")
        # Should not raise, just log
        assert True


class TestHealthCheck:
    """Tests for health check operation."""

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_not_available(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = False
        result = await cache.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_ping_ok(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.health_check()
        assert result is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_ping_fails(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis down")
        with patch("redis_cache._redis_client", mock_redis):
            result = await cache.health_check()
        assert result is False


class TestRoundTrip:
    """Tests for end-to-end cache round-trips with mocked Redis."""

    @pytest.mark.asyncio
    async def test_set_and_get_mapping_roundtrip(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        store = {}
        mock_redis = AsyncMock()

        async def fake_setex(key, ttl, value):
            store[key] = value
            return True

        async def fake_get(key):
            val = store.get(key)
            return val.encode() if val else None

        mock_redis.setex.side_effect = fake_setex
        mock_redis.get.side_effect = fake_get

        with patch("redis_cache._redis_client", mock_redis):
            set_ok = await cache.set_mapping("rt_key", "rt_value", ttl=100)
            assert set_ok is True
            got = await cache.get_mapping("rt_key")
            assert got == "rt_value"

    @pytest.mark.asyncio
    async def test_set_and_get_stats_roundtrip(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        store = {}
        mock_redis = AsyncMock()

        async def fake_setex(key, ttl, value):
            store[key] = value
            return True

        async def fake_get(key):
            raw = store.get(key)
            return raw.encode() if isinstance(raw, str) else raw

        mock_redis.setex.side_effect = fake_setex
        mock_redis.get.side_effect = fake_get

        stats = {"count": 99, "masked": 250}

        with patch("redis_cache._redis_client", mock_redis):
            set_ok = await cache.set_stats("rt_team", stats, ttl=500)
            assert set_ok is True
            got = await cache.get_stats("rt_team")
            assert got == stats

    @pytest.mark.asyncio
    async def test_invalidate_then_get_returns_none(self):
        from redis_cache import RedisCache
        cache = RedisCache()
        cache._available = True
        store = {"vault:del_key": "val"}
        mock_redis = AsyncMock()

        async def fake_delete(key):
            store.pop(key, None)
            return 1

        async def fake_get(key):
            raw = store.get(key)
            return raw.encode() if raw else None

        mock_redis.delete.side_effect = fake_delete
        mock_redis.get.side_effect = fake_get

        with patch("redis_cache._redis_client", mock_redis):
            await cache.invalidate("del_key")
            got = await cache.get_mapping("del_key")
            assert got is None
