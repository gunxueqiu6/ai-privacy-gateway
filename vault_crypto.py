"""
Vault encryption module — AES-256-GCM for PII mapping values.

When VAULT_ENCRYPT_KEY is configured, real PII values are encrypted before
storage and decrypted on read.  Plaintext fallback provides backward
compatibility with data written before encryption was enabled.
"""

import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_crypto_instance: Optional["VaultCrypto"] = None


class VaultCrypto:
    """AES-256-GCM encrypt / decrypt for vault PII values."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError(f"AES key must be exactly 32 bytes, got {len(key)}")
        self._key = key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* with AES-256-GCM.

        Returns base64-encoded ``nonce (12) + ciphertext + tag (16)``.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        # encrypt() already appends the 16-byte GCM tag
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> Optional[str]:
        """Decrypt a value previously produced by :meth:`encrypt`.

        Returns the plaintext string on success, or *None* on failure
        (invalid encoding, wrong key, tampered data, …).
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            payload = base64.b64decode(ciphertext_b64)
            if len(payload) < 12 + 16:  # nonce + minimum ciphertext + tag
                return None
            nonce = payload[:12]
            ciphertext = payload[12:]
            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception:
            logger.debug("Failed to decrypt vault value", exc_info=True)
            return None


def get_vault_crypto() -> Optional[VaultCrypto]:
    """Return the singleton :class:`VaultCrypto`, or *None* if encryption is disabled.

    The instance is created once from :attr:`config.Config.VAULT_ENCRYPT_KEY`.
    When the key is empty, encryption is disabled (returns *None*).
    When the key is not exactly 32 bytes, a 32-byte key is derived via SHA-256.
    """
    global _crypto_instance

    if _crypto_instance is not None:
        return _crypto_instance

    from config import config as app_config

    key_str = app_config.VAULT_ENCRYPT_KEY
    if not key_str:
        logger.info("VAULT_ENCRYPT_KEY is empty — vault encryption disabled")
        return None

    key_bytes = key_str.encode("utf-8")
    if len(key_bytes) != 32:
        key_bytes = hashlib.sha256(key_bytes).digest()
        logger.info("VAULT_ENCRYPT_KEY is not 32 bytes — derived 32-byte key via SHA-256")

    _crypto_instance = VaultCrypto(key_bytes)
    logger.info("Vault encryption initialised (AES-256-GCM)")
    return _crypto_instance
