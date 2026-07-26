import re

path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add team import
old_import = "from license import get_license_service, LicenseError"
new_import = "from license import get_license_service, LicenseError\nfrom team import (\n    create_team, get_team, get_team_members, get_member_count,\n    create_user, authenticate_user, get_user_by_id, get_user_by_api_key,\n    remove_user, update_user_role, regenerate_api_key,\n    create_session, validate_session, delete_session,\n    update_team_settings, get_team_settings,\n    ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER, VALID_ROLES,\n    TeamError,\n)"
content = content.replace(old_import, new_import)

# Find and replace the require_tier function end to add new auth helpers
# Look for the closing blank line after require_tier
marker = "    return _check\n\n\n# Tier enum and gating"
new_marker = "    return _check\n\n\nasync def get_current_user(request: Request) -> Optional[Dict[str, Any]]:\n    \"\"\"Get the currently authenticated user from session token or API key.\"\"\"\n    session_token = request.cookies.get(\"user_session\")\n    if not session_token:\n        auth = request.headers.get(\"Authorization\", \"\")\n        if auth.startswith(\"Bearer \"):\n            session_token = auth[7:]\n    if session_token:\n        user = validate_session(session_token)\n        if user:\n            return user\n        user = get_user_by_api_key(session_token)\n        if user:\n            return user\n    return None\n\n\ndef require_role(*allowed_roles: str):\n    \"\"\"Dependency that requires the current user to have one of the given roles.\"\"\"\n    async def _check(request: Request) -> Dict[str, Any]:\n        user = await get_current_user(request)\n        if not user:\n            raise HTTPException(status_code=401, detail=\"Authentication required\")\n        if user.get(\"role\") not in allowed_roles:\n            raise HTTPException(status_code=403, detail=\"Insufficient permissions\")\n        return user\n    return _check\n\n\ndef get_team_id_from_request(request: Request) -> str:\n    \"\"\"Extract team_id from the current auth context. Falls back to license team.\"\"\"\n    auth = request.headers.get(\"Authorization\", \"\")\n    if auth.startswith(\"Bearer \"):\n        token = auth[7:]\n        user = get_user_by_api_key(token)\n        if user:\n            return user[\"team_id\"]\n        user = validate_session(token)\n        if user:\n            return user[\"team_id\"]\n    return config.license_team_id or \"default\"\n\n\n# Tier enum and gating"

content = content.replace(marker, new_marker)

print("Added auth helpers to main.py")

