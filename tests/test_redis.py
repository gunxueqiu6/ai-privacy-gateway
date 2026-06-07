"""
Redis Storage 测试 - Redis 存储
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio


class TestRedisStorage:
    """Redis 存储测试"""

    def test_redis_connection(self):
        """测试 Redis 连接"""
        try:
            from redis_storage import RedisStorage, get_redis_storage

            # Mock Redis 连接
            with patch('redis.Redis') as mock_redis:
                mock_redis.return_value.ping.return_value = True

                storage = RedisStorage(host="localhost", port=6379)
                assert storage.is_connected() is True
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_redis_connection_failure(self):
        """测试 Redis 连接失败"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_redis.return_value.ping.side_effect = Exception("Connection refused")

                storage = RedisStorage(host="localhost", port=6379)
                assert storage.is_connected() is False
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_set_and_get(self):
        """测试设置和获取"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.get.return_value = "test_value"

                storage = RedisStorage()
                storage.set("test_key", "test_value")

                result = storage.get("test_key")
                assert result == "test_value"

                mock_client.set.assert_called_once()
                mock_client.get.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_set_with_expiry(self):
        """测试带过期时间设置"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client

                storage = RedisStorage()
                storage.set("test_key", "test_value", expire=3600)

                mock_client.setex.assert_called_with("test_key", 3600, "test_value")
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_delete(self):
        """测试删除"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.delete.return_value = 1

                storage = RedisStorage()
                result = storage.delete("test_key")

                assert result == 1
                mock_client.delete.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_exists(self):
        """测试存在检查"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.exists.return_value = True

                storage = RedisStorage()
                result = storage.exists("test_key")

                assert result is True
                mock_client.exists.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_increment(self):
        """测试计数器"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.incr.return_value = 1

                storage = RedisStorage()
                result = storage.increment("counter")

                assert result == 1
                mock_client.incr.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")


class TestRedisHash:
    """Redis Hash 测试"""

    def test_hset_and_hget(self):
        """测试 Hash 设置和获取"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.hget.return_value = "field_value"

                storage = RedisStorage()
                storage.hset("hash_key", "field", "field_value")

                result = storage.hget("hash_key", "field")
                assert result == "field_value"

                mock_client.hset.assert_called_once()
                mock_client.hget.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_hgetall(self):
        """测试获取所有 Hash 字段"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.hgetall.return_value = {"field1": "value1", "field2": "value2"}

                storage = RedisStorage()
                result = storage.hgetall("hash_key")

                assert len(result) == 2
                assert result["field1"] == "value1"
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_hdel(self):
        """测试删除 Hash 字段"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.hdel.return_value = 1

                storage = RedisStorage()
                result = storage.hdel("hash_key", "field")

                assert result == 1
                mock_client.hdel.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")


class TestRedisList:
    """Redis List 测试"""

    def test_lpush_and_lpop(self):
        """测试 List 推入和弹出"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.lpop.return_value = "item1"

                storage = RedisStorage()
                storage.lpush("list_key", "item1")

                result = storage.lpop("list_key")
                assert result == "item1"

                mock_client.lpush.assert_called_once()
                mock_client.lpop.assert_called_once()
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_lrange(self):
        """测试获取 List 范围"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.lrange.return_value = ["item1", "item2", "item3"]

                storage = RedisStorage()
                result = storage.lrange("list_key", 0, -1)

                assert len(result) == 3
                mock_client.lrange.assert_called_with("list_key", 0, -1)
        except ImportError:
            pytest.skip("redis_storage module not available")


class TestRedisHealthCheck:
    """Redis 健康检查测试"""

    def test_health_check_success(self):
        """测试健康检查成功"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.ping.return_value = True
                mock_client.info.return_value = {"connected_clients": 5}

                storage = RedisStorage()
                health = storage.health_check()

                assert health["status"] == "healthy"
                assert "connected_clients" in health
        except ImportError:
            pytest.skip("redis_storage module not available")

    def test_health_check_failure(self):
        """测试健康检查失败"""
        try:
            from redis_storage import RedisStorage

            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.ping.side_effect = Exception("Connection lost")

                storage = RedisStorage()
                health = storage.health_check()

                assert health["status"] == "unhealthy"
        except ImportError:
            pytest.skip("redis_storage module not available")


class TestRedisCluster:
    """Redis 集群测试"""

    def test_cluster_connection(self):
        """测试集群连接"""
        try:
            from redis_storage import RedisClusterStorage

            with patch('redis.RedisCluster') as mock_cluster:
                mock_cluster.return_value.ping.return_value = True

                storage = RedisClusterStorage(
                    startup_nodes=[{"host": "node1", "port": 6379}]
                )
                assert storage.is_connected() is True
        except ImportError:
            pytest.skip("redis_storage module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])