"""
Config 模块单元测试
"""
import os
import pytest


class TestConfigDefaults:
    """默认配置测试"""

    @pytest.fixture
    def config(self):
        from config import Config
        return Config()

    def test_default_port(self, config):
        assert config.LISTEN_PORT == 9999

    def test_default_target_llm(self, config):
        assert config.TARGET_LLM == "https://api.openai.com"

    def test_default_db_path(self, config):
        assert "privacy_vault.db" in config.DB_PATH

    def test_default_db_type(self, config):
        assert config.DB_TYPE == "sqlite"

    def test_default_mask_engine(self, config):
        assert config.MASK_ENGINE_TYPE == "regex"

    def test_default_admin_password(self, config):
        assert config.ADMIN_PASSWORD == "admin123"

    def test_admin_password_hash_generated(self, config):
        """密码哈希自动从明文生成"""
        assert config.ADMIN_PASSWORD_HASH
        assert config.ADMIN_PASSWORD_HASH != config.ADMIN_PASSWORD

    def test_jwt_secret_generated(self, config):
        """JWT 密钥自动生成"""
        assert config.JWT_SECRET
        assert len(config.JWT_SECRET) >= 32


class TestConfigFromEnv:
    """环境变量覆盖测试"""

    def test_env_port_override(self, monkeypatch):
        import importlib, config
        monkeypatch.setenv("LISTEN_PORT", "8888")
        importlib.reload(config)
        c = config.Config()
        assert c.LISTEN_PORT == 8888

    def test_env_target_llm_override(self, monkeypatch):
        import importlib, config
        monkeypatch.setenv("TARGET_LLM", "https://api.deepseek.com")
        importlib.reload(config)
        c = config.Config()
        assert c.TARGET_LLM == "https://api.deepseek.com"

    def test_env_db_path_override(self, monkeypatch):
        import importlib, config
        monkeypatch.setenv("DB_PATH", "/tmp/test.db")
        importlib.reload(config)
        c = config.Config()
        assert c.DB_PATH == "/tmp/test.db"

    def test_env_password_hash(self, monkeypatch):
        """环境变量提供已有哈希则直接使用"""
        import importlib, config
        monkeypatch.setenv("ADMIN_PASSWORD_HASH",
                           "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        importlib.reload(config)
        c = config.Config()
        assert c.ADMIN_PASSWORD_HASH.startswith("$2b$12$")

    def test_env_jwt_secret(self, monkeypatch):
        import importlib, config
        monkeypatch.setenv("JWT_SECRET", "my-fixed-secret")
        importlib.reload(config)
        c = config.Config()
        assert c.JWT_SECRET == "my-fixed-secret"
