"""
负载均衡模块 — 多上游 LLM 健康检查 + 负载均衡。
"""
import asyncio
import itertools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class UpstreamNode:
    """上游节点状态"""
    url: str
    healthy: bool = True
    last_health_check: float = 0.0
    active_connections: int = 0
    consecutive_failures: int = 0


class LoadBalancer:
    """负载均衡器 — 支持 round_robin / random / least_connections 策略"""

    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, urls: List[str], strategy: str = "round_robin") -> None:
        self._strategy = strategy
        self._nodes: List[UpstreamNode] = [UpstreamNode(url=url) for url in urls]
        self._round_robin_cycle = itertools.cycle(range(len(self._nodes)))
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval: float = 30.0
        self._lock = asyncio.Lock()

    # ---- Public API ----

    def get_upstream(self) -> Optional[str]:
        """
        根据策略返回下一个健康上游的 URL。
        如果没有健康节点，返回 None。
        """
        if not self._nodes:
            return None

        healthy_nodes = [n for n in self._nodes if n.healthy]
        if not healthy_nodes:
            logger.warning("[负载均衡] 所有上游节点均不健康")
            return None

        if self._strategy == "round_robin":
            return self._round_robin(healthy_nodes)
        elif self._strategy == "random":
            return self._random(healthy_nodes)
        elif self._strategy == "least_connections":
            return self._least_connections(healthy_nodes)
        else:
            return self._round_robin(healthy_nodes)

    def mark_success(self, url: str) -> None:
        """标记请求成功 — 重置连续失败计数，减少活跃连接数"""
        node = self._find_node(url)
        if node:
            node.consecutive_failures = 0
            node.active_connections = max(0, node.active_connections - 1)

    def mark_failure(self, url: str) -> None:
        """标记节点失败 — 增加失败计数，超阈值则标记不健康"""
        node = self._find_node(url)
        if node:
            node.consecutive_failures += 1
            node.active_connections = max(0, node.active_connections - 1)
            if node.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                node.healthy = False
                logger.warning(
                    "[负载均衡] 节点 %s 已标记为不健康 (连续 %d 次失败)",
                    url, node.consecutive_failures
                )

    def release(self, url: str) -> None:
        """释放连接 — 减少活跃连接计数"""
        node = self._find_node(url)
        if node:
            node.active_connections = max(0, node.active_connections - 1)

    # ---- Health Check ----

    async def start_health_check(self, interval: float = 30.0) -> None:
        """启动后台健康检查任务"""
        self._health_check_interval = interval
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("[负载均衡] 后台健康检查已启动 (间隔: %.1f 秒)", interval)

    async def stop_health_check(self) -> None:
        """停止后台健康检查任务"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("[负载均衡] 后台健康检查已停止")

    async def _health_check_loop(self) -> None:
        """健康检查主循环 — 定期检查所有不健康节点"""
        while True:
            await asyncio.sleep(self._health_check_interval)
            unhealthy_nodes = [n for n in self._nodes if not n.healthy]
            if not unhealthy_nodes:
                continue

            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                for node in unhealthy_nodes:
                    try:
                        response = await client.get(f"{node.url}/v1/models")
                        if response.status_code == 200:
                            node.healthy = True
                            node.consecutive_failures = 0
                            node.last_health_check = time.time()
                            logger.info(
                                "[负载均衡] 节点 %s 已恢复健康", node.url
                            )
                    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                        logger.debug(
                            "[负载均衡] 节点 %s 健康检查失败: %s", node.url, e
                        )

    # ---- Stats ----

    def get_stats(self) -> List[Dict[str, Any]]:
        """返回所有节点的健康统计"""
        return [
            {
                "url": n.url,
                "healthy": n.healthy,
                "active_connections": n.active_connections,
                "consecutive_failures": n.consecutive_failures,
                "last_health_check": n.last_health_check,
            }
            for n in self._nodes
        ]

    # ---- Internal ----

    def _find_node(self, url: str) -> Optional[UpstreamNode]:
        for n in self._nodes:
            if n.url == url:
                return n
        return None

    def _round_robin(self, healthy_nodes: List[UpstreamNode]) -> Optional[str]:
        healthy_urls = {n.url for n in healthy_nodes}
        max_attempts = max(len(self._nodes) * 2, 1)
        for _ in range(max_attempts):
            idx = next(self._round_robin_cycle)
            url = self._nodes[idx].url
            if url in healthy_urls:
                self._nodes[idx].active_connections += 1
                return url
        # 保底：直接从健康列表取第一个
        if healthy_nodes:
            selected = healthy_nodes[0]
            selected.active_connections += 1
            return selected.url
        return None

    def _random(self, healthy_nodes: List[UpstreamNode]) -> Optional[str]:
        if not healthy_nodes:
            return None
        selected = random.choice(healthy_nodes)
        selected.active_connections += 1
        return selected.url

    def _least_connections(self, healthy_nodes: List[UpstreamNode]) -> Optional[str]:
        if not healthy_nodes:
            return None
        selected = min(healthy_nodes, key=lambda n: n.active_connections)
        selected.active_connections += 1
        return selected.url
