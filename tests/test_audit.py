"""audit.py — AuditBus pub/sub 测试"""
import asyncio
import pytest
from audit import AuditBus


class TestAuditBus:
    def test_subscribe_returns_queue(self):
        bus = AuditBus()
        q = bus.subscribe()
        assert isinstance(q, asyncio.Queue)
        assert q.maxsize == 256

    def test_multiple_subscribers(self):
        bus = AuditBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        assert q1 is not q2

    def test_unsubscribe_removes_subscriber(self):
        bus = AuditBus()
        q = bus.subscribe()
        bus.unsubscribe(q)
        assert len(bus._subscribers) == 0

    def test_unsubscribe_nonexistent_does_not_raise(self):
        bus = AuditBus()
        q = asyncio.Queue()
        bus.unsubscribe(q)  # should not raise

    def test_publish_adds_timestamp(self):
        bus = AuditBus()
        q = bus.subscribe()
        bus.publish({"event": "test"})
        event = q.get_nowait()
        assert "_ts" in event
        assert event["event"] == "test"

    def test_publish_to_all_subscribers(self):
        bus = AuditBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        bus.publish({"msg": "broadcast"})
        assert q1.qsize() == 1
        assert q2.qsize() == 1

    def test_publish_queue_full_does_not_block(self):
        bus = AuditBus()
        q = bus.subscribe()
        for _ in range(256):
            q.put_nowait({"_ts": 0})
        bus.publish({"new": "event"})  # should not raise
        assert q.full()

    def test_repeated_unsubscribe_safe(self):
        bus = AuditBus()
        q1 = bus.subscribe()
        bus.unsubscribe(q1)
        bus.unsubscribe(q1)  # no-op, should not raise
        assert len(bus._subscribers) == 0
