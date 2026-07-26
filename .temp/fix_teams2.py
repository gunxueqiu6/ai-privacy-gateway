path = r"G:\projects\ai数据隐私隔离\tests\test_teams.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add setup_class to TestUserCRUD, TestSessionManagement, TestSeatLimit
old_crud = "class TestUserCRUD:"
new_crud = """class TestUserCRUD:

    @classmethod
    def setup_class(cls):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = 50"""

content = content.replace(old_crud, new_crud)

old_session = "class TestSessionManagement:"
new_session = """class TestSessionManagement:

    @classmethod
    def setup_class(cls):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = 50"""

content = content.replace(old_session, new_session)

old_seat = "class TestSeatLimit:"
new_seat = """class TestSeatLimit:

    @classmethod
    def setup_class(cls):
        from config import config as cfg
        cfg.tier = "pro"
        cfg.license_seats = 50"""

content = content.replace(old_seat, new_seat)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added setup_class to all team test classes")
