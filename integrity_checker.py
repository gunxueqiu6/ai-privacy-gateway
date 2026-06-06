"""
运行时完整性检查器 — Python 包装层
加载 Rust 编译的 integrity_check.pyd/.so 模块，提供后台守护线程
"""
import hashlib
import logging
import os
import threading
import time
from typing import Callable, Dict, Optional

from config import config

logger = logging.getLogger(__name__)

# 尝试加载 Rust 编译模块
_INTEGRITY_CORE: Optional[object] = None
_LOAD_ERROR: Optional[str] = None

try:
    import integrity_check
    _INTEGRITY_CORE = integrity_check
    logger.info(f"[完整性检查] 加载 Rust 模块成功 v{integrity_check.__version__}")
except ImportError as e:
    _LOAD_ERROR = str(e)
    logger.warning(f"[完整性检查] Rust 模块未编译: {e}，跳过完整性校验")


class IntegrityChecker:
    """运行时完整性检查器"""

    CHECK_INTERVAL_SEC = 300  # 每 5 分钟检查一次

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_anomaly: Optional[Callable] = None
        self._on_heartbeat: Optional[Callable] = None
        self._last_result: Optional[Dict] = None
        self._anomaly_count: int = 0
        self._available = _INTEGRITY_CORE is not None

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def last_result(self) -> Optional[Dict]:
        return self._last_result

    def set_on_anomaly(self, callback: Callable[[str, str], None]):
        """设置异常回调 — (check_name, detail) -> None"""
        self._on_anomaly = callback

    def set_on_heartbeat(self, callback: Callable[[bool], None]):
        """设置心跳回调 — (ok: bool) -> None"""
        self._on_heartbeat = callback

    def _compute_expected_hashes(self, app_dir: str) -> Dict[str, str]:
        """扫描 app_dir 下的 .py 文件，计算 SHA-256 期望值"""
        expected: Dict[str, str] = {}
        if not os.path.isdir(app_dir):
            return expected

        for root, _dirs, files in os.walk(app_dir):
            for fname in files:
                if fname.endswith(".py") or fname.endswith(".pyd") or fname.endswith(".so"):
                    full = os.path.join(root, fname)
                    try:
                        with open(full, "rb") as fh:
                            h = hashlib.sha256(fh.read()).hexdigest()
                        rel = os.path.relpath(full, app_dir).replace("\\", "/")
                        expected[rel] = h
                    except OSError:
                        continue
        return expected

    def _run_check(self):
        """执行一次完整性检查"""
        if not self._available:
            return

        app_dir = os.path.dirname(os.path.abspath(__file__))
        expected = self._compute_expected_hashes(app_dir)

        try:
            result = _INTEGRITY_CORE.run_integrity_check(
                app_dir,
                expected if expected else None,
                self._on_anomaly,
                self._on_heartbeat,
            )
            self._last_result = result

            if not result.get("passed", True):
                self._anomaly_count += 1
                logger.warning(
                    f"[完整性检查] 第 {self._anomaly_count} 次异常: "
                    f"{result.get('anomalies', [])}"
                )
                self._on_integrity_failure(result)
            else:
                if self._anomaly_count > 0:
                    logger.info(f"[完整性检查] 恢复正常")
                self._anomaly_count = 0

        except Exception as e:
            logger.error(f"[完整性检查] 执行失败: {e}")

    def _on_integrity_failure(self, result: Dict):
        """完整性失败时触发衰减"""
        try:
            from decay_manager import get_decay_manager
            dm = get_decay_manager()
            dm.update()
            current = dm.current_level
            logger.warning(
                f"[完整性检查] 触发衰减，当前等级: {current.name} "
                f"({current.value})"
            )
        except Exception as exc:
            logger.debug(f"[完整性检查] 衰减管理器不可用: {exc}")

    def _loop(self):
        """后台循环"""
        logger.info("[完整性检查] 后台守护线程启动")
        while not self._stop_event.wait(timeout=self.CHECK_INTERVAL_SEC):
            self._run_check()
        logger.info("[完整性检查] 后台守护线程退出")

    def start(self):
        """启动后台检查线程"""
        if not self._available:
            logger.warning(f"[完整性检查] 跳过启动 — Rust 模块不可用: {_LOAD_ERROR}")
            return

        if self._thread and self._thread.is_alive():
            logger.warning("[完整性检查] 已在运行")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="integrity-checker",
            daemon=True,
        )
        self._thread.start()
        logger.info("[完整性检查] 已启动")

    def stop(self, timeout: float = 5.0):
        """停止后台检查线程"""
        if not self._thread or not self._thread.is_alive():
            return

        self._stop_event.set()
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning("[完整性检查] 线程未在超时内退出")
        else:
            logger.info("[完整性检查] 已停止")

    def check_now(self) -> Optional[Dict]:
        """立即执行一次检查（同步）"""
        self._run_check()
        return self._last_result


# 全局实例
_integrity_checker: Optional[IntegrityChecker] = None


def get_integrity_checker() -> IntegrityChecker:
    global _integrity_checker
    if _integrity_checker is None:
        _integrity_checker = IntegrityChecker()
    return _integrity_checker


def start_integrity_checker(app_dir: Optional[str] = None):
    """启动完整性检查守护线程"""
    checker = get_integrity_checker()

    # 连接衰减管理器
    def on_anomaly(name: str, detail: str):
        logger.warning(f"[完整性检查] 检测到异常: {name} — {detail}")
        try:
            from decay_manager import get_decay_manager
            dm = get_decay_manager()
            dm.update()
        except Exception:
            pass

    # 连接 License 心跳
    def on_heartbeat(ok: bool):
        if not ok:
            logger.warning("[完整性检查] 心跳失败 — 完整性异常")

    checker.set_on_anomaly(on_anomaly)
    checker.set_on_heartbeat(on_heartbeat)
    checker.start()


def stop_integrity_checker():
    """停止完整性检查"""
    checker = get_integrity_checker()
    checker.stop()
