"""
Redis 存储模块 - Enterprise 版
替代 SQLite，支持高并发、TTL 自动过期
"""
import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import redis

from config import config

logger = logging.getLogger(__name__)


class RedisStorage:
    """Redis 存储引擎"""

    def __init__(self):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        self.key_prefix = "ai_privacy:"
        self.default_ttl = 86400  # 24小时

    def _get_key(self, key: str) -> str:
        """获取完整键名"""
        return f"{self.key_prefix}{key}"

    def save_mapping(self, session_id: str, placeholder: str, real_value: str, data_type: str):
        """保存单个映射"""
        key = self._get_key(f"mapping:{session_id}:{placeholder}")
        data = {
            "placeholder": placeholder,
            "real_value": real_value,
            "data_type": data_type,
            "created_at": datetime.now().isoformat()
        }
        self.client.setex(key, self.default_ttl, json.dumps(data))

        # 同时存入会话集合
        session_key = self._get_key(f"session:{session_id}")
        self.client.sadd(session_key, placeholder)
        self.client.expire(session_key, self.default_ttl)

    def save_mappings(self, session_id: str, mappings: Dict[str, str], data_type: str = "unknown"):
        """批量保存映射"""
        for placeholder, real_value in mappings.items():
            self.save_mapping(session_id, placeholder, real_value, data_type)
        logger.info(f"[Redis] 保存 {len(mappings)} 条映射，会话 {session_id}")

    def get_mapping(self, session_id: str, placeholder: str) -> Optional[str]:
        """获取单个映射"""
        key = self._get_key(f"mapping:{session_id}:{placeholder}")
        data = self.client.get(key)
        if data:
            return json.loads(data).get("real_value")
        return None

    def get_all_mappings(self) -> Dict[str, str]:
        """获取所有映射（用于还原）"""
        mappings = {}
        pattern = self._get_key("mapping:*")
        for key in self.client.scan_iter(match=pattern):
            data = self.client.get(key)
            if data:
                item = json.loads(data)
                mappings[item["placeholder"]] = item["real_value"]
        return mappings

    def get_session_mappings(self, session_id: str) -> Dict[str, str]:
        """获取会话的所有映射"""
        mappings = {}
        session_key = self._get_key(f"session:{session_id}")
        placeholders = self.client.smembers(session_key)

        for placeholder in placeholders:
            real_value = self.get_mapping(session_id, placeholder)
            if real_value:
                mappings[placeholder] = real_value

        return mappings

    def clear_session(self, session_id: str):
        """清除会话映射"""
        session_key = self._get_key(f"session:{session_id}")
        placeholders = self.client.smembers(session_key)

        for placeholder in placeholders:
            key = self._get_key(f"mapping:{session_id}:{placeholder}")
            self.client.delete(key)

        self.client.delete(session_key)
        logger.info(f"[Redis] 清除会话 {session_id}")

    def clear_all_mappings(self):
        """清除所有映射"""
        pattern = self._get_key("*")
        keys = list(self.client.scan_iter(match=pattern))
        if keys:
            self.client.delete(*keys)
        logger.info("[Redis] 清除所有映射")

    def update_stats(self, stats: Dict[str, int]):
        """更新统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        stats_key = self._get_key(f"stats:{today}")

        for data_type, count in stats.items():
            if count > 0:
                self.client.hincrby(stats_key, f"{data_type}_count", count)
                self.client.hincrby(stats_key, "total_count", count)

        self.client.expire(stats_key, 7 * 86400)  # 保留7天

    def get_today_stats(self) -> Dict:
        """获取今日统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        stats_key = self._get_key(f"stats:{today}")

        stats = self.client.hgetall(stats_key)
        return {
            "date": today,
            "phone_count": int(stats.get("phone_count", 0)),
            "email_count": int(stats.get("email_count", 0)),
            "idcard_count": int(stats.get("idcard_count", 0)),
            "bankcard_count": int(stats.get("bankcard_count", 0)),
            "custom_count": int(stats.get("custom_count", 0)),
            "total_count": int(stats.get("total_count", 0))
        }

    def get_week_stats(self) -> List[Dict]:
        """获取7天统计"""
        result = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            stats_key = self._get_key(f"stats:{date_str}")
            stats = self.client.hgetall(stats_key)
            result.append({
                "date": date_str,
                "total_count": int(stats.get("total_count", 0))
            })
        return result

    def add_custom_keyword(self, keyword: str) -> bool:
        """添加自定义敏感词"""
        key = self._get_key("custom_keywords")
        return self.client.sadd(key, keyword) > 0

    def delete_custom_keyword(self, keyword: str) -> bool:
        """删除自定义敏感词"""
        key = self._get_key("custom_keywords")
        return self.client.srem(key, keyword) > 0

    def get_custom_keywords(self) -> List[str]:
        """获取自定义敏感词列表"""
        key = self._get_key("custom_keywords")
        return list(self.client.smembers(key))

    def save_audit_log(self, log_data: Dict):
        """保存审计日志"""
        log_id = f"log_{int(time.time() * 1000)}"
        key = self._get_key(f"audit:{log_id}")
        log_data["log_id"] = log_id
        log_data["created_at"] = datetime.now().isoformat()
        self.client.setex(key, 30 * 86400, json.dumps(log_data))  # 保留30天

        # 添加到日志索引
        index_key = self._get_key("audit_index")
        self.client.lpush(index_key, log_id)
        self.client.ltrim(index_key, 0, 9999)  # 最多保留10000条索引

    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        index_key = self._get_key("audit_index")
        log_ids = self.client.lrange(index_key, 0, limit - 1)

        logs = []
        for log_id in log_ids:
            key = self._get_key(f"audit:{log_id}")
            data = self.client.get(key)
            if data:
                logs.append(json.loads(data))

        return logs

    def health_check(self) -> bool:
        """健康检查"""
        try:
            return self.client.ping()
        except:
            return False


# 全局 Redis 存储实例
redis_storage: Optional[RedisStorage] = None


def get_redis_storage() -> RedisStorage:
    """获取 Redis 存储实例"""
    global redis_storage
    if redis_storage is None:
        redis_storage = RedisStorage()
    return redis_storage


def get_storage():
    """根据配置获取存储引擎"""
    if config.feature_redis_storage:
        return get_redis_storage()
    else:
        from database import db
        return db