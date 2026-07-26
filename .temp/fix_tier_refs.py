path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix require_tier to work with string tier from config
old_require = '''def require_tier(minimum: str):
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
    return _check'''

new_require = '''def require_tier(minimum: str):
    """Decorator/dependency that requires a minimum license tier.
    
    Returns 402 Payment Required if the current tier is too low.
    """
    order = {"lite": 0, "pro": 1, "enterprise": 2}

    async def _check(request: Request) -> None:
        current = config.tier  # str: "lite", "pro", or "enterprise"
        if order.get(current, 0) < order.get(minimum, 0):
            raise HTTPException(
                status_code=402,
                detail=f"This feature requires at least {minimum.upper()} tier. Current: {current.upper()}"
            )
    return _check'''

content = content.replace(old_require, new_require)

# Fix root endpoint to use config.tier directly (it's still a string)
old_root_ref = '        "version": config.tier.capitalize(),'
new_root_ref = '        "version": config.tier.capitalize() if config.tier != "lite" else "Lite",'

content = content.replace(old_root_ref, new_root_ref)

# Fix version endpoint tier_display
old_display = '        "version_type": tier_display.get(config.tier, "Unknown"),'
new_display = '        "version_type": tier_display.get(config.tier, "Unknown"),\n        "version_display": config.tier.capitalize(),\n        "tier": config.tier,'

# Actually, need to remove duplicate version_display since we already have it
# Let me check what the version endpoint looks like now
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed require_tier and root references")
