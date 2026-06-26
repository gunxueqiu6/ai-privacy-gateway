"""
Advanced config tests — validation, edge cases, secrets persistence.
"""
import os
import pytest
import sys
import json


class TestConfigValidation:
    """Config validation edge cases"""

    def test_invalid_port_raises(self, monkeypatch):
        monkeypatch.setenv("LISTEN_PORT", "99999")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            # Need to avoid cached secrets from previous test
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_invalid_target_llm_url_raises(self, monkeypatch):
        monkeypatch.setenv("TARGET_LLM", "not-a-url")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_invalid_upstream_urls_raises(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_LLM_URLS", "not-a-valid-url, https://api.openai.com")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_invalid_lb_strategy_raises(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_LLM_URLS", "https://api.openai.com")
        monkeypatch.setenv("UPSTREAM_LB_STRATEGY", "invalid_strategy")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_invalid_db_type_raises(self, monkeypatch):
        monkeypatch.setenv("DB_TYPE", "mongodb")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_invalid_mask_engine_type_raises(self, monkeypatch):
        monkeypatch.setenv("MASK_ENGINE_TYPE", "ml")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        with pytest.raises(SystemExit) as excinfo:
            import config as cfg_mod
            importlib.reload(cfg_mod)
            cfg_mod.Config()
        assert excinfo.value.code == 1

    def test_negative_mapping_ttl_clamped(self, monkeypatch):
        monkeypatch.setenv("MAPPING_TTL", "-5")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        import config as cfg_mod
        importlib.reload(cfg_mod)
        c = cfg_mod.Config()
        assert c.MAPPING_TTL == 0

    def test_missing_upstream_api_key_warns(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_API_KEY", "")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        import config as cfg_mod
        importlib.reload(cfg_mod)
        c = cfg_mod.Config()
        assert c.UPSTREAM_API_KEY == ""


class TestConfigStateless:
    """Stateless mode config"""

    def test_stateless_mode_enabled(self, monkeypatch):
        monkeypatch.setenv("STATELESS_MODE", "1")
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$2b$12$LJ3m4ys3MvMWGvKkRnHoSu7WvA6BXBfAMrZTv5B.eqZJmJqoJzCGO")
        import importlib
        import config as cfg_mod
        importlib.reload(cfg_mod)
        c = cfg_mod.Config()
        assert c.STATELESS_MODE is True
