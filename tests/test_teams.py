"""Tests for team and user management (Phase 3)."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_seats(n=50):
    from config import config as cfg
    cfg.tier = "pro"
    cfg.license_seats = n


class TestTeamCRUD:
    def test_create_team(self):
        _ensure_seats()
        from team import create_team, get_team
        team = create_team("Test Team Alpha")
        assert team["id"].startswith("TM")
        assert team["name"] == "Test Team Alpha"
        fetched = get_team(team["id"])
        assert fetched is not None
        assert fetched["name"] == "Test Team Alpha"

    def test_get_nonexistent_team(self):
        from team import get_team
        assert get_team("NONEXISTENT_TEAM") is None

    def test_team_settings(self):
        _ensure_seats()
        from team import create_team, update_team_settings, get_team_settings
        team = create_team("Settings Team")
        update_team_settings(team["id"], {"theme": "dark", "lang": "zh"})
        settings = get_team_settings(team["id"])
        assert settings["theme"] == "dark"
        assert settings["lang"] == "zh"

    def test_get_team_settings_nonexistent(self):
        from team import get_team_settings
        assert get_team_settings("NONEXISTENT") == {}


class TestUserCRUD:
    @pytest.fixture
    def team(self):
        _ensure_seats()
        from team import create_team
        return create_team("Test Team for Users")

    def test_create_user(self, team):
        _ensure_seats()
        from team import create_user, get_user_by_id
        user = create_user(team["id"], "alice", "password123", "admin")
        assert user["username"] == "alice"
        assert user["role"] == "admin"
        assert user["api_key"].startswith("gw_api_")
        fetched = get_user_by_id(user["id"])
        assert fetched is not None
        assert fetched["username"] == "alice"

    def test_create_duplicate_username_fails(self, team):
        _ensure_seats()
        from team import create_user, TeamError
        create_user(team["id"], "bob", "pass1")
        with pytest.raises(TeamError, match="already exists"):
            create_user(team["id"], "bob", "pass2")

    def test_authenticate_success(self, team):
        _ensure_seats()
        from team import create_user, authenticate_user
        create_user(team["id"], "charlie", "secret123", "member")
        success, user, error = authenticate_user("charlie", "secret123")
        assert success
        assert user["username"] == "charlie"
        assert user["role"] == "member"
        assert "password_hash" not in user

    def test_authenticate_wrong_password(self, team):
        _ensure_seats()
        from team import create_user, authenticate_user
        create_user(team["id"], "dave", "correct")
        success, user, error = authenticate_user("dave", "wrong")
        assert not success
        assert user is None

    def test_authenticate_nonexistent_user(self):
        from team import authenticate_user
        success, user, error = authenticate_user("nobody", "nopass")
        assert not success

    def test_get_user_by_api_key(self, team):
        _ensure_seats()
        from team import create_user, get_user_by_api_key
        user = create_user(team["id"], "eve", "pass")
        found = get_user_by_api_key(user["api_key"])
        assert found is not None
        assert found["username"] == "eve"

    def test_get_user_by_invalid_api_key(self):
        from team import get_user_by_api_key
        assert get_user_by_api_key("invalid_key") is None

    def test_remove_user(self, team):
        _ensure_seats()
        from team import create_user, remove_user, get_user_by_id
        user = create_user(team["id"], "frank", "pass")
        assert remove_user(team["id"], user["id"])
        fetched = get_user_by_id(user["id"])
        assert fetched is None or fetched.get("is_active") == 0

    def test_update_user_role(self, team):
        _ensure_seats()
        from team import create_user, update_user_role, get_user_by_id
        user = create_user(team["id"], "grace", "pass", "member")
        assert update_user_role(team["id"], user["id"], "admin")
        updated = get_user_by_id(user["id"])
        assert updated["role"] == "admin"

    def test_update_user_invalid_role(self, team):
        _ensure_seats()
        from team import create_user, update_user_role
        user = create_user(team["id"], "heidi", "pass")
        assert not update_user_role(team["id"], user["id"], "superadmin")

    def test_regenerate_api_key(self, team):
        _ensure_seats()
        from team import create_user, regenerate_api_key
        user = create_user(team["id"], "ivan", "pass")
        old_key = user["api_key"]
        new_key = regenerate_api_key(user["id"], team["id"])
        assert new_key is not None
        assert new_key != old_key
        assert new_key.startswith("gw_api_")

    def test_regenerate_api_key_wrong_team(self):
        from team import regenerate_api_key
        assert regenerate_api_key("SOME_USER", "WRONG_TEAM") is None

    def test_member_count(self, team):
        _ensure_seats()
        from team import create_user, get_member_count
        assert get_member_count(team["id"]) == 0
        create_user(team["id"], "user1", "pass1")
        assert get_member_count(team["id"]) == 1
        create_user(team["id"], "user2", "pass2")
        assert get_member_count(team["id"]) == 2

    def test_get_team_members(self, team):
        _ensure_seats()
        from team import create_user, get_team_members
        create_user(team["id"], "member_a", "pass", "member")
        create_user(team["id"], "admin_a", "pass", "admin")
        members = get_team_members(team["id"])
        assert len(members) == 2
        assert members[0]["role"] == "admin"


class TestSessionManagement:
    @pytest.fixture
    def user_data(self):
        _ensure_seats()
        from team import create_team, create_user
        team = create_team("Session Test Team")
        user = create_user(team["id"], "sessionuser", "password")
        return user

    def test_create_and_validate_session(self, user_data):
        from team import create_session, validate_session
        token = create_session(user_data["id"])
        assert token is not None
        user = validate_session(token)
        assert user is not None
        assert user["username"] == "sessionuser"

    def test_validate_invalid_session(self):
        from team import validate_session
        assert validate_session("invalid_token") is None

    def test_delete_session(self, user_data):
        from team import create_session, validate_session, delete_session
        token = create_session(user_data["id"])
        assert validate_session(token) is not None
        assert delete_session(token)
        assert validate_session(token) is None


class TestSeatLimit:
    def test_seat_limit_enforced(self):
        from config import config as cfg
        cfg.tier = 'pro'; cfg.license_seats = 3
        from team import create_team, create_user, TeamError
        team = create_team("Limited Team")
        create_user(team["id"], "u1", "p1")
        create_user(team["id"], "u2", "p2")
        create_user(team["id"], "u3", "p3")
        with pytest.raises(TeamError, match="seat limit"):
            create_user(team["id"], "u4", "p4")
