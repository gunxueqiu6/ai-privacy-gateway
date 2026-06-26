"""
审计事件广播模块 — 基于 asyncio.Queue 的 pub/sub
"""

import asyncio
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AuditBus:
    """审计事件广播总线"""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def publish(self, event: dict) -> None:
        event["_ts"] = time.time()
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


# 全局总线
audit_bus = AuditBus()
