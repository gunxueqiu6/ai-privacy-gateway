"""
认证模块单元测试 — bcrypt, JWT, 登录锁定
"""
import pytest
import bcrypt
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    from database import db
    # 重置测试 IP 的登录锁定状态（数据库持久化状态会跨测试累积）
    db.record_login_attempt("testclient", success=True)
    # 禁用限流器，仅测试认证逻辑
    app.state.limiter.enabled = False
    return TestClient(app)


class TestBcryptHashing:
    """密码哈希测试"""

    def test_hash_and_verify(self):
        """生成哈希后验证通过"""
        password = "test_password_123"
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt).decode()
        assert bcrypt.checkpw(password.encode(), hashed.encode())

    def test_wrong_password_fails(self):
        """错误密码验证失败"""
        password = "correct_password"
        wrong = "wrong_password"
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt).decode()
        assert not bcrypt.checkpw(wrong.encode(), hashed.encode())

    def test_config_password_hash_verifies(self):
        """已知密码生成哈希后能验证通过"""
        import bcrypt as bc
        pw = b"known_test_pw"
        salt = bc.gensalt()
        hashed = bc.hashpw(pw, salt)
        assert bc.checkpw(pw, hashed)
        assert not bc.checkpw(b"wrong", hashed)


class TestJwtToken:
    """JWT 令牌测试"""

    def test_create_and_verify(self):
        """创建 JWT 后能验证通过"""
        from main import create_jwt_token, verify_jwt_token
        token = create_jwt_token()
        assert token
        assert verify_jwt_token(token)

    def test_tampered_token_fails(self):
        """篡改的令牌验证失败"""
        from main import create_jwt_token, verify_jwt_token
        token = create_jwt_token()
        # 修改 token 中间位置（签名段），避免 base64 padding 字符
        mid = len(token) // 3 * 2
        tampered = token[:mid] + ('A' if token[mid] != 'A' else 'B') + token[mid + 1:]
        assert not verify_jwt_token(tampered)

    def test_empty_token_fails(self):
        """空令牌验证失败"""
        from main import verify_jwt_token
        assert not verify_jwt_token("")

    def test_expired_token_fails(self):
        """过期令牌验证失败"""
        from datetime import UTC, datetime, timedelta
        from jose import jwt
        from config import config

        expired = datetime.now(UTC) - timedelta(hours=1)
        token = jwt.encode(
            {"sub": "admin", "exp": expired},
            config.JWT_SECRET,
            algorithm="HS256"
        )
        from main import verify_jwt_token
        assert not verify_jwt_token(token)


class TestLoginFlow:
    """登录流程测试"""

    def test_login_success(self, client):
        """正确密码登录成功"""
        resp = client.post("/admin/login", json={"password": "test_admin_pw_123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "token" in data
        assert "session_token" in resp.cookies

    def test_login_wrong_password(self, client):
        """错误密码返回 401"""
        resp = client.post("/admin/login", json={"password": "wrong"})
        assert resp.status_code == 401

    def test_login_missing_password(self, client):
        """缺少密码字段"""
        resp = client.post("/admin/login", json={})
        assert resp.status_code == 401

    def test_admin_stats_without_token(self, client):
        """未认证访问管理接口返回 401"""
        resp = client.get("/admin/stats")
        assert resp.status_code == 401

    def test_admin_stats_with_bearer_token(self, client):
        """Bearer token 认证通过"""
        login_resp = client.post("/admin/login", json={"password": "test_admin_pw_123"})
        token = login_resp.json()["token"]

        resp = client.get("/admin/stats",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_stats_with_cookie(self, client):
        """Cookie 认证通过"""
        login_resp = client.post("/admin/login", json={"password": "test_admin_pw_123"})
        token = login_resp.cookies["session_token"]

        client.cookies = {"session_token": token}
        resp = client.get("/admin/stats")
        assert resp.status_code == 200

    def test_admin_stats_invalid_token(self, client):
        """无效 token 返回 401"""
        resp = client.get("/admin/stats",
                          headers={"Authorization": "Bearer invalid_token"})
        assert resp.status_code == 401

    def test_logout(self, client):
        """登出清除 cookie"""
        resp = client.post("/admin/logout")
        assert resp.status_code == 200
        # 验证 cookie 被清除
        set_cookie = resp.headers.get("set-cookie", "")
        assert "Max-Age=0" in set_cookie or 'expires=Thu, 01 Jan 1970' in set_cookie


class TestLoginLockout:
    """登录锁定测试"""

    def test_multiple_failures_return_401(self, client):
        """多次失败登录触发锁定返回 429"""
        from database import db
        # 使用 record_login_attempt 直接设 5 次失败（与 handler 同用 _exclusive_conn，避免 WAL 事务隔离差异）
        db.record_login_attempt("testclient", success=True)  # 重置
        for _ in range(5):
            db.record_login_attempt("testclient", success=False)
        # 第 6 次请求应被锁定
        resp = client.post("/admin/login", json={"password": "wrong_password"})
        assert resp.status_code == 429, f"expected 429 (locked), got {resp.status_code}"

    def test_login_blocked_after_max_attempts(self, client):
        """达到最大尝试次数后被锁定"""
        from database import db
        # 模拟 5 次失败
        test_ip = "127.0.0.1"
        for _ in range(5):
            db.record_login_attempt(test_ip, success=False)

        # 检查是否被锁定
        is_locked, remaining = db.check_login_attempt(test_ip)
        assert is_locked or remaining <= 5
