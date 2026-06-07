"""
审计日志模块 - Enterprise 版
完整审计链：谁 + 何时 + 触发了什么 + 原始内容快照
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AuditLog:
    """审计日志数据结构"""
    log_id: str
    timestamp: str
    session_id: str
    user_id: Optional[str]
    action: str  # mask / unmask / request / response
    data_types: List[str]
    count: int
    request_preview: str  # 前100字符
    response_preview: str  # 前100字符
    ip_address: Optional[str]
    client_info: Optional[str]
    duration_ms: int
    status: str  # success / error


class AuditLogger:
    """审计日志记录器"""

    MAX_PREVIEW_LENGTH = 100

    def __init__(self):
        self.logs_buffer: List[AuditLog] = []
        self.flush_interval = 60  # 60秒批量写入

    def _generate_log_id(self) -> str:
        """生成日志ID"""
        return f"audit_{int(time.time() * 1000)}_{hash(str(time.time())) % 10000}"

    def _truncate_preview(self, content: str) -> str:
        """截取预览"""
        if len(content) > self.MAX_PREVIEW_LENGTH:
            return content[:self.MAX_PREVIEW_LENGTH] + "..."
        return content

    def log_mask_action(
        self,
        session_id: str,
        original_content: str,
        masked_content: str,
        mappings: Dict[str, str],
        stats: Dict[str, int],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        client_info: Optional[str] = None
    ):
        """记录脱敏操作"""
        log = AuditLog(
            log_id=self._generate_log_id(),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            action="mask",
            data_types=list(mappings.keys()),
            count=sum(stats.values()),
            request_preview=self._truncate_preview(original_content),
            response_preview=self._truncate_preview(masked_content),
            ip_address=ip_address,
            client_info=client_info,
            duration_ms=0,
            status="success"
        )

        self._save_log(log)
        logger.info(f"[审计] 脱敏操作 {log.log_id}: {log.count} 条")

    def log_request_action(
        self,
        session_id: str,
        request_body: Dict,
        response_status: int,
        duration_ms: int,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """记录请求转发"""
        log = AuditLog(
            log_id=self._generate_log_id(),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            action="request",
            data_types=[],
            count=0,
            request_preview=self._truncate_preview(json.dumps(request_body)),
            response_preview=f"status: {response_status}",
            ip_address=ip_address,
            client_info=None,
            duration_ms=duration_ms,
            status="success" if response_status == 200 else "error"
        )

        self._save_log(log)

    def log_unmask_action(
        self,
        session_id: str,
        masked_content: str,
        unmasked_content: str,
        mappings: Dict[str, str],
        user_id: Optional[str] = None
    ):
        """记录还原操作"""
        log = AuditLog(
            log_id=self._generate_log_id(),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            action="unmask",
            data_types=list(mappings.keys()),
            count=len(mappings),
            request_preview=self._truncate_preview(masked_content),
            response_preview=self._truncate_preview(unmasked_content),
            ip_address=None,
            client_info=None,
            duration_ms=0,
            status="success"
        )

        self._save_log(log)

    def log_error(
        self,
        session_id: str,
        error_message: str,
        error_type: str,
        user_id: Optional[str] = None
    ):
        """记录错误"""
        log = AuditLog(
            log_id=self._generate_log_id(),
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            action="error",
            data_types=[error_type],
            count=0,
            request_preview=error_message,
            response_preview="",
            ip_address=None,
            client_info=None,
            duration_ms=0,
            status="error"
        )

        self._save_log(log)
        logger.error(f"[审计] 错误 {log.log_id}: {error_message}")

    def _save_log(self, log: AuditLog):
        """保存日志"""
        try:
            from redis_storage import get_storage
            storage = get_storage()
            storage.save_audit_log(asdict(log))
        except:
            # 回退到本地存储
            self.logs_buffer.append(log)
            if len(self.logs_buffer) >= 100:
                self._flush_buffer()

    def _flush_buffer(self):
        """刷新缓冲区"""
        if not self.logs_buffer:
            return

        # 写入本地文件
        log_file = f"audit_logs_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(log_file, 'a') as f:
            for log in self.logs_buffer:
                f.write(json.dumps(asdict(log)) + '\n')

        self.logs_buffer.clear()
        logger.info(f"[审计] 刷新 {len(self.logs_buffer)} 条日志到文件")

    def get_logs(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict]:
        """获取日志"""
        try:
            from redis_storage import get_storage
            storage = get_storage()
            logs = storage.get_audit_logs(limit)

            if user_id:
                logs = [l for l in logs if l.get("user_id") == user_id]

            return logs
        except:
            return [asdict(l) for l in self.logs_buffer[-limit:]]

    def search_logs(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """搜索日志"""
        logs = self.get_logs(1000)

        if start_time:
            logs = [l for l in logs if l["timestamp"] >= start_time]
        if end_time:
            logs = [l for l in logs if l["timestamp"] <= end_time]
        if action:
            logs = [l for l in logs if l["action"] == action]
        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]

        return logs


# 全局审计日志实例
audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志实例"""
    global audit_logger
    if audit_logger is None:
        audit_logger = AuditLogger()
    return audit_logger


# 新增的统计查询方法
def get_today_mask_count() -> int:
    """获取今日脱敏操作总数量"""
    try:
        from datetime import datetime, date
        logger = get_audit_logger()
        logs = logger.get_logs(limit=10000)
        today = date.today().isoformat()
        count = 0
        for log in logs:
            if log.get("timestamp", "").startswith(today) and log.get("action") == "mask":
                count += log.get("count", 0)
        return count
    except Exception:
        return 0


def get_today_entity_count() -> int:
    """获取今日实体处理总数量"""
    try:
        from datetime import datetime, date
        logger = get_audit_logger()
        logs = logger.get_logs(limit=10000)
        today = date.today().isoformat()
        count = 0
        for log in logs:
            if log.get("timestamp", "").startswith(today):
                count += log.get("count", 0)
        return count
    except Exception:
        return 0


def get_today_error_count() -> int:
    """获取今日错误数量"""
    try:
        from datetime import datetime, date
        logger = get_audit_logger()
        logs = logger.get_logs(limit=10000)
        today = date.today().isoformat()
        count = 0
        for log in logs:
            if log.get("timestamp", "").startswith(today) and log.get("status") == "error":
                count += 1
        return count
    except Exception:
        return 0