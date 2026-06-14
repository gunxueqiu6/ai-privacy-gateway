"""Tests for reports module (Phase 4)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReports:
    def test_get_daily_report_empty(self):
        from reports import get_daily_report
        report = get_daily_report(date="2099-01-01")
        assert report["total_count"] == 0
        assert report["date"] == "2099-01-01"

    def test_get_weekly_report(self):
        from reports import get_weekly_report
        report = get_weekly_report(end_date="2099-06-15")
        assert len(report) == 7
        for day in report:
            assert "date" in day

    def test_get_monthly_report(self):
        from reports import get_monthly_report
        report = get_monthly_report(year=2099, month=1)
        assert len(report) == 31

    def test_export_csv(self):
        from reports import export_report_csv
        csv_data = export_report_csv(start_date="2099-01-01", end_date="2099-01-02")
        assert "date" in csv_data
        assert "phone" in csv_data

    def test_get_summary_stats(self):
        from reports import get_summary_stats
        stats = get_summary_stats(days=30)
        assert "days" in stats
        assert stats["days"] == 30


class TestAlerts:
    def test_alert_engine_init(self):
        from alerts import get_alert_engine
        engine = get_alert_engine()
        assert len(engine.rules) >= 3

    def test_evaluate_stats_condition(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 15000}}
        triggered = engine.evaluate(context)
        triggered_names = [a["rule"] for a in triggered]
        assert "High masking volume" in triggered_names

    def test_evaluate_no_trigger(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"stats": {"5min": 100}}
        triggered = engine.evaluate(context)
        triggered_names = [a["rule"] for a in triggered]
        assert "High masking volume" not in triggered_names

    def test_evaluate_integrity_check(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"integrity_check": {"failed": True}}
        triggered = engine.evaluate(context)
        triggered_names = [a["rule"] for a in triggered]
        assert "Database integrity failure" in triggered_names

    def test_evaluate_license_expiring(self):
        from alerts import AlertEngine
        engine = AlertEngine()
        context = {"license": {"expires_in": 3}}
        triggered = engine.evaluate(context)
        triggered_names = [a["rule"] for a in triggered]
        assert "License expiring soon" in triggered_names


class TestEncryptedVault:
    def test_encrypt_decrypt(self):
        from database import EncryptedVault
        import os as _os
        key = _os.urandom(32)  # AES-256 key
        vault = EncryptedVault(key)
        plaintext = "sensitive data here"
        encrypted = vault.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = vault.decrypt(encrypted)
        assert decrypted == plaintext

    def test_no_key_passthrough(self):
        from database import EncryptedVault
        vault = EncryptedVault()
        assert not vault.available
        plaintext = "plain data"
        assert vault.encrypt(plaintext) == plaintext
        assert vault.decrypt(plaintext) == plaintext

    def test_different_encryptions(self):
        from database import EncryptedVault
        import os as _os
        key = _os.urandom(32)
        vault = EncryptedVault(key)
        e1 = vault.encrypt("hello")
        e2 = vault.encrypt("hello")
        assert e1 != e2  # Different nonces
        assert vault.decrypt(e1) == "hello"
        assert vault.decrypt(e2) == "hello"
