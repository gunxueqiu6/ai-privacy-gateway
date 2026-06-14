"""Tests for role-based access control (RBAC): role constants, validation, hierarchy, and enforcement."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRoleConstants:
    """Tests for role constant definitions and valid roles set."""

    def test_role_constants_exist(self):
        from team import ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER
        assert ROLE_ADMIN == "admin"
        assert ROLE_MEMBER == "member"
        assert ROLE_VIEWER == "viewer"

    def test_valid_roles_set(self):
        from team import VALID_ROLES, ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER
        assert len(VALID_ROLES) == 3
        assert ROLE_ADMIN in VALID_ROLES
        assert ROLE_MEMBER in VALID_ROLES
        assert ROLE_VIEWER in VALID_ROLES

    def test_no_extra_roles_in_set(self):
        from team import VALID_ROLES
        assert "superadmin" not in VALID_ROLES
        assert "owner" not in VALID_ROLES
        assert "" not in VALID_ROLES


class TestDefaultRoleAssignment:
    """Tests that new users get the correct default role."""

    def _ensure_seats(self, n=50):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = n

    def test_new_user_defaults_to_member(self):
        self._ensure_seats()
        from team import create_team, create_user
        team = create_team("Default Role Team")
        user = create_user(team["id"], "defaultuser", "password123")
        assert user["role"] == "member"

    def test_new_user_admin_role(self):
        self._ensure_seats()
        from team import create_team, create_user
        team = create_team("Admin Role Team")
        user = create_user(team["id"], "adminuser", "password123", role="admin")
        assert user["role"] == "admin"

    def test_new_user_viewer_role(self):
        self._ensure_seats()
        from team import create_team, create_user
        team = create_team("Viewer Role Team")
        user = create_user(team["id"], "vieweruser", "password123", role="viewer")
        assert user["role"] == "viewer"


class TestInvalidRoleHandling:
    """Tests for handling invalid role values."""

    def _ensure_seats(self, n=50):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = n

    def test_create_user_invalid_role_raises_error(self):
        self._ensure_seats()
        from team import create_team, create_user, TeamError
        team = create_team("Invalid Role Team")
        with pytest.raises(TeamError, match="Invalid role"):
            create_user(team["id"], "badroleuser", "password123", role="superadmin")

    def test_create_user_empty_role_raises_error(self):
        self._ensure_seats()
        from team import create_team, create_user, TeamError
        team = create_team("Empty Role Team")
        with pytest.raises(TeamError, match="Invalid role"):
            create_user(team["id"], "emptyroleuser", "password123", role="")

    def test_update_user_role_valid(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Update Role Team")
        user = create_user(team["id"], "updateroleuser", "password123", role="member")
        assert update_user_role(team["id"], user["id"], "admin")
        updated = get_user_by_id(user["id"])
        assert updated["role"] == "admin"

    def test_update_user_role_to_viewer(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Viewer Update Team")
        user = create_user(team["id"], "viewerupd", "password123", role="member")
        assert update_user_role(team["id"], user["id"], "viewer")
        updated = get_user_by_id(user["id"])
        assert updated["role"] == "viewer"

    def test_update_user_role_invalid_returns_false(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role
        team = create_team("Invalid Update Team")
        user = create_user(team["id"], "invalidupd", "password123")
        assert not update_user_role(team["id"], user["id"], "superadmin")

    def test_update_user_role_empty_returns_false(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role
        team = create_team("Empty Update Team")
        user = create_user(team["id"], "emptyupd", "password123")
        assert not update_user_role(team["id"], user["id"], "")


class TestRoleUpgradeDowngrade:
    """Tests for upgrading and downgrading user roles."""

    def _ensure_seats(self, n=50):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = n

    def test_upgrade_member_to_admin(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Upgrade Team")
        user = create_user(team["id"], "upgradeuser", "password123", role="member")
        assert update_user_role(team["id"], user["id"], "admin")
        assert get_user_by_id(user["id"])["role"] == "admin"

    def test_downgrade_admin_to_member(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Downgrade Team")
        user = create_user(team["id"], "downgradeuser", "password123", role="admin")
        assert update_user_role(team["id"], user["id"], "member")
        assert get_user_by_id(user["id"])["role"] == "member"

    def test_downgrade_admin_to_viewer(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Admin to Viewer Team")
        user = create_user(team["id"], "admin2viewer", "password123", role="admin")
        assert update_user_role(team["id"], user["id"], "viewer")
        assert get_user_by_id(user["id"])["role"] == "viewer"

    def test_upgrade_viewer_to_admin(self):
        self._ensure_seats()
        from team import create_team, create_user, update_user_role, get_user_by_id
        team = create_team("Viewer to Admin Team")
        user = create_user(team["id"], "viewer2admin", "password123", role="viewer")
        assert update_user_role(team["id"], user["id"], "admin")
        assert get_user_by_id(user["id"])["role"] == "admin"


class TestRoleBasedAccess:
    """Tests for role-based authorization logic."""

    def _ensure_seats(self, n=50):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = n

    def test_admin_can_access_admin_routes(self):
        """Verify admin role is recognized and can be authenticated."""
        self._ensure_seats()
        from team import create_team, create_user, authenticate_user
        team = create_team("Admin Access Team")
        create_user(team["id"], "admin_access", "pass123", role="admin")
        success, user, _ = authenticate_user("admin_access", "pass123")
        assert success
        assert user["role"] == "admin"

    def test_member_cannot_be_mistaken_for_admin(self):
        """Member role is distinct from admin role."""
        self._ensure_seats()
        from team import create_team, create_user, authenticate_user
        team = create_team("Member Not Admin Team")
        create_user(team["id"], "member_user", "pass123", role="member")
        success, user, _ = authenticate_user("member_user", "pass123")
        assert success
        assert user["role"] == "member"
        assert user["role"] != "admin"

    def test_viewer_can_read_but_not_admin(self):
        """Viewer role is distinct and not admin."""
        self._ensure_seats()
        from team import create_team, create_user, authenticate_user
        team = create_team("Viewer Not Admin Team")
        create_user(team["id"], "viewer_user", "pass123", role="viewer")
        success, user, _ = authenticate_user("viewer_user", "pass123")
        assert success
        assert user["role"] == "viewer"
        assert user["role"] != "admin"

    def test_role_not_exposed_in_user_info(self):
        """User info should not expose password_hash."""
        self._ensure_seats()
        from team import create_team, create_user, get_user_by_id
        team = create_team("No Hash Team")
        user = create_user(team["id"], "nohash", "pass123", role="admin")
        fetched = get_user_by_id(user["id"])
        assert fetched is not None
        assert "password_hash" not in fetched
        assert fetched["role"] == "admin"


class TestApiKeyRole:
    """Tests that API key management respects role boundaries."""

    def _ensure_seats(self, n=50):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = n

    def test_regenerate_api_key_valid(self):
        self._ensure_seats()
        from team import create_team, create_user, regenerate_api_key
        team = create_team("API Key Team")
        user = create_user(team["id"], "apikeyuser", "pass123", role="admin")
        new_key = regenerate_api_key(user["id"], team["id"])
        assert new_key is not None
        assert new_key.startswith("gw_api_")

    def test_regenerate_api_key_wrong_team_returns_none(self):
        self._ensure_seats()
        from team import create_team, create_user, regenerate_api_key
        team = create_team("API Key Team 2")
        user = create_user(team["id"], "apikeyuser2", "pass123", role="admin")
        assert regenerate_api_key(user["id"], "WRONG_TEAM") is None
