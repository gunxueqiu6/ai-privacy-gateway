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
    # PayPal configuration
    PAYPAL_CLIENT_ID: str = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET: str = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE: str = os.environ.get("PAYPAL_MODE", "sandbox")
    PAYPAL_WEBHOOK_ID: str = os.environ.get("PAYPAL_WEBHOOK_ID", "")

    # License configuration
    LICENSE_PRIVATE_KEY: str = os.environ.get("LICENSE_PRIVATE_KEY", "./vault_data/license_private.pem")
    LICENSE_PUBLIC_KEY: str = os.environ.get("LICENSE_PUBLIC_KEY", "./vault_data/license_public.pem")
    LICENSE_KEY: str = os.environ.get("LICENSE_KEY", "")
    LICENSE_FILE: str = os.environ.get("LICENSE_FILE", "./license.key")

    # Runtime license state (populated at startup)
    tier: str = "lite"
    license_seats: int = 1
    license_expires_at: Optional[str] = None
    license_team_id: Optional[str] = None

    LISTEN_PORT: int = int(os.environ.get("LISTEN_PORT", "9999"))
    TARGET_LLM: str = os.environ.get("TARGET_LLM", "https://api.openai.com")

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
    JWT_SECRET: str = os.environ.get("JWT_SECRET", os.urandom(32).hex())

    # Vault 加密密钥（为空时加密功能禁用）
    VAULT_ENCRYPT_KEY: str = os.environ.get("VAULT_ENCRYPT_KEY", "")

    def __init__(self) -> None:
        """Initialize config, auto-generate password hash, and load license."""
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

        # Auto-load license on startup
        self._load_license()

    def _load_license(self) -> None:
        """Load license from environment variable or file, verify signature, set tier."""
        import os as _os
        from jose import jwt as _jwt
        from jose import JWTError as _JWTError

        # Try LICENSE_KEY env var first
        license_token = self.LICENSE_KEY
        if not license_token and _os.path.exists(self.LICENSE_FILE):
            try:
                with open(self.LICENSE_FILE, "r", encoding="utf-8") as f:
                    license_token = f.read().strip()
            except Exception:
                pass

        if not license_token:
            self.tier = "lite"
            return

        # Load public key for verification
        pub_key_path = self.LICENSE_PUBLIC_KEY
        if not _os.path.exists(pub_key_path):
            logging.getLogger(__name__).warning(
                f"License public key not found: {pub_key_path}, cannot verify license"
            )
            self.tier = "lite"
            return

        try:
            with open(pub_key_path, "rb") as f:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                pub_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load license public key: {e}")
            self.tier = "lite"
            return

        try:
            payload = _jwt.decode(license_token, pub_key, algorithms=["RS256"])
        except _JWTError as e:
            logging.getLogger(__name__).warning(f"License verification failed: {e}")
            self.tier = "lite"
            self.license_seats = 1
            return

        if payload.get("sub") != "license":
            self.tier = "lite"
            return

        # Check expiration
        from datetime import datetime, timezone
        exp = payload.get("exp", 0)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > exp:
            logging.getLogger(__name__).warning(
                f"License expired at {datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()}"
            )
            self.tier = "lite"
            self.license_seats = 1
            return

        self.tier = payload.get("tier", "lite")
        self.license_seats = payload.get("seats", 1)
        self.license_team_id = payload.get("tid")
        self.license_expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        self.LICENSE_KEY = license_token

        logging.getLogger(__name__).info(
            f"License loaded: tier={self.tier}, team={self.license_team_id}, seats={self.license_seats}"
        )


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
