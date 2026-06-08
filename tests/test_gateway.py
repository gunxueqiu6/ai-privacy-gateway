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

    def test_custom_keyword_add_duplicate(self):
        """添加重复自定义敏感词返回 False"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        kw = "重复词"
        assert engine.add_custom_keyword(kw) is True
        assert engine.add_custom_keyword(kw) is False  # 重复
        engine.remove_custom_keyword(kw)

    def test_custom_keyword_remove_nonexistent(self):
        """删除不存在的敏感词返回 False"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        assert engine.remove_custom_keyword("不存在的词") is False

    def test_custom_keyword_add_empty(self):
        """空关键词不添加"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        assert engine.add_custom_keyword("") is False

    def test_get_custom_keywords(self):
        """获取自定义敏感词列表返回副本"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        engine.add_custom_keyword("测试词")
        keywords = engine.get_custom_keywords()
        assert "测试词" in keywords
        # 验证返回的是副本
        keywords.append("篡改")
        assert "篡改" not in engine.get_custom_keywords()
        engine.remove_custom_keyword("测试词")

    def test_plate_mask(self):
        """测试车牌号脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "车牌号是京A12345"
        masked, mappings, stats = engine.mask(text)
        assert "京A12345" not in masked

    def test_ip_mask(self):
        """测试IP地址脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "IP是192.168.1.1"
        masked, mappings, stats = engine.mask(text)
        assert "192.168.1.1" not in masked

    def test_url_mask(self):
        """测试URL脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "访问 https://example.com/page 查看"
        masked, mappings, stats = engine.mask(text)
        assert "https://example.com/page" not in masked

    def test_date_mask(self):
        """测试日期脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "日期是2024-01-15"
        masked, mappings, stats = engine.mask(text)
        assert "2024-01-15" not in masked

    def test_amount_mask(self):
        """测试金额脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "金额¥1,234.56元"
        masked, mappings, stats = engine.mask(text)
        assert "¥1,234.56" not in masked

    def test_postcode_mask(self):
        """测试邮编脱敏"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "邮编100081"
        masked, mappings, stats = engine.mask(text)
        assert "100081" not in masked

    def test_unmask_no_mappings(self):
        """无映射还原返回原文本"""
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        result = engine.unmask("[PII_PHONE_xxx]", {})
        assert "[PII_PHONE_xxx]" in result


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

    def test_feed_done(self):
        """data: [DONE] 触发完成状态"""
        from stream_buffer import StreamBuffer, StreamState

        buffer = StreamBuffer()
        chunks = buffer.feed("data: [DONE]")

        assert buffer.state == StreamState.DONE
        assert len(chunks) == 1
        assert chunks[0].event == 'done'
        assert chunks[0].data == '[DONE]'

    def test_feed_comment_skip(self):
        """: 开头的注释行被忽略"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        chunks = buffer.feed(": this is a comment\n")

        assert len(chunks) == 0

    def test_feed_event_line_skip(self):
        """event: 行被忽略"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        chunks = buffer.feed("event: ping\n")

        assert len(chunks) == 0

    def test_process_chunk_unmask(self):
        """process_chunk 调用 unmask_func 还原占位符"""
        from stream_buffer import StreamBuffer, StreamChunk

        buffer = StreamBuffer()
        buffer.mappings = {"[PII_PHONE_x]": "13812345678"}

        chunk = StreamChunk(event='message', data='call [PII_PHONE_x]', raw='data: call [PII_PHONE_x]', index=0)
        result = buffer.process_chunk(chunk, unmask_func=lambda data, mappings: data.replace("[PII_PHONE_x]", mappings["[PII_PHONE_x]"]))

        assert result.data == "call 13812345678"

    def test_process_chunk_done_returns_as_is(self):
        """done 事件的 chunk 原样返回"""
        from stream_buffer import StreamBuffer, StreamChunk

        buffer = StreamBuffer()
        chunk = StreamChunk(event='done', data='[DONE]', raw='data: [DONE]', index=0)
        result = buffer.process_chunk(chunk, unmask_func=lambda d, m: d)

        assert result.event == 'done'
        assert result.data == '[DONE]'

    def test_flush_returns_full_data(self):
        """flush 返回完整拼接数据"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        buffer.feed("data: hello")
        buffer.feed("data: world")
        result = buffer.flush()

        assert "hello" in result
        assert "world" in result
        assert buffer.is_done()

    def test_is_done_and_is_error(self):
        """状态检查"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        assert not buffer.is_done()
        assert not buffer.is_error()

        buffer.set_error("test error")
        assert buffer.is_error()

    def test_set_mappings(self):
        """设置映射表"""
        from stream_buffer import StreamBuffer

        buffer = StreamBuffer()
        mappings = {"[PII]": "secret"}
        buffer.set_mappings(mappings)
        assert buffer.mappings["[PII]"] == "secret"


