"""
结构化日志配置模块 — JSON 格式日志输出，支持通过环境变量切换为文本格式。
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式化器 — 每行输出一个 JSON 对象。"""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging() -> None:
    """配置根日志记录器。

    环境变量:
        LOG_FORMAT: 日志格式，json 或 text（默认: json）
        LOG_LEVEL:  日志级别（默认: INFO）
    """
    log_format = os.environ.get("LOG_FORMAT", "json").lower()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # 移除已有处理器
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "text":
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    else:
        formatter = JsonFormatter()
    handler.setFormatter(formatter)
    root.addHandler(handler)
