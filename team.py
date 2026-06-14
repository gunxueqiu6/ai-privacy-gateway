"""
Team and user management module for Phase 3 multi-user system.
Handles user CRUD, team CRUD, API key generation, and role-based access.
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

import bcrypt

from database import db as _db
from config import config as _config

logger = logging.getLogger(__name__)

# Role definitions
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLE_VIEWER = "viewer"

VALID_ROLES = {ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER}

# API key prefix
API_KEY_PREFIX = "gw_api_"


class TeamError(Exception):
    """Raised when team/user operations fail."""

    def __init__(self, message: str, code: str = "TEAM_ERROR") -> None:
        super().__init__(message)
        self.code = code


def _generate_api_key() -> str:
    """Generate a unique API key for a user."""
    random_part = secrets.token_hex(24)
    return f"{API_KEY_PREFIX}{random_part}"


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def _now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ==================== Team Operations ====================


def create_team(name: str, license_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new team. Returns team dict."""
    team_id = f"TM{secrets.token_hex(6).upper()}"
    now = _now_iso()

    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO teams (id, name, license_id, created_at) VALUES (?, ?, ?, ?)",
            (team_id, name, license_id, now),
        )

    logger.info(f"Team created: {team_id} ({name})")
    return {"id": team_id, "name": name, "license_id": license_id, "created_at": now}


def get_team(team_id: str) -> Optional[Dict[str, Any]]:
    """Get a team by ID."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_team_members(team_id: str) -> List[Dict[str, Any]]:
    """Get all active members of a team."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, team_id, username, email, role, created_at, last_login_at, is_active "
            "FROM users WHERE team_id = ? AND is_active = 1 ORDER BY role, username",
            (team_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_member_count(team_id: str) -> int:
    """Count active members in a team."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE team_id = ? AND is_active = 1",
            (team_id,),
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0


def update_team_settings(team_id: str, settings: Dict[str, Any]) -> bool:
    """Update team settings (stored as JSON)."""
    import json
    settings_json = json.dumps(settings)
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE teams SET settings = ? WHERE id = ?",
            (settings_json, team_id),
        )
        return cursor.rowcount > 0


def get_team_settings(team_id: str) -> Dict[str, Any]:
    """Get team settings as dict."""
    team = get_team(team_id)
    if not team:
        return {}
    import json
    try:
        return json.loads(team.get("settings", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {}


# ==================== User Operations ====================


def create_user(
    team_id: str,
    username: str,
    password: str,
    role: str = ROLE_MEMBER,
    email: str = "",
) -> Dict[str, Any]:
    """Create a new user in a team. Raises TeamError on failure."""
    if role not in VALID_ROLES:
        raise TeamError(f"Invalid role: {role}", "INVALID_ROLE")

    # Check seat limit
    team = get_team(team_id)
    if not team:
        raise TeamError(f"Team not found: {team_id}", "TEAM_NOT_FOUND")

    # Re-read config dynamically to get latest state (important for tests)
    from config import config as _cfg
    # Only enforce seat limit when tier is pro or enterprise
    if _cfg.tier in ("pro", "enterprise"):
        member_count = get_member_count(team_id)
        if member_count >= _cfg.license_seats:
            raise TeamError(
                f"Team has reached the seat limit ({_cfg.license_seats})",
                "SEAT_LIMIT_REACHED",
            )

    user_id = f"USR{secrets.token_hex(6).upper()}"
    api_key = _generate_api_key()
    password_hash = _hash_password(password)
    now = _now_iso()

    try:
        with _db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users
                   (id, team_id, username, email, password_hash, role, api_key, created_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (user_id, team_id, username, email, password_hash, role, api_key, now),
            )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise TeamError(
                f"Username '{username}' already exists in this team",
                "USERNAME_EXISTS",
            )
        raise

    logger.info(f"User created: {user_id} ({username}) in team {team_id}")
    return {
        "id": user_id,
        "team_id": team_id,
        "username": username,
        "email": email,
        "role": role,
        "api_key": api_key,
        "created_at": now,
    }


def authenticate_user(username: str, password: str, team_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Authenticate a user by username and password.

    If team_id is provided, restricts search to that team.
    Returns (success, user_dict, error_message).
    """
    if team_id:
        query = "SELECT * FROM users WHERE team_id = ? AND username = ? AND is_active = 1"
        params = (team_id, username)
    else:
        query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
        params = (username,)

    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()

    if not row:
        return False, None, "Invalid username or password"

    user = dict(row)
    if not _verify_password(password, user["password_hash"]):
        return False, None, "Invalid username or password"

    # Update last login
    now = _now_iso()
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user["id"]))

    user["last_login_at"] = now
    # Don't return password hash
    del user["password_hash"]

    return True, user, None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            user = dict(row)
            if "password_hash" in user:
                del user["password_hash"]
            return user
        return None


def get_user_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Get a user by their API key."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,))
        row = cursor.fetchone()
        if row:
            user = dict(row)
            if "password_hash" in user:
                del user["password_hash"]
            return user
        return None


