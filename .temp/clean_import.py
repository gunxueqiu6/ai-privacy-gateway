path = r"G:\projects\ai数据隐私隔离\tests\test_payment.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove unused AsyncMock import
content = content.replace("from unittest.mock import AsyncMock, patch\n", "from unittest.mock import patch\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Cleaned up imports")