class TestStreamProcessor:
    """流式处理器测试"""

    def test_process_stream_basic(self):
        """处理基本流式数据"""
        from stream_buffer import create_stream_processor

        def fake_unmask(data, mappings):
            return data

        processor = create_stream_processor(fake_unmask)

        stream = iter(["data: Hello\n\n", "data: World\n\n"])
        results = list(processor.process_stream(stream))

        assert len(results) > 0
        assert any("Hello" in r for r in results)
        assert any("World" in r for r in results)

    def test_process_stream_with_done(self):
        """流式数据遇 [DONE] 停止"""
        from stream_buffer import create_stream_processor

        def fake_unmask(data, mappings):
            return data

        processor = create_stream_processor(fake_unmask)
        stream = iter(["data: [DONE]\n\n"])
        results = list(processor.process_stream(stream))

        assert any("[DONE]" in r for r in results)

    def test_create_stream_processor(self):
        """工厂函数创建 StreamProcessor"""
        from stream_buffer import create_stream_processor

        processor = create_stream_processor(lambda d, m: d)
        assert processor is not None
        assert processor.buffer is not None


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

    def test_add_duplicate_keyword(self):
        """重复添加自定义敏感词不抛异常"""
        from database import db
        kw = "重复敏感词"
        db.add_custom_keyword(kw)
        # 重复添加应返回 False 且不抛异常
        result = db.add_custom_keyword(kw)
        assert result is False
        db.delete_custom_keyword(kw)

    def test_clear_all_mappings(self):
        """清除所有映射"""
        from database import db
        db.save_mappings("test_clear", {"[TEST_x]": "val"}, "test")
        # 确认有数据
        mappings = db.get_all_mappings()
        assert len(mappings) > 0
        db.clear_all_mappings()

    def test_get_all_mappings(self):
        """获取所有映射返回字典"""
        from database import db
        db.save_mappings("test_all", {"[TEST_y]": "hello"}, "test")
        mappings = db.get_all_mappings()
        assert "[TEST_y]" in mappings
        assert mappings["[TEST_y]"] == "hello"
        db.clear_session("test_all")

    def test_update_stats(self):
        """更新统计数据（重建表以获得新 schema）"""
        from database import db
        # 确保 stats 表有全部列
        with db.get_conn() as conn:
            conn.execute("DROP TABLE IF EXISTS stats")
            conn.execute("""
                CREATE TABLE stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    phone_count INTEGER DEFAULT 0,
                    email_count INTEGER DEFAULT 0,
                    idcard_count INTEGER DEFAULT 0,
                    bankcard_count INTEGER DEFAULT 0,
                    custom_count INTEGER DEFAULT 0,
                    person_count INTEGER DEFAULT 0,
                    location_count INTEGER DEFAULT 0,
                    org_count INTEGER DEFAULT 0,
                    plate_count INTEGER DEFAULT 0,
                    ip_count INTEGER DEFAULT 0,
                    url_count INTEGER DEFAULT 0,
                    date_count INTEGER DEFAULT 0,
                    amount_count INTEGER DEFAULT 0,
                    postcode_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0
                )
            """)
        stats = {"phone": 2, "email": 1}
        db.update_stats(stats)

    def test_get_today_stats_with_data(self):
        """获取今日统计数据（有数据时）"""
        from database import db
        db.update_stats({"phone": 1})
        stats = db.get_today_stats()
        assert "phone_count" in stats
        assert "date" in stats


