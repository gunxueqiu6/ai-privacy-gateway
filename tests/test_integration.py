"""
集成测试 - AI Privacy Gateway
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class TestIntegrationMask:
    """脱敏 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_mask_api_basic(self, client):
        """测试基本脱敏 API"""
        response = client.post(
            "/api/mask",
            json={"text": "我的手机号是13812345678"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "masked_text" in data
        assert "entities" in data
        assert "13812345678" not in data["masked_text"]
        assert "[PII_PHONE_" in data["masked_text"]

    def test_mask_api_multiple_entities(self, client):
        """测试多实体脱敏"""
        response = client.post(
            "/api/mask",
            json={"text": "张三的手机13812345678，邮箱test@example.com，身份证110101199001011234"}
        )

        assert response.status_code == 200
        data = response.json()

        # 应检测到多种实体
        entity_types = set(e["type"] for e in data["entities"])
        assert len(entity_types) >= 2

    def test_mask_api_empty_text(self, client):
        """测试空文本"""
        response = client.post(
            "/api/mask",
            json={"text": ""}
        )

        # 应返回错误或空结果
        assert response.status_code in [400, 200]

    def test_mask_api_no_entities(self, client):
        """测试无敏感信息文本"""
        response = client.post(
            "/api/mask",
            json={"text": "这是一段普通文本"}
        )

        assert response.status_code == 200
        data = response.json()

        # 应无实体检测
        assert len(data["entities"]) == 0
        assert data["masked_text"] == "这是一段普通文本"


class TestIntegrationRestore:
    """还原 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_restore_api_basic(self, client):
        """测试基本还原 API"""
        # 先脱敏
        mask_response = client.post(
            "/api/mask",
            json={"text": "手机号13812345678"}
        )
        mask_data = mask_response.json()

        # 再还原
        restore_response = client.post(
            "/api/restore",
            json={
                "text": mask_data["masked_text"],
                "mappings": {e["placeholder"]: e["value"] for e in mask_data["entities"]}
            }
        )

        assert restore_response.status_code == 200
        restore_data = restore_response.json()

        assert "original_text" in restore_data
        assert "13812345678" in restore_data["original_text"]

    def test_restore_api_empty_mappings(self, client):
        """测试空映射还原"""
        response = client.post(
            "/api/restore",
            json={"text": "普通文本", "mappings": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "普通文本"


class TestIntegrationBatch:
    """批量处理 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_batch_mask_api(self, client):
        """测试批量脱敏"""
        response = client.post(
            "/api/mask/batch",
            json={"texts": ["手机13812345678", "邮箱test@example.com", "身份证110101199001011234"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) == 3

    def test_batch_mask_api_limit(self, client):
        """测试批量限制"""
        # 超过50条
        texts = [f"文本{i}" for i in range(60)]

        response = client.post(
            "/api/mask/batch",
            json={"texts": texts}
        )

        # 应返回错误
        assert response.status_code == 400

    def test_batch_mask_api_empty(self, client):
        """测试空批量"""
        response = client.post(
            "/api/mask/batch",
            json={"texts": []}
        )

        assert response.status_code == 400


class TestIntegrationEntities:
    """实体类型 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_get_entities_api(self, client):
        """测试获取实体类型列表"""
        response = client.get("/api/entities")

        assert response.status_code == 200
        data = response.json()

        assert "entities" in data
        assert len(data["entities"]) >= 4  # 至少有 phone, email, idcard, bankcard

        # 验证实体结构
        for entity in data["entities"]:
            assert "type" in entity
            assert "name" in entity
            assert "enabled" in entity


class TestIntegrationChatCompletion:
    """Chat Completion 代理集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_chat_completion_proxy(self, client):
        """测试 Chat Completion 代理"""
        with patch('routers.proxy.get_gateway_core') as mock_gateway:
            mock_core = Mock()
            mock_core.mask_request.return_value = (
                {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "手机号[PII_PHONE_00000001]"}]},
                {},
                {},
                "test-session",
                set()
            )
            mock_core.proxy_request = AsyncMock(return_value=(
                200,
                b'{"id":"test-id","choices":[{"message":{"content":"\xe5\x9b\x9e\xe5\xa4\x8d\xe5\x86\x85\xe5\xae\xb9"}}]}',
                {"content-type": "application/json"}
            ))
            mock_core.unmask_response = Mock(return_value="回复内容")
            mock_gateway.return_value = mock_core

            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "手机号13812345678"}]
                },
                headers={"Authorization": "Bearer test-key"}
            )

            assert response.status_code == 200


class TestIntegrationAdminAuth:
    """Admin 鉴权集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_admin_unauthorized(self, client):
        """测试未登录访问"""
        response = client.get("/admin/stats")

        # 应返回 401
        assert response.status_code == 401

    def test_admin_wrong_password(self, client):
        """测试错误密码登录"""
        response = client.post(
            "/admin/login",
            json={"username": "admin", "password": "wrongpassword"}
        )

        # 应返回 401
        assert response.status_code == 401

    def test_admin_correct_login(self, client):
        """测试正确登录"""
        response = client.post(
            "/admin/login",
            json={"password": "test_admin_pw_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # 验证设置了 session_token cookie
        assert "session_token" in response.cookies

    def test_admin_with_token(self, client):
        """测试带 Cookie 访问"""
        # 先登录获取 cookie
        login_response = client.post(
            "/admin/login",
            json={"password": "test_admin_pw_123"}
        )
        session_cookie = login_response.cookies.get("session_token")

        # 带 cookie 访问
        client.cookies = {"session_token": session_cookie}
        response = client.get("/admin/stats")

        assert response.status_code == 200


class TestIntegrationRateLimit:
    """速率限制集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    @pytest.mark.skip(reason="rate limit test interferes with other tests in shared limiter state")
    def test_rate_limit_mask(self, client):
        """测试脱敏 API 速率限制"""
        responses = []
        for i in range(70):
            response = client.post(
                "/api/mask",
                json={"text": f"测试{i}"}
            )
            responses.append(response.status_code)

        assert 429 in responses


class TestIntegrationFullPipeline:
    """完整管线集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        try:
            from main import app
            return TestClient(app)
        except ImportError:
            pytest.skip("main module not available")

    def test_full_mask_restore_pipeline(self, client):
        """测试完整脱敏→还原管线"""
        original_text = "张三的手机号是13812345678，邮箱test@example.com"

        # 1. 脱敏
        mask_response = client.post(
            "/api/mask",
            json={"text": original_text}
        )
        assert mask_response.status_code == 200
        mask_data = mask_response.json()

        # 验证脱敏结果
        assert "13812345678" not in mask_data["masked_text"]
        assert "test@example.com" not in mask_data["masked_text"]

        # 2. 还原
        mappings = {e["placeholder"]: e["value"] for e in mask_data["entities"]}
        restore_response = client.post(
            "/api/restore",
            json={"text": mask_data["masked_text"], "mappings": mappings}
        )
        assert restore_response.status_code == 200
        restore_data = restore_response.json()

        # 验证还原结果
        assert restore_data["original_text"] == original_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])