"""
License signing and verification service.
Uses JWT RS256 for tamper-proof license keys.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Default RSA key paths
DEFAULT_PRIVATE_KEY_PATH = "./vault_data/license_private.pem"
DEFAULT_PUBLIC_KEY_PATH = "./vault_data/license_public.pem"

# License duration: 365 days
LICENSE_DURATION_DAYS = 365

# License tier seat limits
TIER_SEATS = {
    "pro": 20,
    "enterprise": 100,
    "lite": 1,
}


class LicenseError(Exception):
    """Raised when license operations fail."""

    def __init__(self, message: str, code: str = "LICENSE_ERROR") -> None:
        super().__init__(message)
        self.code = code


def _ensure_keys(private_key_path: str, public_key_path: str) -> None:
    """Generate an RSA key pair if it does not already exist."""
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        return

    os.makedirs(os.path.dirname(private_key_path), exist_ok=True)

    logger.info("Generating new RSA 2048 key pair for license signing...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Write private key
    with open(private_key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    # Restrict permissions on the private key
    os.chmod(private_key_path, 0o600)

    # Write public key
    public_key = private_key.public_key()
    with open(public_key_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    logger.info(f"RSA key pair generated: {private_key_path}, {public_key_path}")


class LicenseService:
    """Manages license signing, verification, and status checks."""

    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ) -> None:
        self.private_key_path = private_key_path or os.environ.get(
            "LICENSE_PRIVATE_KEY", DEFAULT_PRIVATE_KEY_PATH
        )
        self.public_key_path = public_key_path or os.environ.get(
            "LICENSE_PUBLIC_KEY", DEFAULT_PUBLIC_KEY_PATH
        )

        # Ensure keys exist
        _ensure_keys(self.private_key_path, self.public_key_path)

        # Load keys
        with open(self.private_key_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        with open(self.public_key_path, "rb") as f:
            self._public_key = serialization.load_pem_public_key(
                f.read(), backend=default_backend()
            )

    def sign_license(
        self,
        team_id: str,
        tier: str,
        email: str,
        seats: Optional[int] = None,
        duration_days: int = LICENSE_DURATION_DAYS,
    ) -> str:
        """Sign a license JWT token.

        Returns the signed JWT string that serves as the license key.
        """
        if tier not in TIER_SEATS:
            raise LicenseError(f"Unknown tier: {tier}", "INVALID_TIER")

        actual_seats = seats or TIER_SEATS[tier]
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=duration_days)

        payload = {
            "sub": "license",
            "tid": team_id,
            "tier": tier,
            "seats": actual_seats,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "email": email,
            "jti": str(uuid.uuid4()),
        }

        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        logger.info(
            f"License signed: team={team_id}, tier={tier}, "
            f"seats={actual_seats}, expires={expires_at.isoformat()}"
        )
        return token

    def verify_license(
        self, token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Verify a license token.

        Returns (is_valid, payload, error_message).
        """
        try:
            payload = jwt.decode(token, self._public_key, algorithms=["RS256"])
        except JWTError as e:
            logger.warning(f"License verification failed - invalid signature: {e}")
            return False, None, "Invalid license signature"
        except Exception as e:
            logger.error(f"License verification error: {e}")
            return False, None, f"License verification error: {e}"

        # Validate required fields
        if payload.get("sub") != "license":
            return False, None, "Not a valid license token"

        if not payload.get("tid"):
            return False, None, "Missing team ID in license"

        if not payload.get("tier"):
            return False, None, "Missing tier in license"

        # Check expiration
        exp = payload.get("exp", 0)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > exp:
            logger.warning(
                f"License expired: team={payload['tid']}, "
                f"expired={datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()}"
            )
            return False, payload, "License has expired"

        return True, payload, None

    def get_license_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode a license token without verifying signature.

        Useful for displaying metadata before activation.
        """
        try:
            return jwt.get_unverified_claims(token)  # type: ignore[attr-defined]
        except Exception:
            return None

    def is_license_expired(self, token: str) -> bool:
        """Check if a license token is expired (without verifying signature)."""
        info = self.get_license_info(token)
        if not info:
            return True
        exp = info.get("exp", 0)
        return int(datetime.now(timezone.utc).timestamp()) > exp


# Global license service instance
_license_service: Optional[LicenseService] = None


def get_license_service() -> LicenseService:
    """Get or create the global LicenseService instance."""
    global _license_service
    if _license_service is None:
        _license_service = LicenseService()
    return _license_service
