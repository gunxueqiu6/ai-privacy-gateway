path = r"G:\projects\ai数据隐私隔离\tests\test_license.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add module-level teardown
insert_pos = content.find("class TestLicenseActivation")
cleanup_block = """
def teardown_module():
    \"\"\"Reset config after license tests.\"\"\"
    from config import config as cfg
    cfg.tier = "lite"
    cfg.license_seats = 1
    cfg.license_team_id = None
    cfg.license_expires_at = None
    cfg.LICENSE_KEY = ""
    cfg.LICENSE_FILE = "./license.key"


"""

content = content[:insert_pos] + cleanup_block + content[insert_pos]

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added teardown to test_license.py")
