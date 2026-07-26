path = r"G:\projects\ai数据隐私隔离\team.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    # Re-read config dynamically to get latest state (important for tests)
    from config import config as _cfg
    member_count = get_member_count(team_id)
    if member_count >= _cfg.license_seats:
        raise TeamError(
            f"Team has reached the seat limit ({_cfg.license_seats})",
            "SEAT_LIMIT_REACHED",
        )"""

new = """    # Re-read config dynamically to get latest state (important for tests)
    from config import config as _cfg
    # Only enforce seat limit when tier is pro or enterprise
    if _cfg.tier in ("pro", "enterprise"):
        member_count = get_member_count(team_id)
        if member_count >= _cfg.license_seats:
            raise TeamError(
                f"Team has reached the seat limit ({_cfg.license_seats})",
                "SEAT_LIMIT_REACHED",
            )"""

content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed seat limit to only apply for pro/enterprise tiers")
