path = r"G:\projects\ai数据隐私隔离\database.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add encrypted vault class at the end of the file, before db = Database()
marker = "db = Database()"
encrypted_class = """
class EncryptedVault:
    \"\"\"Enterprise encrypted storage for vault mappings using AES-GCM.\"\"\"
    
    def __init__(self, key: Optional[bytes] = None) -> None:
        if key:
            self._key = key
        else:
            import os as _os
            key_env = _os.environ.get("VAULT_ENCRYPTION_KEY", "")
            if key_env:
                import base64
                self._key = base64.b64decode(key_env)
            else:
                self._key = None
    
    @property
    def available(self) -> bool:
        return self._key is not None
    
    def encrypt(self, plaintext: str) -> str:
        \"\"\"Encrypt plaintext using AES-GCM. Returns base64-encoded ciphertext.\"\"\"
        if not self.available:
            return plaintext
        import os as _os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        
        aesgcm = AESGCM(self._key)
        nonce = _os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Combine nonce + ciphertext and base64 encode
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode()
    
    def decrypt(self, ciphertext_b64: str) -> str:
        \"\"\"Decrypt base64-encoded ciphertext back to plaintext.\"\"\"
        if not self.available:
            return ciphertext_b64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        
        aesgcm = AESGCM(self._key)
        combined = base64.b64decode(ciphertext_b64)
        nonce = combined[:12]
        ciphertext = combined[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()


# Global encrypted vault instance
encrypted_vault = EncryptedVault()

db = Database()
"""

content = content.replace(marker, encrypted_class)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("database.py updated with EncryptedVault")
