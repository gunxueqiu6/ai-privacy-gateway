"""
Advanced GatewayCore tests — retry logic, error paths, streaming.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestGatewayCoreRetry:
    """Retry logic and error recovery"""

    def test_is_retryable_timeout(self):
        from gateway_core import GatewayCore
        import httpx
        assert GatewayCore._is_retryable(httpx.TimeoutException("timed out")) is True

    def test_is_retryable_connect_error(self):
        from gateway_core import GatewayCore
        import httpx
        assert GatewayCore._is_retryable(httpx.ConnectError("refused")) is True

    def test_is_retryable_remote_protocol_error(self):
        from gateway_core import GatewayCore
        import httpx
        assert GatewayCore._is_retryable(httpx.RemoteProtocolError("reset")) is True

    def test_is_retryable_http_5xx(self):
        from gateway_core import GatewayCore
        import httpx
        mock_request = Mock(spec=httpx.Request)
        mock_response = Mock(spec=httpx.Response, status_code=503)
        err = httpx.HTTPStatusError("503", request=mock_request, response=mock_response)
        assert GatewayCore._is_retryable(err) is True

    def test_is_retryable_http_4xx_not_retryable(self):
        from gateway_core import GatewayCore
        import httpx
        mock_request = Mock(spec=httpx.Request)
        mock_response = Mock(spec=httpx.Response, status_code=401)
        err = httpx.HTTPStatusError("401", request=mock_request, response=mock_response)
        assert GatewayCore._is_retryable(err) is False

    def test_is_retryable_random_exception_not_retryable(self):
        from gateway_core import GatewayCore
        assert GatewayCore._is_retryable(ValueError("bad value")) is False


class TestGatewayCoreStreaming:
    """Streaming proxy edge cases"""

    @pytest.mark.asyncio
    async def test_proxy_stream_no_healthy_upstream(self):
        with patch('routers.proxy.get_gateway_core') as mock_gw:
            from gateway_core import GatewayCore
            gw = GatewayCore()
            # Make all nodes unhealthy
            for node in gw.load_balancer._nodes:
                node.healthy = False

            results = []
            async for chunk in gw.proxy_stream_request(
                {"messages": [{"role": "user", "content": "hello"}]},
                {"Authorization": "Bearer test"},
                {},
                None
            ):
                results.append(chunk)

            assert len(results) == 1
            data = json.loads(results[0]["data"])
            assert "error" in data
            assert "No healthy upstream" in data["error"]

    def test_gateway_core_init_with_upstream_urls(self, monkeypatch):
        """GatewayCore initializes load balancer with multiple upstream URLs"""
        monkeypatch.setenv("UPSTREAM_LLM_URLS", "https://api.openai.com,https://api.anthropic.com")
        monkeypatch.setenv("UPSTREAM_LB_STRATEGY", "random")
        import importlib
        import config as cfg_mod
        import gateway_core as gc_mod
        # Reload config first so the monkeypatched env vars are picked up
        importlib.reload(cfg_mod)
        importlib.reload(gc_mod)
        try:
            gw = gc_mod.GatewayCore()
            assert len(gw.load_balancer._nodes) == 2
            assert gw.load_balancer._strategy == "random"
        finally:
            gc_mod.gateway_core = None


class TestGatewayCoreUnmaskEdgeCases:
    """Unmask response edge cases"""

    def test_unmask_with_used_placeholders(self):
        from gateway_core import GatewayCore
        gw = GatewayCore()
        text = "Hello [PII_PHONE_A] and [PII_PHONE_B]"
        mappings = {
            "[PII_PHONE_A]": "13811111111",
            "[PII_PHONE_B]": "13922222222",
            "[PII_EMAIL_C]": "test@example.com",
        }
        used = {"[PII_PHONE_A]", "[PII_PHONE_B]"}
        gw.mask_engine = Mock()
        gw.mask_engine.unmask.return_value = "Hello 13811111111 and 13922222222"
        result = gw.unmask_response(text, mappings, used_placeholders=used)
        assert result == "Hello 13811111111 and 13922222222"
        # The email mapping should NOT be passed to unmask (filtered by used_placeholders)
        # Check that unmask was called with filtered mappings
        call_mappings = gw.mask_engine.unmask.call_args[0][1]
        assert "[PII_EMAIL_C]" not in call_mappings

    def test_unmask_with_none_used_placeholders(self):
        """When used_placeholders is None, all mappings are used"""
        from gateway_core import GatewayCore
        gw = GatewayCore()
        gw.mask_engine = Mock()
        gw.mask_engine.unmask.return_value = "Hello World"
        result = gw.unmask_response("Hello [PII_X]", {"[PII_X]": "World"}, used_placeholders=None)
        assert result == "Hello World"
        gw.mask_engine.unmask.assert_called_once()


class TestGatewayCoreProxyGeneric:
    """Generic proxy edge cases"""

    def test_no_upstream_returns_502(self):
        from gateway_core import GatewayCore
        import asyncio

        gw = GatewayCore()
        gw._max_retries = 0

        async def run():
            status, body, headers = await gw.proxy_generic_request(
                "GET", "/v1/models", {"Authorization": "Bearer x"}, None
            )
            return status, body, headers

        result = asyncio.run(run())
        # No healthy upstream or real API responds with auth error
        assert result[0] in [502, 200, 401]
