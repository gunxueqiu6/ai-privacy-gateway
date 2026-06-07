"""
网关核心模块 - 上行脱敏 + 下行还原 + HTTP 代理转发
与 FastAPI 解耦，可独立测试
"""
import json
import logging
import time
import uuid
from typing import Dict, Any, Tuple, AsyncGenerator, Optional

import httpx

from config import config
from mask_engine import get_mask_engine, MaskEngineInterface
from audit_log import get_audit_logger
from alert_manager import get_alert_manager
from decay_manager import get_decay_manager


logger = logging.getLogger(__name__)


class GatewayCore:
    """网关核心处理类"""

    def __init__(self):
        self.mask_engine = get_mask_engine()
        self.target_url = config.TARGET_LLM
        self.timeout = 120.0

    def generate_session_id(self) -> str:
        """生成会话ID"""
        return f"sess_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    def mask_request(self, body: Dict[str, Any], user_id: str = None, ip_address: str = None) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, int], str]:
        """
        上行脱敏处理
        返回: (脱敏后的body, mappings, stats, session_id)
        """
        session_id = self.generate_session_id()

        # 衰减检查
        decay = get_decay_manager()
        decay.update()

        if decay.should_disable_masking():
            logger.warning(f"[衰减] 脱敏已禁用 (等级 {decay.current_level.value})，明文转发")
            return body, {}, {"phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0}, session_id

        if decay.should_drop_request():
            logger.warning(f"[衰减] 随机丢弃请求 (等级 {decay.current_level.value})")
            raise RuntimeError("Service degraded, request dropped")

        all_mappings = {}
        total_stats = {"phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0}

        messages = body.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue

            masked_content, mappings, stats = self.mask_engine.mask(content)
            msg["content"] = masked_content
            all_mappings.update(mappings)

            for k, v in stats.items():
                total_stats[k] += v

        total_count = sum(total_stats.values())
        logger.info(f"[网关拦截] 会话 {session_id}，拦截敏感信息 {total_count} 条")

        # 审计日志
        if config.feature_audit_log:
            audit = get_audit_logger()
            audit.log_mask_action(
                session_id=session_id,
                original_content=json.dumps(body.get("messages", [])),
                masked_content=json.dumps(messages),
                mappings=all_mappings,
                stats=total_stats,
                user_id=user_id,
                ip_address=ip_address
            )

        # 高频脱敏告警
        if total_count >= 100:
            alert = get_alert_manager()
            alert.check_high_frequency(session_id, total_count)

        return body, all_mappings, total_stats, session_id

    def unmask_response(self, text: str, mappings: Dict[str, str], session_id: str = None) -> str:
        """
        下行还原处理
        """
        if not mappings:
            return text

        result = self.mask_engine.unmask(text, mappings)

        # 审计日志
        if config.feature_audit_log and session_id:
            audit = get_audit_logger()
            audit.log_unmask_action(
                session_id=session_id,
                masked_content=text[:500] if len(text) > 500 else text,
                unmasked_content=result[:500] if len(result) > 500 else result,
                mappings=mappings
            )

        return result

    async def proxy_request(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str],
        mappings: Dict[str, str]
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        代理转发请求到目标 LLM
        返回: (status_code, response_body, response_headers)
        """
        target_url = f"{self.target_url}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    target_url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": headers.get("Authorization", "")
                    }
                )

                return response.status_code, response.content, dict(response.headers)

            except httpx.TimeoutException:
                logger.error(f"[网关错误] 请求超时")
                return 504, {"error": "Gateway Timeout"}, {}
            except httpx.RequestError as e:
                logger.error(f"[网关错误] 请求失败: {e}")
                return 502, {"error": str(e)}, {}

    async def proxy_stream_request(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str],
        mappings: Dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """
        流式代理转发
        """
        target_url = f"{self.target_url}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    target_url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": headers.get("Authorization", "")
                    }
                ) as response:

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break

                            # 还原敏感信息
                            unmasked_data = self.unmask_response(data, mappings)
                            yield f"data: {unmasked_data}\n\n"
                        else:
                            yield f"{line}\n"

            except httpx.TimeoutException:
                logger.error(f"[流式错误] 请求超时")
                yield 'data: {"error": "Gateway Timeout"}\n\n'
            except httpx.RequestError as e:
                logger.error(f"[流式错误] 请求失败: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def proxy_generic_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        通用代理转发（非 chat/completions 路由）
        """
        target_url = f"{self.target_url}{path}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    content=body
                )

                return response.status_code, response.content, dict(response.headers)

            except httpx.RequestError as e:
                logger.error(f"[代理错误] {e}")
                return 502, {"error": str(e)}, {}


# 全局网关核心实例
gateway_core: Optional[GatewayCore] = None


def get_gateway_core() -> GatewayCore:
    """获取网关核心实例"""
    global gateway_core
    if gateway_core is None:
        gateway_core = GatewayCore()
    return gateway_core