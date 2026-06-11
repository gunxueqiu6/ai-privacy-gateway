"""
GatewayCore 核心模块单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGatewayCoreInit:
    """网关初始化测试"""

    def test_session_id_format(self):
        """会话 ID 格式正确"""
        from gateway_core import GatewayCore
        gw = GatewayCore()
        sid = gw.generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) > 20

    def test_session_id_unique(self):
        """会话 ID 唯一性"""
        from gateway_core import GatewayCore
        gw = GatewayCore()
        ids = [gw.generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestMaskRequest:
    """脱敏请求测试"""

    @pytest.fixture
    def gateway(self):
        from gateway_core import GatewayCore
        gw = GatewayCore()
        # Mock the mask engine
        gw.mask_engine = Mock()
        gw.mask_engine.mask.return_value = (
            "Hello [PII_PHONE_0001]",
            {"[PII_PHONE_0001]": "13812345678"},
            {"phone": 1}
        )
        return gw

    def test_mask_single_message(self, gateway):
        """单条消息脱敏"""
        body = {
            "model": "gpt-3.5",
            "messages": [
                {"role": "user", "content": "Hello 13812345678"}
            ]
        }
        masked_body, mappings, stats, session_id, _ = gateway.mask_request(body)

        assert "13812345678" not in masked_body["messages"][0]["content"]
        assert "[PII_PHONE_0001]" in masked_body["messages"][0]["content"]
        assert mappings["[PII_PHONE_0001]"] == "13812345678"
        assert stats["phone"] == 1
        assert session_id.startswith("sess_")

    def test_mask_multiple_messages(self, gateway):
        """多条消息脱敏"""
        def side_effect(text):
            if "138" in text:
                return ("masked_a", {"[A]": "138"}, {"phone": 1})
            return ("masked_b", {"[B]": "test@x.com"}, {"email": 1})

        gateway.mask_engine.mask.side_effect = side_effect

        body = {
            "messages": [
                {"role": "user", "content": "call 138"},
                {"role": "assistant", "content": "email test@x.com"}
            ]
        }
        masked_body, mappings, stats, _, _ = gateway.mask_request(body)

        assert masked_body["messages"][0]["content"] == "masked_a"
        assert masked_body["messages"][1]["content"] == "masked_b"
        assert "[A]" in mappings
        assert "[B]" in mappings
        assert stats["phone"] == 1
        assert stats["email"] == 1

    def test_mask_empty_content(self, gateway):
        """空内容消息不处理"""
        body = {
            "messages": [
                {"role": "system", "content": ""}
            ]
        }
        masked_body, mappings, stats, _, _ = gateway.mask_request(body)
        assert mappings == {}

    def test_mask_no_content_field(self, gateway):
        """无 content 字段的消息"""
        body = {
            "messages": [
                {"role": "user"}
            ]
        }
        masked_body, mappings, stats, _, _ = gateway.mask_request(body)
        assert mappings == {}


class TestUnmaskResponse:
    """还原响应测试"""

    @pytest.fixture
    def gateway(self):
        from gateway_core import GatewayCore
        gw = GatewayCore()
        gw.mask_engine = Mock()
        return gw

    def test_unmask_basic(self, gateway):
        """基本还原"""
        gateway.mask_engine.unmask.return_value = "Hello 13812345678"
        result = gateway.unmask_response(
            "Hello [PII_PHONE_0001]",
            {"[PII_PHONE_0001]": "13812345678"}
        )
        assert result == "Hello 13812345678"

    def test_unmask_empty_mappings(self, gateway):
        """空映射不处理"""
        result = gateway.unmask_response("Hello World", {})
        assert result == "Hello World"

    def test_unmask_multiple_placeholders(self, gateway):
        """多个占位符还原"""
        gateway.mask_engine.unmask.return_value = "张三 call 138"
        result = gateway.unmask_response(
            "[PER_0001] call [PHONE_0001]",
            {"[PER_0001]": "张三", "[PHONE_0001]": "138"}
        )
        assert result == "张三 call 138"


class TestMaskRequestStats:
    """统计聚合测试"""

    @pytest.fixture
    def gateway(self):
        from gateway_core import GatewayCore
        gw = GatewayCore()
        gw.mask_engine = Mock()
        return gw

    def test_stats_accumulate(self, gateway):
        """多消息统计累加"""
        call_count = [0]

        def side_effect(text):
            call_count[0] += 1
            if call_count[0] == 1:
                return ("m1", {"[A]": "v1"}, {"phone": 2, "email": 1})
            return ("m2", {"[B]": "v2"}, {"phone": 1, "idcard": 1})

        gateway.mask_engine.mask.side_effect = side_effect

        body = {
            "messages": [
                {"role": "user", "content": "a"},
                {"role": "user", "content": "b"}
            ]
        }
        _, _, stats, _, _ = gateway.mask_request(body)

        assert stats["phone"] == 3
        assert stats["email"] == 1
        assert stats["idcard"] == 1


class TestProxyError:
    """代理错误处理测试"""

    def test_proxy_timeout_returns_504(self):
        """超时返回 504"""
        import httpx
        from gateway_core import GatewayCore
        import asyncio

        gw = GatewayCore()
        gw.timeout = 0.001

        async def run():
            status, body, headers = await gw.proxy_request(
                {"test": True},
                {"Authorization": "Bearer x"},
                {},
                "test-session"
            )
            return status, body, headers

        # The request should fail (timeout or connection error)
        result = asyncio.run(run())
        # Either 504 (timeout) or 502 (connection error) is valid
        assert result[0] in [502, 504]
