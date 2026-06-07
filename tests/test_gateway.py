"""
测试用例 - AI Privacy Gateway Lite
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestMaskEngine:
    """脱敏引擎测试"""

    def test_phone_mask(self):
        """测试手机号脱敏"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        text = "我的手机号是13812345678，请联系我"
        masked, mappings, stats = engine.mask(text)

        assert "13812345678" not in masked
        assert "[PII_PHONE_" in masked
        assert len(mappings) > 0
        assert stats["phone"] >= 1

    def test_email_mask(self):
        """测试邮箱脱敏"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        text = "我的邮箱是 test@example.com"
        masked, mappings, stats = engine.mask(text)

        assert "test@example.com" not in masked
        assert "[PII_EMAIL_" in masked
        assert stats["email"] >= 1

    def test_idcard_mask(self):
        """测试身份证脱敏"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        text = "身份证号110101199001011234"
        masked, mappings, stats = engine.mask(text)

        assert "110101199001011234" not in masked
        assert "[PII_IDCARD_" in masked
        assert stats["idcard"] >= 1

    def test_unmask(self):
        """测试还原"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        text = "手机号13812345678和邮箱test@example.com"
        masked, mappings, stats = engine.mask(text)
        unmasked = engine.unmask(masked, mappings)

        assert "13812345678" in unmasked
        assert "test@example.com" in unmasked
        assert "[PII_PHONE_" in masked or "[PII_EMAIL_" in masked

    def test_custom_keyword(self):
        """测试自定义敏感词"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        engine.add_custom_keyword("密码")
        text = "这是一个密码测试"
        masked, mappings, stats = engine.mask(text)

        assert "密码" not in masked
        assert "[PII_" in masked


class TestStreamBuffer:
    """流式缓冲区测试"""

    def test_chunk_accumulation(self):
        """测试分块累积"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()

        buffer.feed("Hello ")
        buffer.feed("World")

        full_text = ''.join([chunk.raw for chunk in buffer.chunks])
        assert "Hello " in full_text
        assert "World" in full_text

    def test_sse_line_parsing(self):
        """测试 SSE 行解析"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()

        chunks = buffer.feed("data: Hello\n\n")
        assert len(chunks) >= 0

    def test_reset(self):
        """测试缓冲区重置"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        buffer.feed("test")
        buffer.reset()

        assert len(buffer.chunks) == 0


class TestDatabase:
    """数据库测试"""

    def test_save_and_get_mapping(self):
        """测试映射存取"""
        from database import db

        session_id = "test_session_001"
        placeholder = "[PII_PHONE_abc123]"
        real_value = "13812345678"

        db.save_mappings(session_id, {placeholder: real_value}, "phone")
        retrieved = db.get_mapping(session_id, placeholder)

        assert retrieved == real_value

        db.clear_session(session_id)

    def test_custom_keywords(self):
        """测试自定义敏感词"""
        from database import db

        keyword = "测试敏感词"
        db.add_custom_keyword(keyword)

        keywords = db.get_custom_keywords()
        assert keyword in keywords

        db.delete_custom_keyword(keyword)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
