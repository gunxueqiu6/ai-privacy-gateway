"""
配置模块 - 环境变量管理 + 密钥持久化。
"""
import json
import logging
import secrets
import os
import sys
from pathlib import Path
from typing import Optional

import bcrypt

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load .env file into os.environ if it exists (no extra dependency)."""
    # When frozen by PyInstaller, .env lives next to the exe (CWD).
    # When running from source, .env lives in the project root.
    if getattr(sys, 'frozen', False):
        env_path = Path.cwd() / ".env"
    else:
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

    # 多上游 LLM 负载均衡配置
    UPSTREAM_LLM_URLS: str = os.environ.get("UPSTREAM_LLM_URLS", "")
    UPSTREAM_LB_STRATEGY: str = os.environ.get("UPSTREAM_LB_STRATEGY", "round_robin")
    UPSTREAM_HEALTH_CHECK_INTERVAL: int = int(os.environ.get("UPSTREAM_HEALTH_CHECK_INTERVAL", "30"))

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

    # 映射 TTL 秒数（0 = 请求完成即删除，默认 259200 = 72h）
    MAPPING_TTL: int = int(os.environ.get("MAPPING_TTL", "259200"))
    # 无状态模式（纯内存，不落盘）
    STATELESS_MODE: bool = os.environ.get("STATELESS_MODE", "0") == "1"

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

        self._validate()

    def _validate(self) -> None:
        """启动配置校验"""
        has_error = False

        # 多上游 URL 校验（如果配置了 UPSTREAM_LLM_URLS）
        if self.UPSTREAM_LLM_URLS:
            urls = [u.strip() for u in self.UPSTREAM_LLM_URLS.split(",") if u.strip()]
            for url in urls:
                if not (url.startswith("http://") or url.startswith("https://")):
                    print(f"[配置错误] UPSTREAM_LLM_URLS 中的 URL 格式无效: {url}，必须以 http:// 或 https:// 开头")
                    has_error = True
            strategy = self.UPSTREAM_LB_STRATEGY
            if strategy not in ("round_robin", "random", "least_connections"):
                print(f"[配置错误] UPSTREAM_LB_STRATEGY 无效: {strategy}，仅支持 round_robin/random/least_connections")
                has_error = True

        # TARGET_LLM URL 格式校验（仅当未配置 UPSTREAM_LLM_URLS 时）
        if not self.UPSTREAM_LLM_URLS:
            if not (self.TARGET_LLM.startswith("http://") or self.TARGET_LLM.startswith("https://")):
                print(f"[配置错误] TARGET_LLM URL 格式无效: {self.TARGET_LLM}，必须以 http:// 或 https:// 开头")
                has_error = True

        # LISTEN_PORT 端口号校验
        if not 1 <= self.LISTEN_PORT <= 65535:
            print(f"[配置错误] LISTEN_PORT 端口号超出范围: {self.LISTEN_PORT}，有效范围 1-65535")
            has_error = True

        # DB_TYPE 校验
        if self.DB_TYPE and self.DB_TYPE not in ("sqlite", "postgresql"):
            print(f"[配置错误] DB_TYPE 不支持: {self.DB_TYPE}，仅支持 sqlite 或 postgresql")
            has_error = True

        # MASK_ENGINE_TYPE 校验
        if self.MASK_ENGINE_TYPE != "regex":
            print(f"[配置错误] MASK_ENGINE_TYPE 不支持: {self.MASK_ENGINE_TYPE}，目前仅支持 regex")
            has_error = True

        # 警告项
        if not self.UPSTREAM_API_KEY:
            print("[配置警告] 未配置上游API密钥，代理请求可能失败")

        if len(self.JWT_SECRET) < 32:
            print(f"[配置警告] JWT_SECRET 长度不足 32: 当前 {len(self.JWT_SECRET)} 位")

        # MAPPING_TTL 校验
        if self.MAPPING_TTL < 0:
            print(f"[配置警告] MAPPING_TTL 不能为负数: {self.MAPPING_TTL}，使用 0")
            self.MAPPING_TTL = 0

        if has_error:
            sys.exit(1)
        else:
            print("配置校验通过")

# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
