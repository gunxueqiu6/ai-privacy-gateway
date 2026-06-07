"""
配置模块 - 环境变量 + 版本 + License 管理
支持 Lite / Pro / Enterprise 三版本切换
"""
import os
from enum import Enum
from typing import Optional


class VersionType(Enum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Config:
    """全局配置类"""

    # 版本信息
    VERSION: str = os.environ.get("VERSION", "lite")
    VERSION_TYPE: VersionType = VersionType.LITE  # real value set below

    # License 配置
    LICENSE_KEY: str = os.environ.get("LICENSE_KEY", "free_version")

    # 网关配置
    LISTEN_PORT: int = int(os.environ.get("LISTEN_PORT", "9999"))
    TARGET_LLM: str = os.environ.get("TARGET_LLM", "https://api.openai.com")

    # 数据库配置
    DB_PATH: str = os.environ.get("DB_PATH", "./vault_data/privacy_vault.db")
    DB_TYPE: str = os.environ.get("DB_TYPE", "sqlite")  # sqlite / redis

    # Redis 配置 (Enterprise 版)
    REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.environ.get("REDIS_PASSWORD", "")

    # 脱敏引擎配置
    MASK_ENGINE_TYPE: str = os.environ.get("MASK_ENGINE_TYPE", "regex")  # regex / ac_automaton

    # License 服务器配置 (Pro/Enterprise)
    LICENSE_SERVER_URL: str = os.environ.get("LICENSE_SERVER_URL", "")
    LICENSE_VERIFY_INTERVAL: int = int(os.environ.get("LICENSE_VERIFY_INTERVAL", "1800"))  # 30分钟

    # 功能开关
    @property
    def is_lite(self) -> bool:
        return self.VERSION_TYPE == VersionType.LITE

    @property
    def is_pro(self) -> bool:
        return self.VERSION_TYPE == VersionType.PRO

    @property
    def is_enterprise(self) -> bool:
        return self.VERSION_TYPE == VersionType.ENTERPRISE

    @property
    def feature_team_dashboard(self) -> bool:
        """团队看板功能 - Pro/Enterprise"""
        return self.is_pro or self.is_enterprise

    @property
    def feature_concurrent_wal(self) -> bool:
        """多人并发 WAL 模式 - Pro/Enterprise"""
        return self.is_pro or self.is_enterprise

    @property
    def feature_redis_storage(self) -> bool:
        """Redis 存储 - Enterprise"""
        return self.is_enterprise

    @property
    def feature_ac_automaton(self) -> bool:
        """AC 自动机引擎 - Enterprise"""
        return self.is_enterprise and self.MASK_ENGINE_TYPE == "ac_automaton"

    @property
    def feature_audit_log(self) -> bool:
        """审计日志 - Enterprise"""
        return self.is_enterprise

    @property
    def feature_cloud_rules(self) -> bool:
        """规则云端更新 - Pro/Enterprise"""
        return self.is_pro or self.is_enterprise

    @property
    def feature_license_verify(self) -> bool:
        """License 验证 - Pro/Enterprise"""
        return self.is_pro or self.is_enterprise

    @property
    def feature_deterministic_hash(self) -> bool:
        """确定性格式占位符 - Pro/Enterprise"""
        return self.is_pro or self.is_enterprise

    def get_version_display(self) -> str:
        """获取版本显示名称"""
        display_names = {
            VersionType.LITE: "Lite 个人版",
            VersionType.PRO: "Pro 团队版",
            VersionType.ENTERPRISE: "Enterprise 企业版"
        }
        return display_names.get(self.VERSION_TYPE, "Lite 个人版")


# 解析版本类型，带容错
def _parse_version_type() -> VersionType:
    raw = os.environ.get("VERSION", "lite").lower()
    try:
        return VersionType(raw)
    except ValueError:
        return VersionType.LITE

Config.VERSION_TYPE = _parse_version_type()

# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config