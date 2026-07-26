path = r"G:\projects\ai数据隐私隔离\tests\test_teams.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add a module-level fixture to reset config state
# Insert after imports, before TestTeamCRUD
insert_pos = content.find("class TestTeamCRUD")
setup_block = """
def setup_module():
    \"\"\"Ensure config has sufficient seats before any team tests run.\"\"\"
    from config import config as cfg
    cfg.tier = "pro"
    cfg.license_seats = 50
    cfg.license_team_id = "test_team_module"


def teardown_module():
    \"\"\"Reset config after team tests.\"\"\"
    from config import config as cfg
    cfg.tier = "lite"
    cfg.license_seats = 1
    cfg.license_team_id = None


"""

content = content[:insert_pos] + setup_block + content[insert_pos:]

# Fix the SeatLimit test to set its own limit
old_seat = """class TestSeatLimit:
    \"\"\"Tests for license seat limit enforcement.\"\"\"

    def test_seat_limit_enforced(self):
        from team import create_team, create_user, TeamError
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = 3
        team = create_team("Limited Team")
        create_user(team["id"], "u1", "p1")
        create_user(team["id"], "u2", "p2")
        create_user(team["id"], "u3", "p3")
        with pytest.raises(TeamError, match="seat limit"):
            create_user(team["id"], "u4", "p4")"""

new_seat = """class TestSeatLimit:
    \"\"\"Tests for license seat limit enforcement.\"\"\"

    def test_seat_limit_enforced(self):
        from team import create_team, create_user, TeamError
        from config import config as cfg
        cfg.license_seats = 3
        team = create_team("Limited Team")
        create_user(team["id"], "u1", "p1")
        create_user(team["id"], "u2", "p2")
        create_user(team["id"], "u3", "p3")
        with pytest.raises(TeamError, match="seat limit"):
            create_user(team["id"], "u4", "p4")"""

content = content.replace(old_seat, new_seat)

# Also fix the team fixture to not re-set seats each time (module-level now handles it)
old_fixture = """    @pytest.fixture
    def team(self):
        from team import create_team
        from config import config as cfg
        # Ensure seat limit is high enough
        cfg.tier = "pro"
        cfg.license_seats = 20
        return create_team("Test Team for Users")"""

new_fixture = """    @pytest.fixture
    def team(self):
        from team import create_team
        return create_team("Test Team for Users")"""

content = content.replace(old_fixture, new_fixture)

# Fix SessionManagement fixture
old_session_fixture = """    @pytest.fixture
    def user_data(self):
        from team import create_team, create_user
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = 20
        team = create_team("Session Test Team")
        user = create_user(team["id"], "sessionuser", "password")
        return user"""

new_session_fixture = """    @pytest.fixture
    def user_data(self):
        from team import create_team, create_user
        team = create_team("Session Test Team")
        user = create_user(team["id"], "sessionuser", "password")
        return user"""

content = content.replace(old_session_fixture, new_session_fixture)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed test_teams.py with module-level config setup")
