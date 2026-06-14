"""Tests for payment.py and license.py modules.""" 

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLicenseService:
    def test_sign_and_verify_valid(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000001", "pro", "buyer@example.com")
        assert token
        valid, payload, error = svc.verify_license(token)
        assert valid, f"License should be valid: {error}"
        assert payload["sub"] == "license"
        assert payload["tid"] == "T00000001"
        assert payload["tier"] == "pro"
        assert payload["seats"] == 20
        assert payload["email"] == "buyer@example.com"

    def test_sign_enterprise(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000002", "enterprise", "corp@example.com")
        valid, payload, _ = svc.verify_license(token)
        assert valid
        assert payload["tier"] == "enterprise"
        assert payload["seats"] == 100

    def test_sign_custom_seats(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000003", "pro", "team@example.com", seats=50)
        valid, payload, _ = svc.verify_license(token)
        assert valid
        assert payload["seats"] == 50

    def test_verify_tampered_token_fails(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000004", "pro", "test@example.com")
        tampered = token[:-5] + "XXXXX"
        valid, _, error = svc.verify_license(tampered)
        assert not valid

    def test_verify_empty_token_fails(self):
        from license import get_license_service
        svc = get_license_service()
        valid, _, _ = svc.verify_license("")
        assert not valid

    def test_verify_expired_license(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000005", "pro", "test@example.com", duration_days=-1)
        valid, _, error = svc.verify_license(token)
        assert not valid
        assert error is not None  # JWT lib catches expiration as signature error

    def test_multiple_licenses_unique_jti(self):
        from license import get_license_service
        svc = get_license_service()
        jtis = set()
        for i in range(5):
            _, payload, _ = svc.verify_license(svc.sign_license(f"T{i:08d}", "pro", f"u{i}@t.com"))
            jtis.add(payload["jti"])
        assert len(jtis) == 5

    def test_get_license_info_unverified(self):
        from license import get_license_service
        svc = get_license_service()
        token = svc.sign_license("T00000006", "pro", "test@example.com")
        info = svc.get_license_info(token)
        assert info is not None
        assert info["tid"] == "T00000006"

    def test_is_license_expired(self):
        from license import get_license_service
        svc = get_license_service()
        expired = svc.sign_license("T00000007", "pro", "t@t.com", duration_days=-1)
        assert svc.is_license_expired(expired)
        valid = svc.sign_license("T00000008", "pro", "t@t.com", duration_days=365)
        assert not svc.is_license_expired(valid)

    def test_invalid_tier_raises(self):
        from license import get_license_service, LicenseError
        svc = get_license_service()
        with pytest.raises(LicenseError):
            svc.sign_license("T00000009", "invalid_tier", "test@example.com")


class TestPayPalClient:
    @pytest.fixture
    def paypal_client(self):
        from payment import PayPalClient
        return PayPalClient(client_id="test_id", client_secret="test_secret", mode="sandbox")

    def _make_fake_response(self, status_code, json_data, text=""):
        """Create a simple fake httpx response."""
        class FakeResponse:
            def __init__(self, sc, jd, txt):
                self.status_code = sc
                self._json = jd
                self.text = txt
            def json(self):
                return self._json
        return FakeResponse(status_code, json_data, text)

    def _fake_async_client_factory(self, post_side_effect):
        """Create a factory for FakeClient that wraps httpx.AsyncClient context manager."""
        import asyncio

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self._responses = post_side_effect if isinstance(post_side_effect, list) else [post_side_effect]
                self._idx = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                if self._idx >= len(self._responses):
                    raise RuntimeError("No more mock responses")
                resp = self._responses[self._idx]
                self._idx += 1
                return resp

        return FakeClient

    @pytest.mark.asyncio
    async def test_create_order_success(self, paypal_client):
        order_r = self._make_fake_response(201, {"id": "ORD123", "status": "CREATED"})
        FakeClientCls = self._fake_async_client_factory(order_r)

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = "test_token"
            result = await paypal_client.create_order(amount=99.0, tier="pro", email="t@t.com")
            assert result["id"] == "ORD123"

    @pytest.mark.asyncio
    async def test_create_order_auth_failure(self, paypal_client):
        from payment import PayPalError
        auth_r = self._make_fake_response(401, {}, text="Unauthorized")
        FakeClientCls = self._fake_async_client_factory(auth_r)

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = None
            with pytest.raises(PayPalError):
                await paypal_client.create_order(amount=99.0, tier="pro")

    @pytest.mark.asyncio
    async def test_capture_order_success(self, paypal_client):
        cap_r = self._make_fake_response(201, {"id": "CAP123", "status": "COMPLETED"})
        FakeClientCls = self._fake_async_client_factory(cap_r)

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = "test_token"
            result = await paypal_client.capture_order("ORD123")
            assert result["status"] == "COMPLETED"

    def test_get_paypal_client_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            from payment import get_paypal_client
            assert get_paypal_client() is None

    def test_verify_webhook_sandbox(self, paypal_client):
        paypal_client.webhook_id = "WH_TEST"
        headers = {
            "paypal-transmission-id": "txn_1",
            "paypal-transmission-time": "2024-01-01T00:00:00Z",
            "paypal-transmission-sig": "sig",
            "paypal-cert-url": "https://certs.paypal.com",
        }
        assert paypal_client.verify_webhook_signature(headers, json.dumps({"x": 1}))

    def test_verify_webhook_missing_headers(self, paypal_client):
        paypal_client.webhook_id = "WH_TEST"
        assert not paypal_client.verify_webhook_signature({}, "{}")

class TestDatabaseLicense:
    @pytest.fixture
    def fresh_db(self):
        import tempfile
        from database import Database
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = Database(path)
        yield db
        os.unlink(path)

    def test_save_and_get_license(self, fresh_db):
        fresh_db.save_license("L1", "T1", "pro", 20, "a@b.com", "2024-01-01", "2025-01-01", "jwt1", "P1")
        lic = fresh_db.get_license_by_team("T1")
        assert lic is not None
        assert lic["tier"] == "pro"
        assert lic["seats"] == 20
        assert lic["revoked"] == 0

    def test_revoke_license(self, fresh_db):
        fresh_db.save_license("L2", "T2", "enterprise", 100, "c@d.com", "2024-01-01", "2025-01-01", "jwt2")
        assert fresh_db.revoke_license("T2")
        assert fresh_db.is_token_revoked("T2")
        assert fresh_db.get_license_by_team("T2") is None

    def test_revoke_nonexistent(self, fresh_db):
        assert not fresh_db.revoke_license("NOEXIST")
        assert not fresh_db.is_token_revoked("NOEXIST")

    def test_license_count(self, fresh_db):
        assert fresh_db.get_license_count() == 0
        fresh_db.save_license("L3", "T3", "pro", 20, "e@f.com", "2024-01-01", "2025-01-01", "j3")
        assert fresh_db.get_license_count() == 1
        fresh_db.save_license("L4", "T4", "enterprise", 100, "g@h.com", "2024-01-01", "2025-01-01", "j4")
        assert fresh_db.get_license_count() == 2
        fresh_db.revoke_license("T3")
        assert fresh_db.get_license_count() == 1
