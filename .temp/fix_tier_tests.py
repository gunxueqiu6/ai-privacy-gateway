path = r"G:\projects\ai数据隐私隔离\tests\test_license.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Update the tier comparison tests
old_test = """    def test_tier_ordering(self):
        \"\"\"Tier ordering should be lite < pro < enterprise.\"\"\"
        from main import Tier

        assert Tier.LITE < Tier.PRO
        assert Tier.PRO < Tier.ENTERPRISE
        assert Tier.LITE < Tier.ENTERPRISE
        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO
        assert Tier.PRO >= Tier.PRO
        assert Tier.LITE >= Tier.LITE"""

new_test = """    def test_tier_ordering(self):
        \"\"\"Tier values should be ordered lite(0) < pro(1) < enterprise(2).\"\"\"
        from main import Tier

        assert Tier.LITE == 0
        assert Tier.PRO == 1
        assert Tier.ENTERPRISE == 2
        assert Tier.LITE < Tier.PRO
        assert Tier.PRO < Tier.ENTERPRISE
        assert Tier.LITE < Tier.ENTERPRISE
        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO
        assert Tier.PRO >= Tier.PRO
        assert Tier.LITE >= Tier.LITE

    def test_tier_label(self):
        \"\"\"Tier labels should return the correct string.\"\"\"
        from main import Tier

        assert Tier.LITE.label == "lite"
        assert Tier.PRO.label == "pro"
        assert Tier.ENTERPRISE.label == "enterprise\""""

content = content.replace(old_test, new_test)

old_gte = """    def test_tier_gte_helper(self):
        \"\"\"The >= operator should work correctly.\"\"\"
        from main import Tier

        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO
        assert not (Tier.LITE >= Tier.PRO)
        assert not (Tier.PRO >= Tier.ENTERPRISE)"""

new_gte = """    def test_tier_gte_helper(self):
        \"\"\"The >= operator should work correctly.\"\"\"
        from main import Tier

        assert Tier.PRO >= Tier.LITE
        assert Tier.ENTERPRISE >= Tier.PRO
        assert not (Tier.LITE >= Tier.PRO)
        assert not (Tier.PRO >= Tier.ENTERPRISE)"""

# No change needed here, gte_helper looks fine

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated tier comparison tests")
