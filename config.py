"""
配置模块 - 环境变量管理
"""
import logging
import secrets
import os
from typing import Optional

import bcrypt


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
    
    # JWT 密钥 — 生产环境必须显式设置，不自动生成
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "")

    # Vault 加密密钥（为空时加密功能禁用）
    VAULT_ENCRYPT_KEY: str = os.environ.get("VAULT_ENCRYPT_KEY", "")

    # Runtime tier (always "lite" in open-source version)
    tier: str = "lite"

    def __init__(self) -> None:
        """Initialize config and auto-generate password hash."""
        if not self.JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET environment variable is required. "
                "Set it to a random 64-char hex string for production."
            )

        if not self.VAULT_ENCRYPT_KEY:
            logging.getLogger(__name__).warning(
                "VAULT_ENCRYPT_KEY not set — vault encryption is disabled"
            )

        if not self.ADMIN_PASSWORD_HASH and self.ADMIN_PASSWORD:
            # 如果没有哈希但有明文密码，自动生成哈希
            salt = bcrypt.gensalt()
            self.ADMIN_PASSWORD_HASH = bcrypt.hashpw(self.ADMIN_PASSWORD.encode(), salt).decode()

        if not self.ADMIN_PASSWORD_HASH:
            logging.getLogger(__name__).warning(
                "未设置管理员密码（ADMIN_PASSWORD 为空），将生成随机密码用于本次启动"
            )
            random_pw = secrets.token_urlsafe(16)
            salt = bcrypt.gensalt()
            self.ADMIN_PASSWORD_HASH = bcrypt.hashpw(random_pw.encode(), salt).decode()

# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
