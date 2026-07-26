import re

path = r"G:\projects\ai数据隐私隔离\config.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add Optional import
content = content.replace(
    "import secrets\nimport os",
    "import secrets\nimport os\nfrom typing import Optional"
)

# Insert PayPal + license config before LISTEN_PORT line
marker = "    LISTEN_PORT: int = int(os.environ.get(\"LISTEN_PORT\", \"9999\"))"
new_fields = """    # PayPal configuration
    PAYPAL_CLIENT_ID: str = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET: str = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE: str = os.environ.get("PAYPAL_MODE", "sandbox")
    PAYPAL_WEBHOOK_ID: str = os.environ.get("PAYPAL_WEBHOOK_ID", "")

    # License configuration
    LICENSE_PRIVATE_KEY: str = os.environ.get("LICENSE_PRIVATE_KEY", "./vault_data/license_private.pem")
    LICENSE_PUBLIC_KEY: str = os.environ.get("LICENSE_PUBLIC_KEY", "./vault_data/license_public.pem")
    LICENSE_KEY: str = os.environ.get("LICENSE_KEY", "")
    LICENSE_FILE: str = os.environ.get("LICENSE_FILE", "./license.key")

    # Runtime license state (populated at startup)
    tier: str = "lite"
    license_seats: int = 1
    license_expires_at: Optional[str] = None
    license_team_id: Optional[str] = None

"""

content = content.replace(marker, new_fields + marker)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("config.py updated successfully")
