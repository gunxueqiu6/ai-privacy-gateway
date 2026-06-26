"""
End-to-end integration test — full PII masking pipeline.

Tests the complete flow from API request through masking, proxying,
unmasking, and admin endpoints.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, ANY
from fastapi.testclient import TestClient
from routers.dependencies import reset_limiter


class TestE2EMaskEndpoints:
    """E2E tests for /api/mask endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_mask_phone_and_email(self, client):
        """PII phone and email are masked in request text"""
        response = client.post(
            "/api/mask",
            json={"text": "请联系手机13812345678或邮箱test@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "13812345678" not in data["masked_text"]
        assert "test@example.com" not in data["masked_text"]
        assert "[PII_PHONE_" in data["masked_text"]
        assert "[PII_EMAIL_" in data["masked_text"]
        assert len(data["entities"]) >= 2

    def test_mask_idcard_and_bankcard(self, client):
        """ID card and bank card numbers are masked"""
        response = client.post(
            "/api/mask",
            json={"text": "身份证110101199001011234 银行卡6222021234567890123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "110101199001011234" not in data["masked_text"]
        assert "6222021234567890123" not in data["masked_text"]

    def test_mask_with_custom_keywords(self, client):
        """Custom keywords supplied in request body are used for masking"""
        response = client.post(
            "/api/mask",
            json={
                "text": "This is my API_KEY_12345 value",
                "custom_keywords": ["API_KEY_12345"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "API_KEY_12345" not in data["masked_text"]
        assert "[PII_CUSTOM_" in data["masked_text"]

    def test_mask_empty_text_returns_400(self, client):
        """Empty text returns 400 error"""
        response = client.post(
            "/api/mask",
            json={"text": ""}
        )
        assert response.status_code == 400

    def test_mask_very_long_text(self, client):
        """Very long text is handled properly"""
        long_text = "手机13812345678 " * 1000
        response = client.post(
            "/api/mask",
            json={"text": long_text}
        )
        assert response.status_code == 200
        data = response.json()
        assert "13812345678" not in data["masked_text"]

    def test_mask_no_pii(self, client):
        """Text with no PII is returned unchanged"""
        response = client.post(
            "/api/mask",
            json={"text": "Hello, this is normal text with no sensitive data."}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["masked_text"] == "Hello, this is normal text with no sensitive data."
        assert len(data["entities"]) == 0

    def test_mask_chinese_no_pii(self, client):
        """Chinese text with no PII is returned unchanged"""
        response = client.post(
            "/api/mask",
            json={"text": "这是一段普通的中文文本，不包含敏感信息。"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "敏感信息" in data["masked_text"]


class TestE2ERestoreEndpoints:
    """E2E tests for /api/restore endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_restore_full_roundtrip(self, client):
        """Full mask → restore roundtrip recovers original text"""
        original = "张三的手机号是13812345678，邮箱test@example.com"

        # Mask
        mask_resp = client.post("/api/mask", json={"text": original})
        assert mask_resp.status_code == 200
        mask_data = mask_resp.json()

        # Build mappings from entity list
        mappings = {e["placeholder"]: e["value"] for e in mask_data["entities"]}

        # Restore
        restore_resp = client.post(
            "/api/restore",
            json={"text": mask_data["masked_text"], "mappings": mappings}
        )
        assert restore_resp.status_code == 200
        restore_data = restore_resp.json()
        assert restore_data["original_text"] == original

    def test_restore_empty_text_returns_400(self, client):
        """Empty text returns 400"""
        response = client.post(
            "/api/restore",
            json={"text": "", "mappings": {}}
        )
        assert response.status_code == 400

    def test_restore_no_mappings(self, client):
        """Restore with no mappings returns text unchanged"""
        response = client.post(
            "/api/restore",
            json={"text": "some text", "mappings": {}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "some text"


class TestE2EBatchMask:
    """E2E tests for /api/mask/batch endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_batch_mask_multiple_texts(self, client):
        """Batch mask handles multiple texts"""
        response = client.post(
            "/api/mask/batch",
            json={"texts": [
                "手机13812345678",
                "邮箱test@example.com",
                "普通文本"
            ]}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert "13812345678" not in data["results"][0]["masked"]
        assert "test@example.com" not in data["results"][1]["masked"]
        assert data["results"][2]["masked"] == "普通文本"

    def test_batch_mask_limit_exceeded_400(self, client):
        """More than 50 texts returns 400"""
        texts = [f"文本{i}" for i in range(60)]
        response = client.post("/api/mask/batch", json={"texts": texts})
        assert response.status_code == 400

    def test_batch_mask_empty_list_400(self, client):
        """Empty list returns 400"""
        response = client.post("/api/mask/batch", json={"texts": []})
        assert response.status_code == 400

    def test_batch_mask_single_text_too_long(self, client):
        """Single text over 100KB returns 413"""
        long_text = "x" * 200000
        response = client.post(
            "/api/mask/batch",
            json={"texts": [long_text]}
        )
        assert response.status_code == 413


class TestE2EEntities:
    """E2E tests for /api/entities endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_get_entities(self, client):
        """Returns supported entity types"""
        response = client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert data["total"] >= 10
        types = {e["type"] for e in data["entities"]}
        assert "PII_PHONE" in types
        assert "PII_EMAIL" in types
        assert "PII_IDCARD" in types
        assert data["version"] == "Lite"


class TestE2EChatCompletions:
    """E2E tests for /v1/chat/completions proxy"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_chat_completion_no_auth_returns_401(self, client):
        """Request without auth returns 401"""
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-3.5", "messages": [{"role": "user", "content": "hello"}]}
        )
        assert response.status_code == 401

    def test_chat_completion_with_auth_proxies(self, client):
        """Request with auth is proxied (masked then forwarded)"""
        with patch('routers.proxy.get_gateway_core') as mock_gw:
            mock_core = Mock()
            mock_core.mask_request.return_value = (
                {"model": "gpt-3.5", "messages": [{"role": "user", "content": "[PII_PHONE_A]"}]},
                {"[PII_PHONE_A]": "13812345678"},
                {"phone": 1},
                "test-sess-e2e",
                {"[PII_PHONE_A]"}
            )
            mock_core.proxy_request = AsyncMock(return_value=(
                200,
                json.dumps({
                    "id": "chatcmpl-e2e",
                    "choices": [{"message": {"content": "回复内容 [PII_PHONE_A]"}}]
                }).encode(),
                {"content-type": "application/json"}
            ))
            mock_core.unmask_response = Mock(return_value="回复内容 13812345678")
            mock_gw.return_value = mock_core

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "我的手机号是13812345678"}]
                },
                headers={"Authorization": "Bearer test-key"}
            )

            assert response.status_code == 200
            data = response.json()
            # Verify unmasked content in response
            assert "content" in data["choices"][0]["message"]

    def test_chat_completion_streaming_mocks(self, client):
        """Streaming chat completion is handled correctly"""
        with patch('routers.proxy.get_gateway_core') as mock_gw:
            mock_core = Mock()
            mock_core.mask_request.return_value = (
                {"model": "gpt-3.5", "messages": [{"role": "user", "content": "[PII_PHONE_A]"}]},
                {"[PII_PHONE_A]": "13812345678"},
                {"phone": 1},
                "test-sess-stream",
                {"[PII_PHONE_A]"}
            )

            async def mock_stream(*args, **kwargs):
                yield {"data": json.dumps({"choices": [{"delta": {"content": "你好"}}]})}
                yield {"data": "[DONE]"}

            mock_core.proxy_stream_request = mock_stream
            mock_gw.return_value = mock_core

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "我的手机号是13812345678"}],
                    "stream": True
                },
                headers={"Authorization": "Bearer test-key"}
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_chat_completion_empty_messages(self, client):
        """Request with empty messages is handled"""
        with patch('routers.proxy.get_gateway_core') as mock_gw:
            mock_core = Mock()
            mock_core.mask_request.return_value = (
                {"model": "gpt-3.5", "messages": []},
                {},
                {},
                "test-sess-empty",
                set()
            )
            mock_core.proxy_request = AsyncMock(return_value=(
                200,
                json.dumps({
                    "id": "chatcmpl-empty",
                    "choices": [{"message": {"content": "Hello"}}]
                }).encode(),
                {"content-type": "application/json"}
            ))
            mock_core.unmask_response = Mock(return_value="Hello")
            mock_gw.return_value = mock_core

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5",
                    "messages": []
                },
                headers={"Authorization": "Bearer test-key"}
            )
            assert response.status_code == 200

    def test_chat_completion_proxy_502(self, client):
        """When upstream is down, returns 502"""
        with patch('routers.proxy.get_gateway_core') as mock_gw:
            mock_core = Mock()
            mock_core.mask_request.return_value = (
                {"model": "gpt-3.5", "messages": [{"role": "user", "content": "hello"}]},
                {},
                {},
                "test-sess-502",
                set()
            )
            mock_core.proxy_request = AsyncMock(return_value=(
                502,
                json.dumps({"error": "No healthy upstream available"}).encode(),
                {}
            ))
            mock_core.unmask_response = Mock(return_value="hello")
            mock_gw.return_value = mock_core

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5",
                    "messages": [{"role": "user", "content": "hello"}]
                },
                headers={"Authorization": "Bearer test-key"}
            )
            assert response.status_code == 502


