"""
配置模块 - 环境变量管理
"""
import logging
import secrets
import os

import bcrypt


class Config:
    """全局配置类"""

    # 网关配置
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

    def __init__(self) -> None:
        """初始化配置，自动为明文密码生成哈希"""
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
            print(f"\n*** 随机生成的本次管理员密码: {random_pw} ***\n")


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
