"""
告警通知模块 - Enterprise 版
支持钉钉、飞书、企业微信 Webhook 实时通知
"""
import json
import logging
import os
import time
from typing import Dict, List, Optional
from datetime import datetime

import httpx

from config import config

logger = logging.getLogger(__name__)


class AlertChannel:
    """告警渠道基类"""

    def send(self, title: str, content: str, level: str = "warning") -> bool:
        raise NotImplementedError


class DingTalkAlert(AlertChannel):
    """钉钉告警"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, content: str, level: str = "warning") -> bool:
        """发送钉钉消息"""
        level_colors = {
            "info": "#4ade80",
            "warning": "#f59e0b",
            "error": "#f87171",
            "critical": "#ef4444"
        }

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n> 级别: {level}\n\n> 时间: {datetime.now().isoformat()}\n\n{content}"
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.webhook_url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"[钉钉告警] 发送失败: {e}")
            return False


class FeishuAlert(AlertChannel):
    """飞书告警"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, content: str, level: str = "warning") -> bool:
        """发送飞书消息"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": level
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": content}},
                    {"tag": "div", "text": {"tag": "plain_text", "content": f"时间: {datetime.now().isoformat()}"}}
                ]
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.webhook_url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"[飞书告警] 发送失败: {e}")
            return False


class WeComAlert(AlertChannel):
    """企业微信告警"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, content: str, level: str = "warning") -> bool:
        """发送企业微信消息"""
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n> 级别: {level}\n> 时间: {datetime.now().isoformat()}\n\n{content}"
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.webhook_url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"[企微告警] 发送失败: {e}")
            return False


class AlertManager:
    """告警管理器"""

    ALERT_RULES = {
        # 高频脱敏告警
        "high_frequency_mask": {
            "threshold": 100,  # 单次脱敏超过100条
            "level": "warning",
            "title": "高频脱敏告警",
            "template": "会话 {session_id} 单次脱敏 {count} 条敏感信息，请关注"
        },
        # License 过期告警
        "license_expired": {
            "threshold": 0,
            "level": "critical",
            "title": "License 过期告警",
            "template": "License {license_key} 已过期，请立即续费"
        },
        # 验证失败告警
        "verify_failed": {
            "threshold": 10,  # 连续验证失败10次
            "level": "error",
            "title": "验证失败告警",
            "template": "License 验证连续失败 {count} 次，请检查网络"
        },
        # 异常请求告警
        "abnormal_request": {
            "threshold": 0,
            "level": "warning",
            "title": "异常请求告警",
            "template": "检测到异常请求: {error_message}"
        },
        # 泄密风险告警
        "leak_risk": {
            "threshold": 0,
            "level": "critical",
            "title": "泄密风险告警",
            "template": "检测到潜在泄密风险: {risk_detail}"
        }
    }

    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.alert_history: List[Dict] = []
        self._load_channels()

    def _load_channels(self):
        """加载告警渠道"""
        # 从配置加载 Webhook URL
        dingtalk_url = os.environ.get("DINGTALK_WEBHOOK", "")
        feishu_url = os.environ.get("FEISHU_WEBHOOK", "")
        wecom_url = os.environ.get("WECOM_WEBHOOK", "")

        if dingtalk_url:
            self.channels.append(DingTalkAlert(dingtalk_url))
            logger.info("[告警] 钉钉渠道已加载")

        if feishu_url:
            self.channels.append(FeishuAlert(feishu_url))
            logger.info("[告警] 飞书渠道已加载")

        if wecom_url:
            self.channels.append(WeComAlert(wecom_url))
            logger.info("[告警] 企业微信渠道已加载")

    def add_channel(self, channel: AlertChannel):
        """添加告警渠道"""
        self.channels.append(channel)

    def send_alert(self, alert_type: str, **kwargs) -> bool:
        """发送告警"""
        rule = self.ALERT_RULES.get(alert_type)
        if not rule:
            logger.warning(f"[告警] 未知的告警类型: {alert_type}")
            return False

        title = rule["title"]
        content = rule["template"].format(**kwargs)
        level = rule["level"]

        # 记录告警历史
        alert_record = {
            "alert_type": alert_type,
            "title": title,
            "content": content,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "params": kwargs
        }
        self.alert_history.append(alert_record)

        # 发送到所有渠道
        success = False
        for channel in self.channels:
            if channel.send(title, content, level):
                success = True
                logger.info(f"[告警] 发送成功: {title} -> {channel.__class__.__name__}")

        return success

    def check_high_frequency(self, session_id: str, count: int) -> bool:
        """检查高频脱敏"""
        threshold = self.ALERT_RULES["high_frequency_mask"]["threshold"]
        if count >= threshold:
            return self.send_alert("high_frequency_mask", session_id=session_id, count=count)
        return False

    def check_license_expired(self, license_key: str) -> bool:
        """检查 License 过期"""
        return self.send_alert("license_expired", license_key=license_key)

    def check_verify_failed(self, count: int) -> bool:
        """检查验证失败"""
        threshold = self.ALERT_RULES["verify_failed"]["threshold"]
        if count >= threshold:
            return self.send_alert("verify_failed", count=count)
        return False

    def check_abnormal_request(self, error_message: str) -> bool:
        """检查异常请求"""
        return self.send_alert("abnormal_request", error_message=error_message)

    def check_leak_risk(self, risk_detail: str) -> bool:
        """检查泄密风险"""
        return self.send_alert("leak_risk", risk_detail=risk_detail)

    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """获取告警历史"""
        return self.alert_history[-limit:]


# 全局告警管理器实例
alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
    return alert_manager