class TestE2EAdmin:
    """E2E tests for admin endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_admin_login_and_stats(self, client):
        """Admin login then access stats"""
        # Login
        login_resp = client.post(
            "/admin/login",
            json={"password": "test_admin_pw_123"}
        )
        assert login_resp.status_code == 200
        assert "session_token" in login_resp.cookies

        # Access stats with session cookie
        cookie_value = login_resp.cookies["session_token"]
        response = client.get(
            "/admin/stats",
            cookies={"session_token": cookie_value}
        )
        assert response.status_code == 200

    def test_admin_unauthorized_stats(self, client):
        """Stats without login returns 401"""
        response = client.get("/admin/stats")
        assert response.status_code == 401

    def test_admin_wrong_password(self, client):
        """Wrong password returns 401"""
        response = client.post(
            "/admin/login",
            json={"password": "wrong_password_123"}
        )
        assert response.status_code == 401

    def test_admin_health(self, client):
        """Health endpoint is publicly accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["service"] == "AI Privacy Gateway"

    def test_root_endpoint(self, client):
        """Root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["service"] == "AI Privacy Gateway"

    def test_admin_with_bearer_token(self, client):
        """Admin endpoints accept Bearer token header"""
        # Login to get token
        login_resp = client.post(
            "/admin/login",
            json={"password": "test_admin_pw_123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.cookies.get("session_token")

        # Use Bearer token header instead of cookie
        response = client.get(
            "/admin/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_admin_with_invalid_token(self, client):
        """Invalid Bearer token returns 401"""
        response = client.get(
            "/admin/stats",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 401


class TestE2EHealthEndpoints:
    """E2E tests for health endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        reset_limiter()

    @pytest.fixture
    def client(self):
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_health_endpoint(self, client):
        """Health check returns status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "uptime_seconds" in data

    def test_root_health(self, client):
        """Root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["service"] == "AI Privacy Gateway"
