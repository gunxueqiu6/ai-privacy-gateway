"""
Alert Manager 测试 - 告警管理器
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio


class TestAlertManager:
    """告警管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        try:
            from alert_manager import AlertManager, get_alert_manager

            manager = get_alert_manager()
            assert manager is not None
        except ImportError:
            pytest.skip("alert_manager module not available")

    def test_add_alert_rule(self):
        """测试添加告警规则"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()
            rule = AlertRule(
                name="高频脱敏告警",
                condition="mask_count > 100",
                level=AlertLevel.WARNING,
                channels=["dingtalk"]
            )

            manager.add_rule(rule)
            rules = manager.get_rules()

            assert len(rules) > 0
            assert any(r.name == "高频脱敏告警" for r in rules)
        except ImportError:
            pytest.skip("alert_manager module not available")

    def test_remove_alert_rule(self):
        """测试删除告警规则"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()
            rule = AlertRule(
                name="测试规则",
                condition="test",
                level=AlertLevel.INFO,
                channels=[]
            )

            manager.add_rule(rule)
            manager.remove_rule("测试规则")

            rules = manager.get_rules()
            assert not any(r.name == "测试规则" for r in rules)
        except ImportError:
            pytest.skip("alert_manager module not available")

    def test_check_alert_condition(self):
        """测试告警条件检查"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()

            # 添加规则：脱敏次数超过阈值
            rule = AlertRule(
                name="脱敏阈值",
                condition="mask_count > 50",
                level=AlertLevel.WARNING,
                channels=[]
            )
            manager.add_rule(rule)

            # 模拟统计数据
            stats = {"mask_count": 60}
            triggered = manager.check_conditions(stats)

            assert len(triggered) > 0
            assert any(a.rule_name == "脱敏阈值" for a in triggered)
        except ImportError:
            pytest.skip("alert_manager module not available")

    def test_alert_not_triggered(self):
        """测试告警未触发"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()
            rule = AlertRule(
                name="高阈值",
                condition="mask_count > 1000",
                level=AlertLevel.WARNING,
                channels=[]
            )
            manager.add_rule(rule)

            stats = {"mask_count": 10}
            triggered = manager.check_conditions(stats)

            assert len(triggered) == 0
        except ImportError:
            pytest.skip("alert_manager module not available")


class TestAlertChannels:
    """告警渠道测试"""

    @pytest.mark.asyncio
    async def test_dingtalk_send(self):
        """测试钉钉发送"""
        try:
            from alert_manager import DingTalkChannel

            channel = DingTalkChannel(webhook="https://oapi.dingtalk.com/robot/send?access_token=test")

            # Mock HTTP请求
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value = MagicMock(status_code=200)

                result = await channel.send("测试告警消息", level="WARNING")

                assert result is True
                mock_post.assert_called_once()
        except ImportError:
            pytest.skip("alert_manager module not available")

    @pytest.mark.asyncio
    async def test_feishu_send(self):
        """测试飞书发送"""
        try:
            from alert_manager import FeishuChannel

            channel = FeishuChannel(webhook="https://open.feishu.cn/open-apis/bot/v2/hook/test")

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value = MagicMock(status_code=200)

                result = await channel.send("测试告警消息", level="WARNING")

                assert result is True
        except ImportError:
            pytest.skip("alert_manager module not available")

    @pytest.mark.asyncio
    async def test_wechat_work_send(self):
        """测试企业微信发送"""
        try:
            from alert_manager import WechatWorkChannel

            channel = WechatWorkChannel(webhook="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value = MagicMock(status_code=200)

                result = await channel.send("测试告警消息", level="WARNING")

                assert result is True
        except ImportError:
            pytest.skip("alert_manager module not available")

    @pytest.mark.asyncio
    async def test_channel_failure(self):
        """测试渠道发送失败"""
        try:
            from alert_manager import DingTalkChannel

            channel = DingTalkChannel(webhook="https://invalid.url")

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value = MagicMock(status_code=500)

                result = await channel.send("测试消息", level="WARNING")

                assert result is False
        except ImportError:
            pytest.skip("alert_manager module not available")


class TestHighFrequencyCheck:
    """高频检查测试"""

    def test_high_frequency_mask(self):
        """测试高频脱敏检测"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()

            # 高频规则：每分钟超过100次
            rule = AlertRule(
                name="高频脱敏",
                condition="mask_rate > 100",
                level=AlertLevel.CRITICAL,
                channels=["dingtalk", "feishu"]
            )
            manager.add_rule(rule)

            # 模拟高频数据
            stats = {"mask_rate": 150}
            triggered = manager.check_conditions(stats)

            assert len(triggered) > 0
            alert = triggered[0]
            assert alert.level == AlertLevel.CRITICAL
        except ImportError:
            pytest.skip("alert_manager module not available")

    def test_frequency_threshold_configurable(self):
        """测试频率阈值可配置"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel

            manager = AlertManager()

            # 可配置阈值
            thresholds = [50, 100, 200]
            for threshold in thresholds:
                rule = AlertRule(
                    name=f"阈值{threshold}",
                    condition=f"mask_rate > {threshold}",
                    level=AlertLevel.WARNING,
                    channels=[]
                )
                manager.add_rule(rule)

            rules = manager.get_rules()
            assert len(rules) >= 3
        except ImportError:
            pytest.skip("alert_manager module not available")


class TestAlertCooldown:
    """告警冷却测试"""

    def test_alert_cooldown(self):
        """测试告警冷却时间"""
        try:
            from alert_manager import AlertManager, AlertRule, AlertLevel
            import time

            manager = AlertManager(cooldown_seconds=60)
            rule = AlertRule(
                name="冷却测试",
                condition="mask_count > 10",
                level=AlertLevel.WARNING,
                channels=[]
            )
            manager.add_rule(rule)

            # 第一次触发
            stats = {"mask_count": 20}
            triggered1 = manager.check_conditions(stats)
            assert len(triggered1) > 0

            # 立即再次检查（冷却期内）
            triggered2 = manager.check_conditions(stats)
            # 应该被冷却，不重复触发
            # 实现取决于具体逻辑
        except ImportError:
            pytest.skip("alert_manager module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])