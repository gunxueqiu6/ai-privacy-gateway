"""
网关核心模块 - 上行脱敏 + 下行还原 + HTTP 代理转发
"""
import asyncio
import copy
import json
import logging
import os
import random
import re
import time
import uuid
from typing import Dict, Any, Tuple, AsyncGenerator, Optional, Set, Union

import httpx

from config import config
from load_balancer import LoadBalancer
from mask_engine import get_mask_engine
from audit import audit_bus
from database import db
from metrics import pii_detected_total, pii_masked_total, gateway_errors_total


logger = logging.getLogger(__name__)


class GatewayCore:
    """网关核心处理类"""

    def __init__(self) -> None:
        self.mask_engine = get_mask_engine()
        self.target_url = config.TARGET_LLM

        # 初始化负载均衡器
        if config.UPSTREAM_LLM_URLS:
            upstream_urls = [u.strip() for u in config.UPSTREAM_LLM_URLS.split(",") if u.strip()]
        else:
            upstream_urls = [config.TARGET_LLM]
        self.load_balancer = LoadBalancer(upstream_urls, config.UPSTREAM_LB_STRATEGY)
        if len(upstream_urls) > 1:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.load_balancer.start_health_check(config.UPSTREAM_HEALTH_CHECK_INTERVAL)
                )
            except RuntimeError:
                pass  # Health check will start on first request/reload_config
            logger.info(
                "多上游 LLM 已启用: %d 个节点, 策略: %s, 健康检查间隔: %ds",
                len(upstream_urls), config.UPSTREAM_LB_STRATEGY, config.UPSTREAM_HEALTH_CHECK_INTERVAL
            )

        # 无状态模式日志
        if config.STATELESS_MODE:
            logger.info("无状态模式已启用 — 映射数据不落盘，仅存内存")
        logger.info("映射 TTL 配置: %d 秒 (%.1f 小时)", config.MAPPING_TTL, config.MAPPING_TTL / 3600)

        # 共享连接池客户端
        pool_limits = httpx.Limits(
            max_connections=int(os.environ.get("UPSTREAM_MAX_CONNECTIONS", "100")),
            max_keepalive_connections=int(os.environ.get("UPSTREAM_MAX_KEEPALIVE", "20")),
        )
        client_timeout = httpx.Timeout(float(os.environ.get("UPSTREAM_TIMEOUT", "120.0")))
        self._client = httpx.AsyncClient(timeout=client_timeout, limits=pool_limits)

        # 重试配置
        self._max_retries = int(os.environ.get("UPSTREAM_MAX_RETRIES", "0"))
        self._retry_delay = float(os.environ.get("UPSTREAM_RETRY_DELAY", "1.0"))

        # 并发控制与优雅关闭
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        self._active_requests = 0
        self._shutdown_flag = False

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        """判断是否可重试的瞬态错误"""
        if isinstance(error, httpx.TimeoutException):
            return True
        if isinstance(error, httpx.ConnectError):
            return True
        if isinstance(error, httpx.RemoteProtocolError):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            return 500 <= error.response.status_code < 600
        return False

    @staticmethod
    def _extract_texts_from_content(content: Union[str, list]) -> list:
        """
        从消息 content 中提取文本片段。
        支持 OpenAI 格式（字符串）和 Anthropic 格式（content block 数组）。
        """
        if isinstance(content, str):
            return [content]
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return texts

    @staticmethod
    def _rebuild_content(original_content: Union[str, list], masked_texts: list) -> Union[str, list]:
        """
        将脱敏后的文本重新构建为原始 content 格式。
        """
        if isinstance(original_content, str):
            return masked_texts[0] if masked_texts else original_content
        rebuilt = copy.deepcopy(original_content)
        text_idx = 0
        for block in rebuilt:
            if isinstance(block, dict) and block.get("type") == "text":
                if text_idx < len(masked_texts):
                    block["text"] = masked_texts[text_idx]
                    text_idx += 1
        return rebuilt

    @property
    def active_requests(self) -> int:
        """当前正在处理的活跃请求数"""
        return self._active_requests

    @property
    def shutdown_flag(self) -> bool:
        """是否正在关闭中"""
        return self._shutdown_flag

    @shutdown_flag.setter
    def shutdown_flag(self, value: bool) -> None:
        self._shutdown_flag = value

    def generate_session_id(self) -> str:
        """生成会话ID"""
        return f"sess_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    def _resolve_upstream(self, body: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        根据请求 body 中的 model 字段解析上游 URL。
        优先级: UPSTREAM_MODEL_MAP 精确匹配 > 通配符 * > 负载均衡器
        """
        if body:
            model = body.get("model", "")
            if model and hasattr(config, 'UPSTREAM_MODEL_MAP'):
                model_map = config.UPSTREAM_MODEL_MAP
                if model in model_map:
                    logger.debug("模型 %s 映射到指定上游: %s", model, model_map[model])
                    return model_map[model]
                if "*" in model_map:
                    logger.debug("模型 %s 使用通配符上游: %s", model, model_map["*"])
                    return model_map["*"]
        return self.load_balancer.get_upstream()

    def mask_request(self, body: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, int], str, Set[str]]:
        """
        上行脱敏处理。
        当 DRY_RUN_MODE 启用时，仅检测并统计 PII，不实际脱敏，不写入 Vault。
        返回: (脱敏后的body, mappings, stats, session_id, used_placeholders)
        """
        session_id = self.generate_session_id()
        dry_run = config.DRY_RUN_MODE

        all_mappings = {}
        total_stats = {
            "phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0,
            "person": 0, "location": 0, "org": 0, "organization": 0,
            "plate": 0, "coordinates": 0, "ip": 0, "url": 0, "date": 0, "amount": 0, "postcode": 0,
            "passport": 0, "ssn": 0, "credit_code": 0, "mac": 0
        }

        messages = body.get("messages", [])
        masked_body = copy.deepcopy(body)
        masked_messages = masked_body["messages"]
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if not content:
                continue

            texts = self._extract_texts_from_content(content)
            if not texts:
                continue

            masked_texts = []
            for t in texts:
                if dry_run:
                    # Dry-run: 检测但不脱敏，也不生成 mappings
                    masked_t, _, block_stats = self.mask_engine.mask(t)
                    # 丢弃 mappings，统计仍记录
                    masked_texts.append(t)  # 保留原始文本
                else:
                    masked_t, block_mappings, block_stats = self.mask_engine.mask(t)
                    masked_texts.append(masked_t)
                    all_mappings.update(block_mappings)

                for k, v in block_stats.items():
                    if k in total_stats:
                        total_stats[k] += v

            masked_messages[i]["content"] = self._rebuild_content(content, masked_texts)

        total_count = sum(total_stats.values())
        if dry_run:
            logger.info("[Dry-Run] 会话 %s，检测到敏感信息 %d 条（未脱敏）", session_id, total_count)
        else:
            logger.info("[网关拦截] 会话 %s，拦截敏感信息 %d 条", session_id, total_count)

        # 更新 Prometheus PII 指标（detected 总是记录；masked 仅在非 dry-run 时记录）
        for entity_type, count in total_stats.items():
            if count > 0:
                pii_detected_total.labels(entity_type=entity_type).inc(count)
                if not dry_run:
                    pii_masked_total.labels(entity_type=entity_type).inc(count)

        # 记录审计日志
        db.log_audit(session_id, "mask_request", {
            "entity_count": total_count,
            "stats": total_stats,
            "dry_run": dry_run,
        })
        audit_bus.publish({
            "event": "mask",
            "session_id": session_id,
            "entity_count": total_count,
            "stats": total_stats,
            "dry_run": dry_run,
        })

        # 提取实际出现在脱敏文本中的占位符
        pii_pattern = re.compile(r'\[PII_\w+_[A-Z]+\]')
        used_placeholders: Set[str] = set()
        for msg in masked_messages:
            content = msg.get("content", "")
            if content:
                texts = self._extract_texts_from_content(content)
                for t in texts:
                    used_placeholders.update(pii_pattern.findall(t))

        return masked_body, all_mappings, total_stats, session_id, used_placeholders

    def unmask_response(self, text: str, mappings: Dict[str, str], session_id: Optional[str] = None, used_placeholders: Optional[Set[str]] = None) -> str:
        """
        下行还原处理
        """
        if not mappings:
            return text

        # 仅还原实际出现在请求脱敏输出中的占位符，防注入
        if used_placeholders is not None:
            mappings = {k: v for k, v in mappings.items() if k in used_placeholders}

        result = self.mask_engine.unmask(text, mappings)
        return result

    async def proxy_request(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str],
        mappings: Dict[str, str],
        session_id: Optional[str] = None
    ) -> Tuple[int, Union[bytes, Dict[str, Any]], Dict[str, str]]:
        """
        代理转发请求到目标 LLM（含重试 + 负载均衡 + 并发限制 + 优雅关闭）
        返回: (status_code, response_body, response_headers)
        """
        if self._shutdown_flag:
            return 503, json.dumps({"error": "Server shutting down, retry later"}).encode(), {}

        async with self._semaphore:
            self._active_requests += 1
            try:
                start_time = time.time()
                last_error: Optional[Exception] = None

                for attempt in range(self._max_retries + 1):
                    upstream_url = self._resolve_upstream(body)
                    if upstream_url is None:
                        gateway_errors_total.labels(error_type="no_healthy_upstream").inc()
                        return 502, json.dumps({"error": "No healthy upstream available"}).encode(), {}

                    target_url = f"{upstream_url}/v1/chat/completions"

                    if attempt > 0:
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        jitter = random.uniform(0, delay * 0.1)
                        await asyncio.sleep(delay + jitter)
                        logger.info(f"[重试] 第 {attempt}/{self._max_retries} 次重试 {session_id}")

                    try:
                        response = await self._client.post(
                            target_url,
                            json=body,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": headers.get("authorization", "")
                            }
                        )

                        # 5xx 服务端错误也可重试
                        if response.status_code >= 500 and attempt < self._max_retries:
                            self.load_balancer.mark_failure(upstream_url)
                            last_error = httpx.HTTPStatusError(
                                f"Upstream {response.status_code}",
                                request=response.request,
                                response=response
                            )
                            continue

                        self.load_balancer.mark_success(upstream_url)
                        latency_ms = int((time.time() - start_time) * 1000)
                        db.log_audit(session_id, "proxy_request", {
                            "status_code": response.status_code,
                            "latency_ms": latency_ms,
                            "attempts": attempt + 1,
                        })
                        audit_bus.publish({
                            "event": "proxy",
                            "session_id": session_id,
                            "status_code": response.status_code,
                            "latency_ms": latency_ms,
                            "attempts": attempt + 1,
                        })
                        return response.status_code, response.content, dict(response.headers)

                    except httpx.TimeoutException as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="timeout").inc()
                        logger.warning(f"[网关] 超时 (attempt {attempt + 1}): {e}")
                    except httpx.ConnectError as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="connect_error").inc()
                        logger.warning(f"[网关] 连接失败 (attempt {attempt + 1}): {e}")
                    except httpx.RemoteProtocolError as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="protocol_error").inc()
                        logger.warning(f"[网关] 协议错误 (attempt {attempt + 1}): {e}")

                # 所有重试耗尽
                error_msg = "Gateway Timeout" if isinstance(last_error, httpx.TimeoutException) else "Upstream service unavailable"
                status_code = 504 if isinstance(last_error, httpx.TimeoutException) else 502
                logger.error(f"[网关错误] 重试耗尽: {last_error}")
                db.log_audit(session_id, "proxy_error", {"error": str(last_error), "attempts": self._max_retries + 1})
                audit_bus.publish({
                    "event": "proxy_error",
                    "session_id": session_id,
                    "error": str(last_error),
                    "attempts": self._max_retries + 1,
                })
                return status_code, json.dumps({"error": error_msg}).encode(), {}
            finally:
                self._active_requests -= 1

    async def proxy_stream_request(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str],
        mappings: Dict[str, str],
        used_placeholders: Optional[Set[str]] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        流式代理转发 — 产出 SSE dict，由 EventSourceResponse 编码。
        """
        if self._shutdown_flag:
            yield {"data": json.dumps({"error": "Server shutting down, retry later"})}
            return

        async with self._semaphore:
            self._active_requests += 1
            try:
                upstream_url = self._resolve_upstream(body)
                if upstream_url is None:
                    logger.error("[流式错误] 无健康上游可用")
                    yield {"data": json.dumps({"error": "No healthy upstream available"})}
                    return

                target_url = f"{upstream_url}/v1/chat/completions"
                audit_bus.publish({
                    "event": "proxy_stream_start",
                })

                try:
                    async with self._client.stream(
                        "POST",
                        target_url,
                        json=body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": headers.get("authorization", "")
                        }
                    ) as response:

                        if response.status_code >= 500:
                            self.load_balancer.mark_failure(upstream_url)
                            error_body = await response.aread()
                            yield {"data": error_body.decode() if isinstance(error_body, bytes) else error_body}
                            return

                        self.load_balancer.mark_success(upstream_url)

                        async for line in response.aiter_lines():
                            if not line:
                                continue

                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    yield {"data": "[DONE]"}
                                    break

                                unmasked_data = self.unmask_response(data, mappings, used_placeholders=used_placeholders)
                                yield {"data": unmasked_data}
                            else:
                                yield {"data": line}

                except httpx.TimeoutException:
                    self.load_balancer.mark_failure(upstream_url)
                    gateway_errors_total.labels(error_type="stream_timeout").inc()
                    logger.error(f"[流式错误] 请求超时")
                    yield {"data": json.dumps({"error": "Gateway Timeout"})}
                except httpx.RequestError as e:
                    self.load_balancer.mark_failure(upstream_url)
                    gateway_errors_total.labels(error_type="stream_request_error").inc()
                    logger.error(f"[流式错误] 请求失败: {e}")
                    yield {"data": json.dumps({"error": "Upstream service unavailable"})}
            finally:
                self._active_requests -= 1

    async def proxy_generic_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        通用代理转发（非 chat/completions 路由，含重试 + 负载均衡 + 并发限制 + 优雅关闭）
        """
        if self._shutdown_flag:
            return 503, b'{"error": "Server shutting down, retry later"}', {}

        async with self._semaphore:
            self._active_requests += 1
            try:
                # 尝试解析 JSON body 用于模型路由
                body_dict: Optional[Dict[str, Any]] = None
                if body and method in ("POST", "PUT", "PATCH"):
                    try:
                        body_dict = json.loads(body)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass

                last_error: Optional[Exception] = None

                for attempt in range(self._max_retries + 1):
                    upstream_url = self._resolve_upstream(body_dict)
                    if upstream_url is None:
                        return 502, b'{"error": "No healthy upstream available"}', {}

                    target_url = f"{upstream_url}{path}"

                    if attempt > 0:
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        jitter = random.uniform(0, delay * 0.1)
                        await asyncio.sleep(delay + jitter)

                    try:
                        response = await self._client.request(
                            method=method,
                            url=target_url,
                            headers=headers,
                            content=body
                        )

                        if response.status_code >= 500 and attempt < self._max_retries:
                            self.load_balancer.mark_failure(upstream_url)
                            last_error = httpx.HTTPStatusError(
                                f"Upstream {response.status_code}",
                                request=response.request,
                                response=response
                            )
                            continue

                        self.load_balancer.mark_success(upstream_url)
                        return response.status_code, response.content, dict(response.headers)

                    except httpx.TimeoutException as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="generic_timeout").inc()
                    except httpx.ConnectError as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="generic_connect_error").inc()
                    except httpx.RemoteProtocolError as e:
                        self.load_balancer.mark_failure(upstream_url)
                        last_error = e
                        gateway_errors_total.labels(error_type="generic_protocol_error").inc()

                logger.error(f"[代理错误] 重试耗尽: {last_error}")
                return 502, b'{"error": "Upstream service unavailable"}', {}
            finally:
                self._active_requests -= 1


    # ---- Hot-Reload ----

    async def reload_config(self) -> None:
        """Hot-reload configuration without restarting the server."""
        self.target_url = config.TARGET_LLM

        # Rebuild upstream list
        if config.UPSTREAM_LLM_URLS:
            upstream_urls = [u.strip() for u in config.UPSTREAM_LLM_URLS.split(",") if u.strip()]
        else:
            upstream_urls = [config.TARGET_LLM]

        # Stop old health check
        asyncio.get_event_loop().create_task(self.load_balancer.stop_health_check())

        # Recreate load balancer with new settings
        self.load_balancer = LoadBalancer(upstream_urls, config.UPSTREAM_LB_STRATEGY)
        if len(upstream_urls) > 1:
            asyncio.get_event_loop().create_task(
                self.load_balancer.start_health_check(config.UPSTREAM_HEALTH_CHECK_INTERVAL)
            )

        # Rebuild httpx client with new timeout
        pool_limits = httpx.Limits(
            max_connections=int(os.environ.get("UPSTREAM_MAX_CONNECTIONS", "100")),
            max_keepalive_connections=int(os.environ.get("UPSTREAM_MAX_KEEPALIVE", "20")),
        )
        client_timeout = httpx.Timeout(float(os.environ.get("UPSTREAM_TIMEOUT", "120.0")))
        self._client = httpx.AsyncClient(timeout=client_timeout, limits=pool_limits)
        self._max_retries = int(os.environ.get("UPSTREAM_MAX_RETRIES", "0"))
        self._retry_delay = float(os.environ.get("UPSTREAM_RETRY_DELAY", "1.0"))

        logger.info("GatewayCore configuration hot-reloaded")


# 全局网关核心实例
gateway_core: Optional[GatewayCore] = None


def get_gateway_core() -> GatewayCore:
    """获取网关核心实例"""
    global gateway_core
    if gateway_core is None:
        gateway_core = GatewayCore()
    return gateway_core