def remove_user(team_id: str, user_id: str) -> bool:
    """Deactivate a user (soft delete)."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE id = ? AND team_id = ?",
            (user_id, team_id),
        )
        return cursor.rowcount > 0


def update_user_role(team_id: str, user_id: str, role: str) -> bool:
    """Update a user's role."""
    if role not in VALID_ROLES:
        return False
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET role = ? WHERE id = ? AND team_id = ?",
            (role, user_id, team_id),
        )
        return cursor.rowcount > 0


def regenerate_api_key(user_id: str, team_id: str) -> Optional[str]:
    """Regenerate a user's API key."""
    new_key = _generate_api_key()
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET api_key = ? WHERE id = ? AND team_id = ?",
            (new_key, user_id, team_id),
        )
        if cursor.rowcount > 0:
            return new_key
        return None


def create_session(user_id: str, duration_hours: int = 24) -> str:
    """Create a session token for a user."""
    session_id = f"SES{secrets.token_hex(8).upper()}"
    token = secrets.token_urlsafe(32)
    now = _now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M:%S")

    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, token, now, expires),
        )

    return token


def validate_session(token: str) -> Optional[Dict[str, Any]]:
    """Validate a session token and return the associated user."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT u.*, s.expires_at as session_expires
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = ? AND u.is_active = 1""",
            (token,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    user = dict(row)
    # Check expiration
    try:
        expires_at = datetime.fromisoformat(user["session_expires"])
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            # Delete expired session
            with _db.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
    except (ValueError, TypeError):
        pass

    if "password_hash" in user:
        del user["password_hash"]
    return user


def delete_session(token: str) -> bool:
    """Delete a session (logout)."""
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return cursor.rowcount > 0


def find_or_create_oauth_user(
    team_id: str,
    email: str,
    name: str,
    provider: str,
    provider_id: str,
) -> Dict[str, Any]:
    """Find an existing user by OAuth identity, or create a new one.

    Looks up by (oauth_provider, oauth_id) in the users table.
    If found, returns the existing user (updating email/name if changed).
    If not found, creates a new user with a random password
    (since they will authenticate via OAuth).

    Args:
        team_id: The team to create the user in.
        email: The user's email from the OAuth provider.
        name: The user's display name from the OAuth provider.
        provider: The OAuth provider name ("google" or "github").
        provider_id: The user's unique ID from the provider.

    Returns:
        User dict (without password_hash).

    Raises:
        TeamError: If user creation fails.
    """
    if not team_id or not provider or not provider_id:
        raise TeamError(
            "team_id, provider, and provider_id are required",
            code="INVALID_OAUTH_PARAMS",
        )

    # Look up by OAuth identity
    with _db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE oauth_provider = ? AND oauth_id = ? AND is_active = 1",
            (provider, provider_id),
        )
        row = cursor.fetchone()

    if row:
        user = dict(row)
        # Update email/name if changed at the provider
        if user.get("email") != email or user.get("name") != name:
            with _db.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET email = ?, username = ? WHERE id = ?",
                    (email, name, user["id"]),
                )
            # Refresh the user dict with updated values
            user["email"] = email
            user["username"] = name
        if "password_hash" in user:
            del user["password_hash"]
        logger.info("OAuth user found: provider=%s, provider_id=%s", provider, provider_id)
        return user

    # Check seat limit before creating
    team = get_team(team_id)
    if not team:
        raise TeamError(f"Team not found: {team_id}", code="TEAM_NOT_FOUND")

    from config import config as _cfg
    if _cfg.tier in ("pro", "enterprise"):
        member_count = get_member_count(team_id)
        if member_count >= _cfg.license_seats:
            raise TeamError(
                f"Team has reached the seat limit ({_cfg.license_seats})",
                code="SEAT_LIMIT_REACHED",
            )

    # Create user with random password (they'll use OAuth)
    user_id = f"USR{secrets.token_hex(6).upper()}"
    api_key = _generate_api_key()
    random_password = secrets.token_urlsafe(24)
    password_hash = _hash_password(random_password)
    now = _now_iso()

    try:
        with _db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users
                   (id, team_id, username, email, password_hash, role, api_key,
                    oauth_provider, oauth_id, created_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    user_id, team_id, name, email, password_hash, ROLE_MEMBER,
                    api_key, provider, provider_id, now,
                ),
            )
    except Exception as e:
        if "UNIQUE" in str(e):
            # Race condition: user was created between our SELECT and INSERT
            # Retry the lookup
            return find_or_create_oauth_user(team_id, email, name, provider, provider_id)
        raise TeamError(f"Failed to create OAuth user: {str(e)}", code="OAUTH_USER_CREATE_FAILED")

    logger.info(
        "OAuth user created: name=%s, email=%s, provider=%s",
        name, email, provider,
    )
    return {
        "id": user_id,
        "team_id": team_id,
        "username": name,
        "email": email,
        "role": ROLE_MEMBER,
        "api_key": api_key,
        "oauth_provider": provider,
        "oauth_id": provider_id,
        "created_at": now,
    }
