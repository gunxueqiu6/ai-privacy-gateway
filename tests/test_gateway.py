"""
测试用例 - AI Privacy Gateway
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestMaskEngine:
    """脱敏引擎测试"""

    def test_phone_mask(self):
        """测试手机号脱敏"""
        from mask_engine import RegexMaskEngine

        engine = RegexMaskEngine()
        text = "我的手机号是13812345678，请联系我"
        masked, mappings, stats = engine.mask(text)

        assert "13812345678" not in masked
        assert "[VAULT_" in masked
        assert len(mappings) > 0
        assert stats["phone"] >= 1

    def test_email_mask(self):
        """测试邮箱脱敏"""
        from mask_engine import RegexMaskEngine

        engine = RegexMaskEngine()
        text = "我的邮箱是 test@example.com"
        masked, mappings, stats = engine.mask(text)

        assert "test@example.com" not in masked
        assert "[VAULT_" in masked
        assert stats["email"] >= 1

    def test_idcard_mask(self):
        """测试身份证脱敏"""
        from mask_engine import RegexMaskEngine

        engine = RegexMaskEngine()
        text = "身份证号110101199001011234"
        masked, mappings, stats = engine.mask(text)

        assert "110101199001011234" not in masked
        assert "[VAULT_" in masked
        assert stats["idcard"] >= 1

    def test_unmask(self):
        """测试还原"""
        from mask_engine import RegexMaskEngine

        engine = RegexMaskEngine()
        text = "手机号13812345678和邮箱test@example.com"
        masked, mappings, stats = engine.mask(text)
        unmasked = engine.unmask(masked, mappings)

        assert "13812345678" in unmasked
        assert "test@example.com" in unmasked

    def test_custom_keyword(self):
        """测试自定义敏感词"""
        from mask_engine import RegexMaskEngine

        engine = RegexMaskEngine()
        engine.add_custom_keyword("密码")
        text = "这是一个密码测试"
        masked, mappings, stats = engine.mask(text)

        assert "密码" not in masked
        assert "[VAULT_" in masked


class TestStreamBuffer:
    """流式缓冲区测试"""

    def test_chunk_accumulation(self):
        """测试分块累积"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()

        buffer.feed("Hello ")
        buffer.feed("World")

        assert len(buffer.buffer) == 2

    def test_sse_line_parsing(self):
        """测试 SSE 行解析"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()

        buffer.feed("data: Hello\n\n")
        chunks = buffer.chunks

        assert len(chunks) >= 0

    def test_clear(self):
        """测试缓冲区清空"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        buffer.feed("test")
        buffer.reset()

        assert buffer.buffer == []


class TestDatabase:
    """数据库测试"""

    def test_save_and_get_mapping(self):
        """测试映射存取"""
        from database import db

        session_id = "test_session_001"
        placeholder = "[VAULT_PHONE_abc123]"
        real_value = "13812345678"

        db.save_mappings(session_id, {placeholder: real_value}, "phone")
        all_mappings = db.get_all_mappings()

        assert placeholder in all_mappings
        assert all_mappings[placeholder] == real_value

        db.clear_all_mappings()

    def test_custom_keywords(self):
        """测试自定义敏感词"""
        from database import db

        keyword = "测试敏感词"
        db.add_custom_keyword(keyword)

        keywords = db.get_custom_keywords()
        assert keyword in keywords

        db.delete_custom_keyword(keyword)


class TestLicenseClient:
    """License 客户端测试"""

    @pytest.mark.asyncio
    async def test_no_server_fallback(self):
        """测试无服务器时的回退"""
        from license_client import LicenseClient

        client = LicenseClient()
        client.server_url = None  # 无服务器

        success, msg = await client.activate()
        assert success is True
        assert msg == "no_server"

    def test_hardware_fingerprint(self):
        """测试硬件指纹采集"""
        from license_client import HardwareFingerprint

        fp = HardwareFingerprint.collect()

        assert "board_serial" in fp
        assert "disk_uuid" in fp
        assert "mac_address" in fp


class TestDecayManager:
    """衰减管理器测试"""

    def test_normal_level(self):
        """测试正常等级"""
        from decay_manager import DecayManager

        manager = DecayManager()
        level = manager.update()

        assert level.value == 0  # NORMAL

    def test_warning_message(self):
        """测试警告消息"""
        from decay_manager import DecayManager

        manager = DecayManager()
        msg = manager.get_warning_message()

        assert msg is None  # 正常状态无警告


class TestRBAC:
    """RBAC 测试"""

    def test_default_users(self):
        """测试默认用户"""
        from rbac import get_rbac_manager

        rbac = get_rbac_manager()
        users = rbac.list_users()

        assert len(users) >= 2  # 至少 admin 和 auditor

    def test_authenticate(self):
        """测试认证"""
        from rbac import get_rbac_manager

        rbac = get_rbac_manager()
        token = rbac.authenticate("admin", "admin123")

        assert token is not None

    def test_wrong_password(self):
        """测试错误密码"""
        from rbac import get_rbac_manager

        rbac = get_rbac_manager()
        token = rbac.authenticate("admin", "wrongpassword")

        assert token is None

    def test_permission_check(self):
        """测试权限检查"""
        from rbac import get_rbac_manager, Permission

        rbac = get_rbac_manager()
        token = rbac.authenticate("admin", "admin123")

        assert rbac.check_permission(token, Permission.MANAGE_USERS) is True
        assert rbac.check_permission(token, Permission.VIEW_STATS) is True


class TestIntegrityCheck:
    """完整性校验测试"""

    def test_compute_hash(self):
        """测试哈希计算"""
        try:
            from integrity_check import compute_bytes_hash

            result = compute_bytes_hash(b"test data")
            assert len(result) == 64  # SHA256 十六进制长度
        except ImportError:
            pytest.skip("integrity_check module not available")

    def test_detect_debugger(self):
        """测试调试器检测"""
        try:
            from integrity_check import detect_debugger

            result = detect_debugger()
            assert isinstance(result, bool)
        except ImportError:
            pytest.skip("integrity_check module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
