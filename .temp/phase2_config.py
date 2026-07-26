path = r"G:\projects\ai数据隐私隔离\config.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix __init__ to call _load_license
old_init = '    def __init__(self) -> None:\n        \"\"\"初始化配置，自动为明文密码生成哈希\"\"\"'
new_init = '    def __init__(self) -> None:\n        \"\"\"Initialize config, auto-generate password hash, and load license.\"\"\"'
content = content.replace(old_init, new_init)

# Add _load_license after the random password block and before the global config line
marker = '            print(f"\\n*** 随机生成的本次管理员密码: {random_pw} ***\\n")\n\n\n# 全局配置实例'
load_license_method = '''
        # Auto-load license on startup
        self._load_license()

    def _load_license(self) -> None:
        """Load license from environment variable or file, verify signature, set tier."""
        import os as _os
        from jose import jwt as _jwt
        from jose import JWTError as _JWTError

        # Try LICENSE_KEY env var first
        license_token = self.LICENSE_KEY
        if not license_token and _os.path.exists(self.LICENSE_FILE):
            try:
                with open(self.LICENSE_FILE, "r", encoding="utf-8") as f:
                    license_token = f.read().strip()
            except Exception:
                pass

        if not license_token:
            self.tier = "lite"
            return

        # Load public key for verification
        pub_key_path = self.LICENSE_PUBLIC_KEY
        if not _os.path.exists(pub_key_path):
            logging.getLogger(__name__).warning(
                f"License public key not found: {pub_key_path}, cannot verify license"
            )
            self.tier = "lite"
            return

        try:
            with open(pub_key_path, "rb") as f:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                pub_key = serialization.load_pem_public_key(f.read(), backend=default_backend())
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load license public key: {e}")
            self.tier = "lite"
            return

        try:
            payload = _jwt.decode(license_token, pub_key, algorithms=["RS256"])
        except _JWTError as e:
            logging.getLogger(__name__).warning(f"License verification failed: {e}")
            self.tier = "lite"
            self.license_seats = 1
            return

        if payload.get("sub") != "license":
            self.tier = "lite"
            return

        # Check expiration
        from datetime import datetime, timezone
        exp = payload.get("exp", 0)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > exp:
            logging.getLogger(__name__).warning(
                f"License expired at {datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()}"
            )
            self.tier = "lite"
            self.license_seats = 1
            return

        self.tier = payload.get("tier", "lite")
        self.license_seats = payload.get("seats", 1)
        self.license_team_id = payload.get("tid")
        self.license_expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        self.LICENSE_KEY = license_token

        logging.getLogger(__name__).info(
            f"License loaded: tier={self.tier}, team={self.license_team_id}, seats={self.license_seats}"
        )


# 全局配置实例'''

content = content.replace(marker, load_license_method)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("config.py updated with _load_license")
