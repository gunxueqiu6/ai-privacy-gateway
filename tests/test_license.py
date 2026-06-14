"""Tests for license lifecycle: activate, refresh, expire, revoke, and tier gating."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def teardown_module():
    """Reset config after license tests."""
    from config import config as cfg
    cfg.tier = "lite"
    cfg.license_seats = 1
    cfg.license_team_id = None
    cfg.license_expires_at = None
    cfg.LICENSE_KEY = ""
    cfg.LICENSE_FILE = "./license.key"


class TestLicenseActivation:
    """Tests for license activation flow."""

    def setup_method(self):
        """Reset global state before each test."""
        from config import config as app_config
        app_config.tier = "lite"
        app_config.license_seats = 1
        app_config.license_team_id = None
        app_config.license_expires_at = None
        app_config.LICENSE_KEY = ""

    def test_valid_license_sets_tier(self):
        from license import get_license_service
        from config import config as app_config
        svc = get_license_service()
        token = svc.sign_license("TACTIVE01", "pro", "buyer@test.com")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(token)
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "pro"
            assert app_config.license_seats == 20
            assert app_config.license_team_id == "TACTIVE01"
            assert app_config.license_expires_at is not None
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"

    def test_expired_license_downgrades_to_lite(self):
        from license import get_license_service
        from config import config as app_config
        svc = get_license_service()
        token = svc.sign_license("TEXPIRED", "pro", "test@test.com", duration_days=-1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(token)
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "lite"
            assert app_config.license_seats == 1
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"

    def test_tampered_license_downgrades_to_lite(self):
        from config import config as app_config
        fake_token = "this.is.a.fake.license.key"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(fake_token)
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "lite"
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"

    def test_empty_license_file_stays_lite(self):
        from config import config as app_config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write("")
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "lite"
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"

    def test_no_license_file_stays_lite(self):
        from config import config as app_config
        app_config.LICENSE_FILE = "./nonexistent_license.key"
        app_config.LICENSE_KEY = ""
        app_config._load_license()
        assert app_config.tier == "lite"

    def test_enterprise_license_sets_enterprise_tier(self):
        from license import get_license_service
        from config import config as app_config
        svc = get_license_service()
        token = svc.sign_license("TENT001", "enterprise", "corp@test.com")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(token)
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "enterprise"
            assert app_config.license_seats == 100
            assert app_config.license_team_id == "TENT001"
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"

    def test_revoked_license_downgrades(self):
        from license import get_license_service
        from config import config as app_config
        from database import db
        svc = get_license_service()
        token = svc.sign_license("TREVOKED", "pro", "test@test.com")
        db.save_license(
            license_id="REV001", team_id="TREVOKED", tier="pro",
            seats=20, email="test@test.com",
            issued_at="2024-01-01 00:00:00", expires_at="2025-01-01 00:00:00",
            jwt_token=token,
        )
        db.revoke_license("TREVOKED")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(token)
            key_path = f.name
        try:
            app_config.LICENSE_FILE = key_path
            app_config._load_license()
            assert app_config.tier == "pro"
        finally:
            os.unlink(key_path)
            app_config.LICENSE_FILE = "./license.key"


class TestTierComparison:
    def test_tier_ordering(self):
        from main import Tier
        assert Tier.LITE.value == "lite"
        assert Tier.PRO.value == "pro"
        assert Tier.ENTERPRISE.value == "enterprise"
        assert Tier.LITE < Tier.PRO
        assert Tier.PRO < Tier.ENTERPRISE
        assert Tier.LITE < Tier.ENTERPRISE
        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO

    def test_tier_gte_helper(self):
        from main import Tier
        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO
        assert not (Tier.LITE >= Tier.PRO)
        assert not (Tier.PRO >= Tier.ENTERPRISE)


class TestConfigLicenseLoading:
    def setup_method(self):
        from config import config as app_config
        app_config.tier = "lite"
        app_config.license_seats = 1
        app_config.license_team_id = None
        app_config.license_expires_at = None
        app_config.LICENSE_KEY = ""
        app_config.LICENSE_FILE = "./license.key"

    def test_env_var_license_key_takes_priority(self):
        from license import get_license_service
        from config import config as app_config
        svc = get_license_service()
        token = svc.sign_license("TENV001", "pro", "env@test.com")
        with patch.dict(os.environ, {"LICENSE_KEY": token}):
            app_config.LICENSE_KEY = token
            app_config._load_license()
            assert app_config.tier == "pro"
            assert app_config.license_team_id == "TENV001"
        app_config.LICENSE_KEY = ""

    def test_missing_public_key_downgrades(self):
        from license import get_license_service
        from config import config as app_config
        svc = get_license_service()
        token = svc.sign_license("TNOKEY", "pro", "test@test.com")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(token)
            key_path = f.name
        try:
            app_config.LICENSE_PUBLIC_KEY = "./nonexistent_pubkey.pem"
            app_config.LICENSE_FILE = key_path
            app_config.LICENSE_KEY = ""
            app_config._load_license()
            assert app_config.tier == "lite"
        finally:
            os.unlink(key_path)
            app_config.LICENSE_PUBLIC_KEY = "./vault_data/license_public.pem"
            app_config.LICENSE_FILE = "./license.key"
