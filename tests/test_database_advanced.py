"""
Advanced database tests — encryption, audit integrity, custom regex rules, stateless mode.
"""
import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock


class TestDatabaseAudit:
    """Audit log integrity tests"""

    def test_verify_audit_integrity_empty(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            assert db.verify_audit_integrity() is True
        finally:
            os.unlink(db_path)

    def test_verify_audit_integrity_tampered(self):
        """Tampering with an earlier record is detected by the hash chain."""
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.log_audit("s1", "action1", {"k": "v1"})
            db.log_audit("s2", "action2", {"k": "v2"})
            assert db.verify_audit_integrity() is True

            # Tamper with the FIRST record — this should be caught because
            # the second record's prev_hash chains back to the first.
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE audit_log SET action = 'tampered' WHERE id = 1"
                )
            assert db.verify_audit_integrity() is False
        finally:
            os.unlink(db_path)

    def test_audit_log_single_entry(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.log_audit("s1", "test_action")
            assert db.verify_audit_integrity() is True
        finally:
            os.unlink(db_path)


class TestDatabaseCustomRegexRules:
    """Custom regex rules CRUD"""

    def test_add_and_get_custom_regex_rule(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            rule_id = db.add_custom_regex_rule("test_rule", r"\d+", "custom")
            assert rule_id > 0
            rules = db.get_custom_regex_rules()
            assert len(rules) == 1
            assert rules[0]["name"] == "test_rule"
            assert rules[0]["pattern"] == r"\d+"
            assert rules[0]["enabled"] == 1
        finally:
            os.unlink(db_path)

    def test_add_duplicate_name_returns_minus_one(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.add_custom_regex_rule("dup_name", r"\d+", "custom")
            result = db.add_custom_regex_rule("dup_name", r"\w+", "phone")
            assert result == -1
        finally:
            os.unlink(db_path)

    def test_delete_custom_regex_rule(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            rule_id = db.add_custom_regex_rule("del_test", r"\d+", "custom")
            assert db.delete_custom_regex_rule(rule_id) is True
            assert db.delete_custom_regex_rule(9999) is False  # nonexistent
            rules = db.get_custom_regex_rules()
            assert len(rules) == 0
        finally:
            os.unlink(db_path)

    def test_toggle_custom_regex_rule(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            rule_id = db.add_custom_regex_rule("tog_test", r"\d+", "custom")
            db.toggle_custom_regex_rule(rule_id, enabled=False)
            rules = db.get_custom_regex_rules()
            assert rules[0]["enabled"] == 0
            db.toggle_custom_regex_rule(rule_id, enabled=True)
            rules = db.get_custom_regex_rules()
            assert rules[0]["enabled"] == 1
        finally:
            os.unlink(db_path)


class TestDatabaseEncryption:
    """Encryption integration with database"""

    def test_encrypted_save_and_retrieve(self, monkeypatch):
        from database import Database
        import tempfile
        monkeypatch.setenv("VAULT_ENCRYPT_KEY", "a" * 32)
        from config import Config
        old_key = Config.VAULT_ENCRYPT_KEY
        Config.VAULT_ENCRYPT_KEY = "a" * 32
        try:
            # Force reload vault_crypto module
            import vault_crypto
            vault_crypto._crypto_instance = None

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                db_path = f.name
            try:
                db = Database(db_path=db_path, mapping_ttl=3600)
                db.save_mappings("enc_sess", {"[PII_TEST]": "secret_value"}, "test")
                retrieved = db.get_mapping("enc_sess", "[PII_TEST]")
                assert retrieved == "secret_value"

                # Verify value is encrypted in the database
                import sqlite3
                conn = sqlite3.connect(db_path)
                row = conn.execute(
                    "SELECT real_value FROM vault_mappings WHERE placeholder = ?",
                    ("[PII_TEST]",)
                ).fetchone()
                conn.close()
                assert row is not None
                assert row[0] != "secret_value"  # should be encrypted
            finally:
                os.unlink(db_path)
        finally:
            Config.VAULT_ENCRYPT_KEY = old_key
            import vault_crypto
            vault_crypto._crypto_instance = None

    def test_encryption_off_plaintext_storage(self):
        """When VAULT_ENCRYPT_KEY is empty, values are stored as plaintext."""
        from database import Database
        import tempfile
        # Ensure vault crypto is disabled for this test
        import vault_crypto
        vault_crypto._crypto_instance = None
        import config as cfg_mod
        old_key = cfg_mod.Config.VAULT_ENCRYPT_KEY
        cfg_mod.Config.VAULT_ENCRYPT_KEY = ""

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.save_mappings("plain_sess", {"[PII_X]": "plain_value"}, "test")
            retrieved = db.get_mapping("plain_sess", "[PII_X]")
            assert retrieved == "plain_value"

            # Verify value is stored as plaintext
            import sqlite3
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT real_value FROM vault_mappings WHERE placeholder = ?",
                ("[PII_X]",)
            ).fetchone()
            conn.close()
            assert row[0] == "plain_value"
        finally:
            cfg_mod.Config.VAULT_ENCRYPT_KEY = old_key
            vault_crypto._crypto_instance = None
            os.unlink(db_path)


class TestDatabaseEdgeCases:
    """Additional database edge cases"""

    def test_get_mapping_missing(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            result = db.get_mapping("nonexistent_session", "[PII_XXXX]")
            assert result is None
        finally:
            os.unlink(db_path)

    def test_clear_session_twice(self):
        from database import db
        db.save_mappings("dup_clear_sess", {"[A]": "v1"}, "test")
        db.clear_session("dup_clear_sess")
        # Second clear should not raise
        db.clear_session("dup_clear_sess")

    def test_stats_organization_mapped_to_org(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.update_stats({"organization": 3, "phone": 1})
            # Check org_count got incremented
            with db.get_conn() as conn:
                row = conn.execute(
                    "SELECT org_count, phone_count FROM stats"
                ).fetchone()
                assert row["org_count"] >= 3
                assert row["phone_count"] >= 1
        finally:
            os.unlink(db_path)

    def test_update_stats_unknown_field_skipped(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.update_stats({"unknown_field": 5, "phone": 1})  # should not raise
            with db.get_conn() as conn:
                row = conn.execute(
                    "SELECT phone_count, total_count FROM stats"
                ).fetchone()
                assert row["phone_count"] >= 1
        finally:
            os.unlink(db_path)

    def test_update_stats_empty(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            db.update_stats({})  # should not raise
        finally:
            os.unlink(db_path)

    def test_cleanup_expired_mappings_in_memory(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=-1)
            db.save_mappings("expired_sess", {"[PII_X]": "val"}, "test")
            deleted = db.cleanup_expired_mappings(retention_hours=0)
            assert deleted >= 0
        finally:
            os.unlink(db_path)

    def test_login_lockout_reached(self):
        from database import Database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = Database(db_path=db_path, mapping_ttl=3600)
            ip = "192.168.50.1"
            for _ in range(5):
                db.record_login_attempt(ip, success=False)
            locked, remaining = db.check_login_attempt(ip)
            assert locked is True
            assert remaining == 0
            # Cleanup
            db.record_login_attempt(ip, success=True)
        finally:
            os.unlink(db_path)
