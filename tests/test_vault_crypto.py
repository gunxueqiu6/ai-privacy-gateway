"""vault_crypto.py — AES-256-GCM 加密/解密测试"""
import os
import pytest
from vault_crypto import VaultCrypto


@pytest.fixture
def vc():
    key = os.urandom(32)
    return VaultCrypto(key=key)


class TestVaultCryptoInit:
    def test_valid_32_byte_key(self):
        key = os.urandom(32)
        vc = VaultCrypto(key)
        assert vc is not None

    def test_invalid_key_length_raises(self):
        with pytest.raises(ValueError, match="exactly 32 bytes"):
            VaultCrypto(b"short")


class TestEncryptDecrypt:
    def test_roundtrip_ascii(self, vc):
        encrypted = vc.encrypt("hello world")
        assert encrypted != "hello world"
        decrypted = vc.decrypt(encrypted)
        assert decrypted == "hello world"

    def test_roundtrip_chinese(self, vc):
        plaintext = "张三，身份证号 110101199003071234"
        encrypted = vc.encrypt(plaintext)
        decrypted = vc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_empty_string(self, vc):
        encrypted = vc.encrypt("")
        decrypted = vc.decrypt(encrypted)
        assert decrypted == ""

    def test_roundtrip_long_text(self, vc):
        plaintext = "A" * 10000
        encrypted = vc.encrypt(plaintext)
        decrypted = vc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_roundtrip_special_chars(self, vc):
        plaintext = '{"key": "value", "nested": {"a": [1,2,3]}}'
        encrypted = vc.encrypt(plaintext)
        decrypted = vc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encryption_is_non_deterministic(self, vc):
        """每个 nonce 随机，所以加密结果不一致"""
        c1 = vc.encrypt("hello")
        c2 = vc.encrypt("hello")
        assert c1 != c2  # different nonce each time

    def test_encrypted_is_base64(self, vc):
        encrypted = vc.encrypt("hello")
        import base64
        # should be valid base64
        base64.b64decode(encrypted)


class TestDecryptErrors:
    def test_wrong_key_fails(self, vc):
        encrypted = vc.encrypt("hello")
        wrong_vc = VaultCrypto(os.urandom(32))
        result = wrong_vc.decrypt(encrypted)
        assert result is None

    def test_tampered_data_fails(self, vc):
        import base64
        encrypted = vc.encrypt("secret")
        # decode, flip a byte in the ciphertext, re-encode
        payload = bytearray(base64.b64decode(encrypted))
        payload[len(payload) // 2] ^= 0xFF  # flip bits in the middle
        tampered = base64.b64encode(bytes(payload)).decode("ascii")
        result = vc.decrypt(tampered)
        assert result is None

    def test_short_ciphertext_fails(self, vc):
        result = vc.decrypt("short")
        assert result is None

    def test_invalid_base64_fails(self, vc):
        result = vc.decrypt("!!!not base64!!!")
        assert result is None

    def test_empty_ciphertext_fails(self, vc):
        result = vc.decrypt("")
        assert result is None
