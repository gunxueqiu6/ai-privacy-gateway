path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_tier = """class Tier(str, Enum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def __ge__(self, other: "Tier") -> bool:
        order = {"lite": 0, "pro": 1, "enterprise": 2}
        return order[self.value] >= order[other.value]"""

new_tier = """class Tier(str, Enum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def order(self) -> int:
        _order = {"lite": 0, "pro": 1, "enterprise": 2}
        return _order[self.value]

    def __ge__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() >= other.order()
        return NotImplemented

    def __lt__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() < other.order()
        return NotImplemented

    def __le__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() <= other.order()
        return NotImplemented

    def __gt__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() > other.order()
        return NotImplemented"""

content = content.replace(old_tier, new_tier)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed Tier with all comparison operators")