class TestMaskEngineRegexFallback:
    """正则 fallback 路径测试（模拟 NER 不可用）"""

    def test_regex_fallback_all_entities(self):
        """NER 不可用时正则引擎覆盖所有实体类型"""
        import mask_engine
        from mask_engine import RegexMaskEngine
        saved = mask_engine.HAS_NER
        mask_engine.HAS_NER = False
        try:
            engine = RegexMaskEngine()
            text = "手机13812345678 邮箱 test@example.com 身份证110101199001011234 银行卡6222021234567890123 车牌京A12345 IP192.168.1.1 网址 https://example.com 日期2024-01-15 金额¥1,234.56 邮编100081"
            masked, mappings, stats = engine.mask(text)
            assert "13812345678" not in masked
            assert "test@example.com" not in masked
            assert "110101199001011234" not in masked
            assert "6222021234567890123" not in masked
            assert "京A12345" not in masked
            assert "192.168.1.1" not in masked
            assert "https://example.com" not in masked
            assert "2024-01-15" not in masked
            assert "¥1,234.56" not in masked
            assert "100081" not in masked
        finally:
            mask_engine.HAS_NER = saved


class TestMaskEngineEdgeCases:
    """脱敏引擎边界条件"""

    def test_bankcard_skips_11digit_phone(self):
        """银行卡正则跳过 11 位手机号"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        # 11 位且以 1 开头的数字被银行卡正则跳过（防止与手机号重复）
        text = "卡号13812345678"
        masked, mappings, stats = engine.mask(text)
        # 13812345678 作为手机号脱敏，不额外作为银行卡
        assert stats.get("bankcard", 0) == 0

    def test_create_mask_engine_loads_db_keywords(self):
        """create_mask_engine 从数据库加载自定义关键词"""
        from database import db, Database
        from mask_engine import create_mask_engine

        # 先写入一个测试关键词
        db.add_custom_keyword("create_test_kw")
        try:
            engine = create_mask_engine()
            keywords = engine.get_custom_keywords()
            assert "create_test_kw" in keywords
        finally:
            db.delete_custom_keyword("create_test_kw")

    def test_multi_line_with_blank(self):
        """多行含空行也能正常脱敏"""
        from mask_engine import get_mask_engine

        engine = get_mask_engine()
        text = "第一行\n\n手机号13812345678\n\n最后一行"
        masked, mappings, stats = engine.mask(text)
        assert "13812345678" not in masked
        assert stats["phone"] >= 1


class TestDatabaseEdge:
    """数据库边界测试"""

    def test_check_login_attempt_new_ip(self):
        """新 IP 检查登录返回不锁定"""
        from database import db
        is_locked, remaining = db.check_login_attempt("192.168.99.1")
        assert not is_locked
        assert remaining == 5

    def test_record_failed_login(self):
        """记录失败登录增加计数"""
        from database import db
        ip = "192.168.88.1"
        db.record_login_attempt(ip, success=False)
        try:
            is_locked, remaining = db.check_login_attempt(ip)
            assert not is_locked
            assert remaining == 4
        finally:
            # 清理
            db.record_login_attempt(ip, success=True)

    def test_record_login_success_clears_attempts(self):
        """登录成功后清除尝试记录"""
        from database import db
        ip = "192.168.77.1"
        db.record_login_attempt(ip, success=False)
        db.record_login_attempt(ip, success=True)
        is_locked, remaining = db.check_login_attempt(ip)
        assert not is_locked
        assert remaining == 5

    def test_log_audit(self):
        """审计日志写入"""
        from database import db
        db.log_audit("test_session_audit", "mask", {"count": 42})
        # 不抛异常即成功


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