# Now add auth and team endpoints before the startup entry
startup_marker = "# ==================== 启动入口 ===================="
new_endpoints = """# ==================== User Auth API ====================

@app.post("/auth/login")
@limiter.limit("10/minute")
async def user_login(request: Request) -> JSONResponse:
    \"\"\"User login with username, password, and optional team_id.\"\"\"
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    team_id = body.get("team_id", "").strip() or None

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    client_ip = request.client.host if request.client else "unknown"
    is_locked, _ = db.check_login_attempt(client_ip)
    if is_locked:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    success, user, error = authenticate_user(username, password, team_id)
    if not success:
        db.record_login_attempt(client_ip, success=False)
        raise HTTPException(status_code=401, detail=error or "Login failed")

    db.record_login_attempt(client_ip, success=True)
    session_token = create_session(user["id"])
    db.log_audit(None, "user_login", {"user_id": user["id"], "team_id": user["team_id"]})

    response = JSONResponse({
        "status": "ok", "message": "Login successful",
        "user": user, "token": session_token,
    })
    response.set_cookie(key="user_session", value=session_token, httponly=True, samesite="strict", max_age=86400)
    return response


@app.post("/auth/logout")
@limiter.limit("10/minute")
async def user_logout(request: Request) -> JSONResponse:
    \"\"\"User logout.\"\"\"
    session_token = request.cookies.get("user_session")
    if not session_token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            session_token = auth[7:]
    if session_token:
        delete_session(session_token)
    response = JSONResponse({"status": "ok", "message": "Logged out"})
    response.delete_cookie("user_session")
    return response


@app.get("/auth/me")
@limiter.limit("30/minute")
async def auth_me(request: Request) -> JSONResponse:
    \"\"\"Get current user info.\"\"\"
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse(user)


# ==================== Team Management API ====================

@app.get("/admin/team")
@limiter.limit("10/minute")
async def admin_team(request: Request) -> JSONResponse:
    \"\"\"Get team info and member list (requires admin auth).\"\"\"
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team associated with this license")
    team = get_team(team_id)
    if not team:
        team = create_team(team_id[:16] if team_id else "Default Team", license_id=None)
    members = get_team_members(team_id)
    return JSONResponse({
        "team": team, "members": members,
        "member_count": get_member_count(team_id),
        "seat_limit": config.license_seats,
        "settings": get_team_settings(team_id),
    })


@app.post("/admin/team/members")
@limiter.limit("10/minute")
async def admin_team_add_member(request: Request) -> JSONResponse:
    \"\"\"Add a new team member (admin only).\"\"\"
    await require_admin(request)
    await require_tier("pro")
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "member")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team associated. Activate a license first.")
    try:
        user = create_user(team_id, username, password, role)
        db.log_audit(None, "member_added", {"user_id": user["id"], "team_id": team_id})
        return JSONResponse({"status": "ok", "user": user})
    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/admin/team/members/{user_id}")
@limiter.limit("10/minute")
async def admin_team_remove_member(user_id: str, request: Request) -> JSONResponse:
    \"\"\"Remove a team member (admin only).\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    if remove_user(team_id, user_id):
        db.log_audit(None, "member_removed", {"user_id": user_id, "team_id": team_id})
        return JSONResponse({"status": "ok", "message": "Member removed"})
    raise HTTPException(status_code=404, detail="Member not found")


@app.put("/admin/team/members/{user_id}/role")
@limiter.limit("10/minute")
async def admin_team_update_role(user_id: str, request: Request) -> JSONResponse:
    \"\"\"Update a member role (admin only).\"\"\"
    await require_admin(request)
    await require_tier("pro")
    body = await request.json()
    role = body.get("role", "").strip()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    if update_user_role(team_id, user_id, role):
        db.log_audit(None, "member_role_updated", {"user_id": user_id, "role": role})
        return JSONResponse({"status": "ok", "message": f"Role updated to {role}"})
    raise HTTPException(status_code=404, detail="Member not found")


@app.post("/admin/team/members/{user_id}/reset-api-key")
@limiter.limit("5/minute")
async def admin_team_reset_api_key(user_id: str, request: Request) -> JSONResponse:
    \"\"\"Regenerate a member API key (admin only).\"\"\"
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    new_key = regenerate_api_key(user_id, team_id)
    if new_key:
        db.log_audit(None, "api_key_reset", {"user_id": user_id})
        return JSONResponse({"status": "ok", "api_key": new_key})
    raise HTTPException(status_code=404, detail="Member not found")


@app.get("/admin/team/settings")
@limiter.limit("10/minute")
async def admin_team_get_settings(request: Request) -> JSONResponse:
    \"\"\"Get team settings (admin only).\"\"\"
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        return JSONResponse({})
    return JSONResponse(get_team_settings(team_id))


@app.put("/admin/team/settings")
@limiter.limit("10/minute")
async def admin_team_update_settings(request: Request) -> JSONResponse:
    \"\"\"Update team settings (admin only).\"\"\"
    await require_admin(request)
    body = await request.json()
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    update_team_settings(team_id, body)
    db.log_audit(None, "team_settings_updated", {"team_id": team_id})
    return JSONResponse({"status": "ok", "message": "Settings updated"})


# ==================== 启动入口 ===================="""

content = content.replace(startup_marker, new_endpoints)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("main.py updated with Phase 3 auth and team endpoints")
