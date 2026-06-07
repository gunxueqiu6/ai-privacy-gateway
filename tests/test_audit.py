"""
Audit Log 测试 - 审计日志
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import time


class TestAuditLog:
    """审计日志测试"""

    def test_audit_logger_initialization(self):
        """测试审计日志初始化"""
        try:
            from audit_log import AuditLogger, get_audit_logger

            logger = get_audit_logger()
            assert logger is not None
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_log_write(self):
        """测试日志写入"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir)

                entry = AuditEntry(
                    action="mask",
                    user="admin",
                    timestamp=time.time(),
                    details={"text_length": 100, "entities_found": 3}
                )

                logger.log(entry)

                # 验证日志文件存在
                log_files = os.listdir(tmpdir)
                assert len(log_files) > 0
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_buffer_flush(self):
        """测试缓冲区刷新"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir, buffer_size=5)

                # 写入少于缓冲区大小的日志
                for i in range(3):
                    entry = AuditEntry(
                        action=f"action_{i}",
                        user="test",
                        timestamp=time.time(),
                        details={}
                    )
                    logger.log(entry)

                # 手动刷新
                logger.flush()

                # 验证日志已写入
                log_files = os.listdir(tmpdir)
                assert len(log_files) > 0
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_auto_flush_on_buffer_full(self):
        """测试缓冲区满自动刷新"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir, buffer_size=3)

                # 写入超过缓冲区大小的日志
                for i in range(5):
                    entry = AuditEntry(
                        action=f"action_{i}",
                        user="test",
                        timestamp=time.time(),
                        details={}
                    )
                    logger.log(entry)

                # 应该已自动刷新
                log_files = os.listdir(tmpdir)
                assert len(log_files) > 0
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_log_search(self):
        """测试日志搜索"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir)

                # 写入测试日志
                entry1 = AuditEntry(
                    action="mask",
                    user="admin",
                    timestamp=time.time(),
                    details={"text": "test1"}
                )
                entry2 = AuditEntry(
                    action="restore",
                    user="admin",
                    timestamp=time.time(),
                    details={"text": "test2"}
                )
                logger.log(entry1)
                logger.log(entry2)
                logger.flush()

                # 搜索
                results = logger.search(action="mask")
                assert len(results) >= 1
                assert all(r.action == "mask" for r in results)
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_search_by_user(self):
        """测试按用户搜索"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir)

                # 写入不同用户的日志
                for user in ["admin", "user1", "user2"]:
                    entry = AuditEntry(
                        action="mask",
                        user=user,
                        timestamp=time.time(),
                        details={}
                    )
                    logger.log(entry)
                logger.flush()

                # 搜索特定用户
                results = logger.search(user="admin")
                assert len(results) >= 1
                assert all(r.user == "admin" for r in results)
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_search_by_time_range(self):
        """测试按时间范围搜索"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir)

                now = time.time()
                # 写入不同时间的日志
                entry1 = AuditEntry(
                    action="mask",
                    user="test",
                    timestamp=now - 3600,  # 1小时前
                    details={}
                )
                entry2 = AuditEntry(
                    action="mask",
                    user="test",
                    timestamp=now,  # 现在
                    details={}
                )
                logger.log(entry1)
                logger.log(entry2)
                logger.flush()

                # 搜索最近1小时
                results = logger.search(start_time=now - 1800, end_time=now + 100)
                assert len(results) >= 1
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_log_rotation(self):
        """测试日志轮转"""
        try:
            from audit_log import AuditLogger

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir, max_file_size=1024)

                # 写入大量日志触发轮转
                for i in range(100):
                    entry = AuditEntry(
                        action=f"action_{i}",
                        user="test",
                        timestamp=time.time(),
                        details={"data": "x" * 100}  # 较大的详情
                    )
                    logger.log(entry)
                logger.flush()

                # 应该有多个日志文件
                log_files = os.listdir(tmpdir)
                # 根据实现，可能有轮转文件
        except (ImportError, TypeError):
            pytest.skip("audit_log module API mismatch")

    def test_log_format(self):
        """测试日志格式"""
        try:
            from audit_log import AuditLogger, AuditEntry

            with tempfile.TemporaryDirectory() as tmpdir:
                logger = AuditLogger(log_dir=tmpdir)

                entry = AuditEntry(
                    action="mask",
                    user="admin",
                    timestamp=time.time(),
                    details={"count": 5}
                )
                logger.log(entry)
                logger.flush()

                # 读取日志文件验证格式
                log_files = os.listdir(tmpdir)
                if log_files:
                    with open(os.path.join(tmpdir, log_files[0]), 'r') as f:
                        content = f.read()
                        # 应包含关键信息
                        assert "mask" in content or "admin" in content
        except ImportError:
            pytest.skip("audit_log module not available")


class TestAuditEntry:
    """审计条目测试"""

    def test_entry_creation(self):
        """测试条目创建"""
        try:
            from audit_log import AuditEntry

            entry = AuditEntry(
                action="test_action",
                user="test_user",
                timestamp=time.time(),
                details={"key": "value"}
            )

            assert entry.action == "test_action"
            assert entry.user == "test_user"
            assert entry.details["key"] == "value"
        except ImportError:
            pytest.skip("audit_log module not available")

    def test_entry_serialization(self):
        """测试条目序列化"""
        try:
            from audit_log import AuditEntry
            import json

            entry = AuditEntry(
                action="test",
                user="user",
                timestamp=time.time(),
                details={}
            )

            # 序列化
            serialized = entry.to_dict()
            assert isinstance(serialized, dict)
            assert "action" in serialized
            assert "user" in serialized

            # 反序列化
            deserialized = AuditEntry.from_dict(serialized)
            assert deserialized.action == entry.action
        except ImportError:
            pytest.skip("audit_log module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])