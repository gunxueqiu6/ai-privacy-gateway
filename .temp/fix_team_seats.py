path = r"G:\projects\ai数据隐私隔离\team.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Change the seat limit check to dynamically read from config
old_check = """    # Check seat limit
    team = get_team(team_id)
    if not team:
        raise TeamError(f"Team not found: {team_id}", "TEAM_NOT_FOUND")

    member_count = get_member_count(team_id)
    if member_count >= _config.license_seats:
        raise TeamError(
            f"Team has reached the seat limit ({_config.license_seats})",
            "SEAT_LIMIT_REACHED",
        )"""

new_check = """    # Check seat limit
    team = get_team(team_id)
    if not team:
        raise TeamError(f"Team not found: {team_id}", "TEAM_NOT_FOUND")

    # Re-read config dynamically to get latest state (important for tests)
    from config import config as _cfg
    member_count = get_member_count(team_id)
    if member_count >= _cfg.license_seats:
        raise TeamError(
            f"Team has reached the seat limit ({_cfg.license_seats})",
            "SEAT_LIMIT_REACHED",
        )"""

content = content.replace(old_check, new_check)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed team.py seat limit check to use dynamic config")
