"""
配置模块 - 环境变量管理 + 密钥持久化。
"""
import json
import logging
import secrets
import os
from pathlib import Path
from typing import Optional

import bcrypt

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load .env file into os.environ if it exists (no extra dependency)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    with env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key not in os.environ:
                os.environ[key] = value


def _secrets_file() -> Path:
    """Path to the persisted secrets file (alongside the database)."""
    vault_dir = os.environ.get("VAULT_DIR", "./vault_data")
    return Path(vault_dir) / ".secrets.json"


def _load_persisted_secrets() -> dict:
    """Load secrets from disk. Returns empty dict if none saved."""
    sf = _secrets_file()
    if sf.exists():
        try:
            with sf.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to read persisted secrets, will regenerate")
    return {}


def _save_persisted_secrets(secrets_dict: dict) -> None:
    """Save secrets to disk atomically."""
    sf = _secrets_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    tmp = sf.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(secrets_dict, f)
    tmp.replace(sf)


_load_dotenv()


class Config:
    """全局配置类"""

    # 网关配置
    LISTEN_PORT: int = int(os.environ.get("LISTEN_PORT", "9999"))
    TARGET_LLM: str = os.environ.get("TARGET_LLM", "https://api.openai.com")
    UPSTREAM_API_KEY: str = os.environ.get("UPSTREAM_API_KEY", "")

    # 数据库配置
    DB_PATH: str = os.environ.get("DB_PATH", "./vault_data/privacy_vault.db")
    DB_TYPE: str = os.environ.get("DB_TYPE", "sqlite")

    # 脱敏引擎配置
    MASK_ENGINE_TYPE: str = os.environ.get("MASK_ENGINE_TYPE", "regex")

    # 管理员密码（明文，用于首次生成哈希）
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")

    # 管理员密码哈希
    ADMIN_PASSWORD_HASH: str = os.environ.get("ADMIN_PASSWORD_HASH", "")

    # JWT 密钥
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "")

    # Vault 加密密钥（为空时加密功能禁用）
    VAULT_ENCRYPT_KEY: str = os.environ.get("VAULT_ENCRYPT_KEY", "")

    # Runtime tier (always "lite" in open-source version)
    tier: str = "lite"

    def __init__(self) -> None:
        """Initialize config — prefer env vars, then persisted secrets, then auto-generate."""
        persisted = _load_persisted_secrets()

        # JWT secret
        if not self.JWT_SECRET:
            if persisted.get("jwt_secret"):
                self.JWT_SECRET = persisted["jwt_secret"]
            else:
                self.JWT_SECRET = secrets.token_hex(32)
                persisted["jwt_secret"] = self.JWT_SECRET
                logger.warning("JWT_SECRET not set — auto-generated and persisted")

        # Vault encryption key
        if not self.VAULT_ENCRYPT_KEY:
            if persisted.get("vault_encrypt_key"):
                self.VAULT_ENCRYPT_KEY = persisted["vault_encrypt_key"]
        if not self.VAULT_ENCRYPT_KEY:
            logger.warning("VAULT_ENCRYPT_KEY not set — vault encryption is disabled")

        # Admin password
        if not self.ADMIN_PASSWORD_HASH and self.ADMIN_PASSWORD:
            salt = bcrypt.gensalt()
            self.ADMIN_PASSWORD_HASH = bcrypt.hashpw(self.ADMIN_PASSWORD.encode(), salt).decode()

        if not self.ADMIN_PASSWORD_HASH:
            if persisted.get("admin_password_hash"):
                self.ADMIN_PASSWORD_HASH = persisted["admin_password_hash"]
                self.ADMIN_PASSWORD = persisted.get("admin_password", "")
            else:
                random_pw = secrets.token_urlsafe(12)
                self.ADMIN_PASSWORD = random_pw
                salt = bcrypt.gensalt()
                self.ADMIN_PASSWORD_HASH = bcrypt.hashpw(random_pw.encode(), salt).decode()
                persisted["admin_password_hash"] = self.ADMIN_PASSWORD_HASH
                persisted["admin_password"] = random_pw
                logger.warning("ADMIN_PASSWORD not set — auto-generated: %s", random_pw)

        # Persist any new secrets
        _save_persisted_secrets(persisted)

# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
