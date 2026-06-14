"""Tests for alerts module (Phase 4)."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# TestAlertRule
# ============================================================


class TestAlertRule:
    def test_create_rule_with_required_fields(self):
        from alerts import AlertRule
        rule = AlertRule(name="Test", condition="stats.x > 10", actions=["email"])
        assert rule.name == "Test"
        assert rule.condition == "stats.x > 10"
        assert rule.actions == ["email"]
        assert rule.config == {}

    def test_create_rule_with_config(self):
        from alerts import AlertRule
        rule = AlertRule(
            name="Test", condition="stats.x > 10", actions=["email"],
            config={"severity": "high", "cooldown": 300},
        )
        assert rule.config["severity"] == "high"
        assert rule.config["cooldown"] == 300

    def test_create_rule_default_config(self):
        from alerts import AlertRule
        rule = AlertRule(name="N", condition="stats.x > 1", actions=["webhook"])
        assert rule.config == {}


# ============================================================
# TestAlertEngineInit
# ============================================================


class TestAlertEngineInit:
    def test_init_default_rules(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        assert len(engine.rules) >= 3

    def test_init_rule_names(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        names = [r.name for r in engine.rules]
        assert "High masking volume" in names
        assert "Database integrity failure" in names
        assert "License expiring soon" in names

    def test_init_from_env_var(self):
        custom_rules = json.dumps([
            {"name": "Custom rule", "condition": "stats.errors > 5", "actions": ["email"]},
        ])
        with patch.dict(os.environ, {"ALERT_RULES": custom_rules}, clear=False):
            from alerts import AlertEngine
            engine = AlertEngine()
        assert len(engine.rules) == 1
        assert engine.rules[0].name == "Custom rule"

    def test_init_invalid_env_var_falls_back(self):
        with patch.dict(os.environ, {"ALERT_RULES": "not-json"}, clear=False):
            from alerts import AlertEngine
            engine = AlertEngine()
        assert len(engine.rules) >= 3

    def test_get_alert_engine_singleton(self):
        from alerts import get_alert_engine, _alert_engine
        old = _alert_engine
        try:
            engine1 = get_alert_engine()
            engine2 = get_alert_engine()
            assert engine1 is engine2
        finally:
            pass

    def test_get_alert_engine_creates(self):
        from alerts import get_alert_engine, _alert_engine
        old = _alert_engine
        try:
            engine = get_alert_engine()
            assert engine is not None
            assert hasattr(engine, "rules")
        finally:
            pass

# ============================================================
# TestEvaluateStatsCondition
# ============================================================


class TestEvaluateStatsCondition:
    def test_greater_than_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 15000}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "High masking volume" in names

    def test_greater_than_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 100}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "High masking volume" not in names

    def test_greater_equal_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.count >= 50"
        context = {"stats": {"count": 50}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 1

    def test_greater_equal_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.count >= 50"
        context = {"stats": {"count": 49}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 0

    def test_less_than_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.errors < 5"
        context = {"stats": {"errors": 2}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 1

    def test_less_than_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.errors < 5"
        context = {"stats": {"errors": 10}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 0

    def test_less_equal_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.count <= 3"
        context = {"stats": {"count": 3}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 1

    def test_less_equal_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.count <= 3"
        context = {"stats": {"count": 4}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 0

    def test_missing_stats_field_defaults_zero(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "High masking volume" not in names

    def test_multiple_fields_checked(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.cpu > 80"
        context = {"stats": {"cpu": 95, "mem": 50}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 1

# ============================================================
# TestEvaluateIntegrityCondition
# ============================================================


class TestEvaluateIntegrityCondition:
    def test_failed_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"integrity_check": {"failed": True}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "Database integrity failure" in names

    def test_failed_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"integrity_check": {"failed": False}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "Database integrity failure" not in names

    def test_missing_integrity_context(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "Database integrity failure" not in names

    def test_integrity_other_fields(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"integrity_check": {"corrupted": True, "failed": False}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "Database integrity failure" not in names

    def test_integrity_failed_with_extra(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"integrity_check": {"failed": True, "checksum": "abc"}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "Database integrity failure" in names


# ============================================================
# TestEvaluateLicenseCondition
# ============================================================


class TestEvaluateLicenseCondition:
    def test_expires_soon_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"license": {"expires_in": 3}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" in names

    def test_expires_soon_not_triggered(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"license": {"expires_in": 30}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" not in names

    def test_expires_soon_boundary(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"license": {"expires_in": 7}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" not in names

    def test_expires_soon_empty_context(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" not in names

    def test_less_equal_operator(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[2].condition = "license.expires_in <= 7days"
        context = {"license": {"expires_in": 7}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" in names

    def test_license_expired(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"license": {"expires_in": 0}}
        triggered = engine.evaluate(context)
        names = [a["rule"] for a in triggered]
        assert "License expiring soon" in names

# ============================================================
# TestEvaluateEdgeCases
# ============================================================


class TestEvaluateEdgeCases:
    def test_empty_context(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        triggered = engine.evaluate({})
        assert triggered == []

    def test_none_values(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": None, "integrity_check": None, "license": None}
        triggered = engine.evaluate(context)
        assert triggered == []

    def test_unknown_condition_prefix(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "unknown.field > 10"
        context = {"unknown": {"field": 100}}
        triggered = engine.evaluate(context)
        assert triggered == []

    def test_malformed_condition(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.badformat"
        context = {"stats": {"badformat": 999}}
        triggered = engine.evaluate(context)
        assert triggered == []

    def test_empty_stats_value(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        engine.rules[0].condition = "stats.val > 0"
        context = {"stats": {"val": 0}}
        triggered = engine.evaluate(context)
        assert len(triggered) == 0


# ============================================================
# TestSendEmail
# ============================================================


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_send_email_success(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["email"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value
            instance.send_message = MagicMock()
            instance.quit = MagicMock()
            result = await engine.send_email(alert, "test@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_auth(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["email"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch.dict(os.environ, {
            "ALERT_SMTP_USER": "user", "ALERT_SMTP_PASS": "pass",
        }, clear=False):
            with patch("alerts.smtplib.SMTP") as mock_smtp:
                instance = mock_smtp.return_value
                instance.send_message = MagicMock()
                instance.quit = MagicMock()
                result = await engine.send_email(alert, "test@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_failure(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["email"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP error")
            result = await engine.send_email(alert, "test@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_smtp_error_in_method(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["email"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value
            instance.send_message.side_effect = Exception("Send failed")
            result = await engine.send_email(alert, "test@example.com")
        assert result is False

# ============================================================
# TestSendWebhook
# ============================================================


class TestSendWebhook:
    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["webhook"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            instance.post = AsyncMock(return_value=mock_resp)
            result = await engine.send_webhook(alert, "https://hooks.example.com/alert")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_webhook_failure_status(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["webhook"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            instance.post = AsyncMock(return_value=mock_resp)
            result = await engine.send_webhook(alert, "https://hooks.example.com/alert")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_webhook_exception(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "Test", "condition": "test", "actions": ["webhook"],
            "timestamp": "2025-01-01T00:00:00", "context": {},
        }
        with patch("alerts.httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.post = AsyncMock(side_effect=Exception("Network error"))
            result = await engine.send_webhook(alert, "https://hooks.example.com/alert")
        assert result is False


# ============================================================
# TestProcess
# ============================================================


class TestProcess:
    @pytest.mark.asyncio
    async def test_process_no_trigger(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 0}}
        with patch("alerts.db") as mock_db:
            result = await engine.process(context)
        assert result == []

    @pytest.mark.asyncio
    async def test_process_logs_audit(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 99999}}
        with patch("alerts.db") as mock_db:
            with patch.dict(os.environ, {}, clear=False):
                result = await engine.process(context)
        assert len(result) >= 1
        mock_db.log_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_sends_email_when_configured(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 99999}}
        with patch("alerts.db") as mock_db:
            with patch.dict(os.environ, {"ALERT_EMAIL": "admin@example.com"}, clear=False):
                with patch.object(engine, "send_email", AsyncMock(return_value=True)):
                    result = await engine.process(context)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_process_actions_list(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 99999}}
        with patch("alerts.db") as mock_db:
            with patch.dict(os.environ, {}, clear=False):
                result = await engine.process(context)
        for alert in result:
            assert "rule" in alert
            assert "condition" in alert
            assert "actions" in alert
            assert "timestamp" in alert
            assert "context" in alert

    @pytest.mark.asyncio
    async def test_process_multiple_triggers(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {
            "stats": {"5min": 99999},
            "integrity_check": {"failed": True},
            "license": {"expires_in": 1},
        }
        with patch("alerts.db") as mock_db:
            with patch.dict(os.environ, {}, clear=False):
                result = await engine.process(context)
        names = [a["rule"] for a in result]
        assert "High masking volume" in names
        assert "Database integrity failure" in names
        assert "License expiring soon" in names

    @pytest.mark.asyncio
    async def test_process_skips_email_when_no_recipient(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        alert = {
            "rule": "High masking volume", "condition": "stats.5min > 10000",
            "actions": ["email"], "timestamp": "", "context": {},
        }
        with patch("alerts.db") as mock_db:
            with patch.dict(os.environ, {"ALERT_EMAIL": ""}, clear=False):
                with patch.object(engine, "send_email", AsyncMock()) as mock_send:
                    engine.evaluate = MagicMock(return_value=[alert])
                    result = await engine.process({})
        assert len(result) == 1
        assert mock_send.await_count == 0
