"""
配置模块 - 环境变量管理
"""
import os


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

    # 管理员密码
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
