"""Pytest 配置文件"""
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ.setdefault("TARGET_LLM", "https://api.openai.com")
os.environ.setdefault("LISTEN_PORT", "9999")