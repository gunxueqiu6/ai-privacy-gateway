"""
PayPal REST API v2 integration module.
Handles order creation, capture, webhook verification.
"""
import json
import logging
import base64
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple

import httpx

logger = logging.getLogger(__name__)

# PayPal API base URLs
PAYPAL_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE = "https://api-m.paypal.com"


class PayPalError(Exception):
    """Raised when a PayPal API call fails."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class PayPalClient:
    """PayPal REST API v2 client for processing payments."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        mode: str = "sandbox",
        webhook_id: Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = mode
        self.webhook_id = webhook_id
        self._base_url = PAYPAL_LIVE if mode == "live" else PAYPAL_SANDBOX
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> str:
        """Obtain an OAuth2 access token from PayPal."""
        if self._access_token:
            return self._access_token

        auth_str = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                headers={
                    "Authorization": f"Basic {auth_str}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        if resp.status_code != 200:
            logger.error(f"PayPal auth failed: {resp.status_code} {resp.text}")
            raise PayPalError("Failed to authenticate with PayPal", resp.status_code)

        data = resp.json()
        self._access_token = data["access_token"]
        return self._access_token

    async def create_order(
        self,
        amount: float,
        currency: str = "USD",
        tier: str = "pro",
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a PayPal order for a Pro or Enterprise license.

        Returns the order object containing the order ID for client-side approval.
        """
        access_token = await self._get_access_token()

        tier_prices = {"pro": 99.00, "enterprise": 999.00}
        price = tier_prices.get(tier, amount)

        tier_names = {"pro": "AI Privacy Gateway - Pro (Annual)", "enterprise": "AI Privacy Gateway - Enterprise (Annual)"}
        item_name = tier_names.get(tier, f"AI Privacy Gateway - {tier} License")

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{price:.2f}",
                    },
                    "description": item_name,
                }
            ],
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": f"APG-{tier}-{email or 'unknown'}",  # idempotency
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders",
                json=order_payload,
                headers=headers,
            )

        if resp.status_code not in (200, 201):
            logger.error(f"PayPal create_order failed: {resp.status_code} {resp.text}")
            raise PayPalError(
                "Failed to create PayPal order",
                resp.status_code,
                resp.json() if resp.text else None,
            )

        data = resp.json()
        logger.info(f"PayPal order created: {data.get('id')} ({tier})")
        return data

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """Capture a PayPal order after client-side approval.

        Returns the capture result with transaction details.
        """
        access_token = await self._get_access_token()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code not in (200, 201):
            logger.error(f"PayPal capture failed: {resp.status_code} {resp.text}")
            raise PayPalError(
                "Failed to capture PayPal payment",
                resp.status_code,
                resp.json() if resp.text else None,
            )

        data = resp.json()
        logger.info(f"PayPal order captured: {order_id}, status={data.get('status')}")
        return data

    def verify_webhook_signature(
        self,
        headers: Dict[str, str],
        body: str,
    ) -> bool:
        """Verify the authenticity of a PayPal webhook event.

        Uses the PayPal webhook signature verification algorithm.
        """
        if not self.webhook_id:
            logger.warning("Webhook verification skipped: no webhook_id configured")
            return False

        transmission_id = headers.get("paypal-transmission-id", "")
        transmission_time = headers.get("paypal-transmission-time", "")
        transmission_sig = headers.get("paypal-transmission-sig", "")
        cert_url = headers.get("paypal-cert-url", "")

        if not all([transmission_id, transmission_time, transmission_sig, cert_url]):
            logger.warning("Missing required PayPal webhook headers")
            return False

        # Build the expected signature payload
        expected_sig = (
            f"{transmission_id}|{transmission_time}|{self.webhook_id}|"
            f"{hashlib.sha256(body.encode()).hexdigest()}"
        )

        # For production, download the cert from cert_url and verify with openssl.
        # For sandbox/testing, we accept the signature as-is.
        if self.mode == "sandbox":
            logger.info(f"Webhook signature accepted in sandbox mode: {transmission_id}")
            return True

        # In live mode, perform full cert-based verification
        try:
            import subprocess
            import tempfile

            # Write the signature to a temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sig", delete=False) as sig_file:
                sig_file.write(transmission_sig)
                sig_path = sig_file.name

            # Write the expected payload to a temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as payload_file:
                payload_file.write(expected_sig)
                payload_path = payload_file.name

            # Download cert
            import urllib.request
            with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_file:
                urllib.request.urlretrieve(cert_url, cert_file.name)
                cert_path = cert_file.name

            # Verify using openssl
            result = subprocess.run(
                [
                    "openssl", "dgst", "-sha256", "-verify", cert_path,
                    "-signature", sig_path, payload_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            import os
            for p in [sig_path, payload_path, cert_path]:
                try:
                    os.unlink(p)
                except OSError:
                    pass

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False

    async def handle_webhook(
        self, event_body: Dict[str, Any], headers: Dict[str, str]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Process a PayPal webhook event.

        Returns (is_verified, parsed_event_data).
        """
        body_str = json.dumps(event_body)

        if not self.verify_webhook_signature(headers, body_str):
            return False, None

        event_type = event_body.get("event_type", "")
        resource = event_body.get("resource", {})

        logger.info(f"Webhook event received: {event_type}")

        parsed = {
            "event_type": event_type,
            "resource_type": resource.get("state", ""),
            "resource_id": resource.get("id", ""),
        }

        # Handle specific events
        if event_type == "CHECKOUT.ORDER.APPROVED":
            parsed["order_id"] = resource.get("id", "")
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            parsed["capture_id"] = resource.get("id", "")
            parsed["amount"] = resource.get("amount", {})

        return True, parsed


def get_paypal_client() -> Optional[PayPalClient]:
    """Create a PayPalClient from environment variables.

    Returns None if PayPal is not configured.
    """
    import os
    from config import config as app_config

    client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
    client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.info("PayPal not configured: missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET")
        return None

    mode = os.environ.get("PAYPAL_MODE", "sandbox")
    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "")

    return PayPalClient(
        client_id=client_id,
        client_secret=client_secret,
        mode=mode,
        webhook_id=webhook_id if webhook_id else None,
    )
