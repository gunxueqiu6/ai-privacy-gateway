path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add Tier enum and require_tier after the require_admin function
require_admin_end = '    return token\n\n\n# ==================== 主代理路由 ===================='

tier_code = '''    return token


# Tier enum and gating
from enum import Enum

class Tier(str, Enum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def __ge__(self, other: "Tier") -> bool:
        order = {"lite": 0, "pro": 1, "enterprise": 2}
        return order[self.value] >= order[other.value]


def require_tier(minimum: str):
    """Decorator/dependency that requires a minimum license tier.
    
    Returns 402 Payment Required if the current tier is too low.
    """
    async def _check(request: Request) -> None:
        current = config.tier
        order = {"lite": 0, "pro": 1, "enterprise": 2}
        if order.get(current, 0) < order.get(minimum, 0):
            raise HTTPException(
                status_code=402,
                detail=f"This feature requires at least {minimum.upper()} tier. Current: {current.upper()}"
            )
    return _check


'''

content = content.replace(require_admin_end, tier_code + require_admin_end)

# Update root endpoint to reflect dynamic tier
old_root = '''async def root() -> dict:
    """根路由 - 健康检查"""
    return {
        "status": "healthy",
        "service": "AI隐私网关",
        "version": "Lite"
    }'''

new_root = '''async def root() -> dict:
    """Root - health check with tier info."""
    return {
        "status": "healthy",
        "service": "AI Privacy Gateway",
        "version": config.tier.capitalize(),
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
    }'''

content = content.replace(old_root, new_root)

# Update version endpoint to reflect dynamic tier
old_version_endpoint = '@app.get("/admin/version")'
new_version_endpoint = '''@app.get("/admin/version")
@limiter.limit("10/minute")
async def get_version(request: Request) -> dict:
    """Get version info with license tier."""
    await require_admin(request)

    tier_display = {"lite": "Lite (Open Core)", "pro": "Pro (Team)", "enterprise": "Enterprise"}
    return {
        "version": "2.0",
        "version_type": tier_display.get(config.tier, "Unknown"),
        "version_display": config.tier.capitalize(),
        "tier": config.tier,
        "target_llm": config.TARGET_LLM,
        "license": {
            "team_id": config.license_team_id,
            "seats": config.license_seats,
            "expires_at": config.license_expires_at,
        },
    }


# Old version endpoint (replaced above)
@app.get("/admin/version")'''

# Find and replace the old get_version route
# Actually, need to find the old one and replace it
old_ver = '@app.get("/admin/version")\n@limiter.limit("10/minute")\nasync def get_version(request: Request) -> dict:\n    """获取版本信息"""\n    await require_admin(request)\n\n    return {\n        "version": "2.0",\n        "version_type": "Lite (Open Core)",\n        "version_display": "Lite",\n        "target_llm": config.TARGET_LLM\n    }'

# We may have a duplicate now. Let's just remove the old version endpoint and keep the new one.
# Actually, the easiest approach: replace the old with new directly
content = content.replace(old_ver, new_version_endpoint)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("main.py updated with require_tier, Tier enum, updated root/version endpoints")
