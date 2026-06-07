"""
渐进式衰减模块 - Pro/Enterprise 版
验证失败后逐步降级功能
"""
import asyncio
import logging
import random
import time
from enum import IntEnum
from typing import Optional

from config import config
from license_client import get_license_client

logger = logging.getLogger(__name__)


class DecayLevel(IntEnum):
    """衰减等级"""
    NORMAL = 0          # 正常运行
    WARNING = 1         # 显示警告
    RULES_EXPIRED = 2   # 规则过期，脱敏失效
    DELAY_INJECTED = 3  # 流式延迟 +200ms
    DROPPING_5PERCENT = 4  # 随机丢弃 5% 请求
    DISABLED = 5        # 脱敏完全停止
    SHUTDOWN = 6        # 容器停止


class DecayManager:
    """渐进式衰减管理器"""

    # 衰减时间阈值（秒）
    THRESHOLDS = {
        DecayLevel.WARNING: 0,           # 验证失败 1 次
        DecayLevel.RULES_EXPIRED: 3600,   # 连续 1 小时
        DecayLevel.DELAY_INJECTED: 3600,  # 连续 1 小时
        DecayLevel.DROPPING_5PERCENT: 21600,  # 连续 6 小时
        DecayLevel.DISABLED: 86400,       # 连续 24 小时
        DecayLevel.SHUTDOWN: 604800,      # 连续 7 天
    }

    def __init__(self):
        self.current_level = DecayLevel.NORMAL
        self.failure_start_time: Optional[float] = None
        self.total_failure_duration: float = 0
        self.warning_shown: bool = False

    def update(self) -> DecayLevel:
        """更新衰减等级"""
        if not config.feature_license_verify:
            # Lite 版无验证，始终正常
            return DecayLevel.NORMAL

        client = get_license_client()
        failures = client.get_verify_failure_count()

        if failures == 0:
            # 验证成功，恢复正常
            self.current_level = DecayLevel.NORMAL
            self.failure_start_time = None
            self.total_failure_duration = 0
            self.warning_shown = False
            return DecayLevel.NORMAL

        if self.failure_start_time is None:
            self.failure_start_time = time.time()

        self.total_failure_duration = time.time() - self.failure_start_time

        # 计算衰减等级
        if failures >= 1 and self.current_level == DecayLevel.NORMAL:
            self.current_level = DecayLevel.WARNING

        if self.total_failure_duration >= self.THRESHOLDS[DecayLevel.RULES_EXPIRED]:
            self.current_level = DecayLevel.RULES_EXPIRED

        if self.total_failure_duration >= self.THRESHOLDS[DecayLevel.DELAY_INJECTED]:
            self.current_level = DecayLevel.DELAY_INJECTED

        if self.total_failure_duration >= self.THRESHOLDS[DecayLevel.DROPPING_5PERCENT]:
            self.current_level = DecayLevel.DROPPING_5PERCENT

        if self.total_failure_duration >= self.THRESHOLDS[DecayLevel.DISABLED]:
            self.current_level = DecayLevel.DISABLED

        if self.total_failure_duration >= self.THRESHOLDS[DecayLevel.SHUTDOWN]:
            self.current_level = DecayLevel.SHUTDOWN

        return self.current_level

    def should_apply_delay(self) -> bool:
        """是否应该注入延迟"""
        return self.current_level >= DecayLevel.DELAY_INJECTED

    def should_drop_request(self) -> bool:
        """是否应该丢弃请求"""
        if self.current_level >= DecayLevel.DROPPING_5PERCENT:
            return random.random() < 0.05  # 5% 概率丢弃
        return False

    def should_disable_masking(self) -> bool:
        """是否应该禁用脱敏"""
        return self.current_level >= DecayLevel.DISABLED

    def should_shutdown(self) -> bool:
        """是否应该停止容器"""
        return self.current_level >= DecayLevel.SHUTDOWN

    def get_delay_ms(self) -> int:
        """获取注入延迟毫秒数"""
        if self.current_level >= DecayLevel.DELAY_INJECTED:
            return 200
        return 0

    def get_warning_message(self) -> Optional[str]:
        """获取警告消息"""
        if self.current_level == DecayLevel.NORMAL:
            return None

        messages = {
            DecayLevel.WARNING: "License 验证失败，请检查网络连接",
            DecayLevel.RULES_EXPIRED: "脱敏规则已过期，敏感信息可能泄露",
            DecayLevel.DELAY_INJECTED: "服务响应延迟增加",
            DecayLevel.DROPPING_5PERCENT: "部分请求可能失败，请尽快续费",
            DecayLevel.DISABLED: "脱敏功能已停止，所有请求将添加 UNLICENSED 标记",
            DecayLevel.SHUTDOWN: "服务即将停止，请立即续费"
        }

        return messages.get(self.current_level)

    def get_status(self) -> dict:
        """获取衰减状态"""
        return {
            "level": self.current_level.value,
            "level_name": self.current_level.name,
            "failure_duration": self.total_failure_duration,
            "warning": self.get_warning_message()
        }


# 全局衰减管理器实例
decay_manager: Optional[DecayManager] = None


def get_decay_manager() -> DecayManager:
    """获取衰减管理器实例"""
    global decay_manager
    if decay_manager is None:
        decay_manager = DecayManager()
    return decay_manager


async def decay_monitor_task():
    """衰减监控后台任务"""
    manager = get_decay_manager()

    while True:
        level = manager.update()

        if manager.should_shutdown():
            logger.critical("License 验证失败超过 7 天，服务即将停止")
            # 优雅关闭
            import os
            os._exit(0)

        await asyncio.sleep(60)  # 每分钟检查一次