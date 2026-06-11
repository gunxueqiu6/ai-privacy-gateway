"""Pytest 配置文件"""
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试环境变量
os.environ["TARGET_LLM"] = "https://api.openai.com"
os.environ["LISTEN_PORT"] = "9999"
os.environ["ADMIN_PASSWORD"] = ""
os.environ["ADMIN_PASSWORD_HASH"] = (
    "$2b$12$IZYZuT8o8BPjWkz8NkBC8O12k1InUhkwFcF9M.OcMZ68h70FGP.4a"
)
os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"

# 如果 config 模块已经被导入过，直接设置类属性确保一致性
if "config" in sys.modules:
    from config import Config
    Config.ADMIN_PASSWORD = ""
    Config.ADMIN_PASSWORD_HASH = os.environ["ADMIN_PASSWORD_HASH"]
    Config.JWT_SECRET = "test-jwt-secret-key-for-testing-only"
