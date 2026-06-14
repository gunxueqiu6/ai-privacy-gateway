"""
Alert notification engine for Enterprise tier.
Rule-based evaluation with SMTP email and webhook delivery.
"""
import json
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

from database import db
from config import config

logger = logging.getLogger(__name__)


class AlertRule:
    """A single alert rule with a condition and action."""

    def __init__(self, name: str, condition: str, actions: List[str], config: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.condition = condition
        self.actions = actions  # ["email", "webhook"]
        self.config = config or {}


class AlertEngine:
    """Rule-based alert evaluation and delivery engine."""

    def __init__(self) -> None:
        self.rules: List[AlertRule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load alert rules from config or use defaults."""
        # Default rules
        default_rules = [
            {
                "name": "High masking volume",
                "condition": "stats.5min > 10000",
                "actions": ["email"],
            },
            {
                "name": "Database integrity failure",
                "condition": "integrity_check.failed",
                "actions": ["email"],
            },
            {
                "name": "License expiring soon",
                "condition": "license.expires_in < 7days",
                "actions": ["email"],
            },
        ]

        # Try to load from environment
        import os
        rules_json = os.environ.get("ALERT_RULES", "")
        if rules_json:
            try:
                rules_data = json.loads(rules_json)
            except json.JSONDecodeError:
                rules_data = default_rules
        else:
            rules_data = default_rules

        for rule_data in rules_data:
            self.rules.append(AlertRule(**rule_data))

        logger.info(f"Loaded {len(self.rules)} alert rules")

    def evaluate(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all rules against the given context.

        Returns a list of triggered alerts.
        """
        triggered = []
        for rule in self.rules:
            if self._evaluate_condition(rule.condition, context):
                alert = {
                    "rule": rule.name,
                    "condition": rule.condition,
                    "actions": rule.actions,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": context,
                }
                triggered.append(alert)
        return triggered

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against context data."""
        try:
            # stats.5min > 10000
            if condition.startswith("stats."):
                parts = condition.replace("stats.", "").strip().split(" ")
                if len(parts) == 3:
                    field, op, threshold_str = parts
                    value = context.get("stats", {}).get(field, 0)
                    threshold = int(threshold_str)
                    if op == ">":
                        return value > threshold
                    elif op == ">=":
                        return value >= threshold
                    elif op == "<":
                        return value < threshold
                    elif op == "<=":
                        return value <= threshold

            # integrity_check.failed
            if condition.startswith("integrity_check."):
                key = condition.replace("integrity_check.", "").strip()
                return bool(context.get("integrity_check", {}).get(key, False))

            # license.expires_in < 7days
            if condition.startswith("license."):
                parts = condition.replace("license.", "").strip().split(" ")
                if len(parts) == 3:
                    field, op, threshold_str = parts
                    expires_in = context.get("license", {}).get(field, 9999)
                    # Parse "7days" -> 7
                    threshold = int(threshold_str.replace("days", "").strip())
                    if op == "<":
                        return expires_in < threshold
                    elif op == "<=":
                        return expires_in <= threshold

            return False
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    async def send_email(self, alert: Dict[str, Any], recipient: str) -> bool:
        """Send an alert via SMTP email."""
        smtp_host = config.__class__.__dict__.get("ALERT_SMTP_HOST", "")
        if not smtp_host:
            import os
            smtp_host = os.environ.get("ALERT_SMTP_HOST", "localhost")
            smtp_port = int(os.environ.get("ALERT_SMTP_PORT", "25"))
            smtp_user = os.environ.get("ALERT_SMTP_USER", "")
            smtp_pass = os.environ.get("ALERT_SMTP_PASS", "")
            smtp_from = os.environ.get("ALERT_SMTP_FROM", "alerts@privacygw.local")
        else:
            import os
            smtp_port = int(os.environ.get("ALERT_SMTP_PORT", "25"))
            smtp_user = os.environ.get("ALERT_SMTP_USER", "")
            smtp_pass = os.environ.get("ALERT_SMTP_PASS", "")
            smtp_from = os.environ.get("ALERT_SMTP_FROM", "alerts@privacygw.local")

        body = f"""Alert: {alert['rule']}
Condition: {alert['condition']}
Time: {alert['timestamp']}
Context: {json.dumps(alert['context'], indent=2)}
"""
        msg = MIMEText(body)
        msg["Subject"] = f"[PrivacyGW Alert] {alert['rule']}"
        msg["From"] = smtp_from
        msg["To"] = recipient

        try:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if smtp_user:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            logger.info(f"Alert email sent: {alert['rule']} -> {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False

    async def send_webhook(self, alert: Dict[str, Any], url: str) -> bool:
        """Send an alert via webhook (Slack, Feishu, custom)."""
        payload = {
            "text": f"[PrivacyGW Alert] {alert['rule']}\n{alert['condition']}\n{alert['timestamp']}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code < 400:
                    logger.info(f"Alert webhook sent: {alert['rule']} -> {url}")
                    return True
                logger.warning(f"Alert webhook failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to send alert webhook: {e}")
            return False

    async def process(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate rules and send notifications for triggered alerts.

        Returns list of triggered alerts.
        """
        triggered = self.evaluate(context)
        if not triggered:
            return []

        import os
        email_recipient = os.environ.get("ALERT_EMAIL", "")
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "")

        for alert in triggered:
            db.log_audit(None, "alert_triggered", alert)

            if "email" in alert["actions"] and email_recipient:
                await self.send_email(alert, email_recipient)
            if "webhook" in alert["actions"] and webhook_url:
                await self.send_webhook(alert, webhook_url)

        return triggered


# Global alert engine instance
_alert_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    """Get or create the alert engine instance."""
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine()
    return _alert_engine
