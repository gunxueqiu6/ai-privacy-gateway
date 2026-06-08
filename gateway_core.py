"""
网关核心模块 - 上行脱敏 + 下行还原 + HTTP 代理转发
"""
import json
import logging
import time
import uuid
from typing import Dict, Any, Tuple, AsyncGenerator, Optional

import httpx

from config import config
from mask_engine import get_mask_engine, MaskEngineInterface
from database import db


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

    def mask_request(self, body: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, int], str]:
        """
        上行脱敏处理
        返回: (脱敏后的body, mappings, stats, session_id)
        """
        session_id = self.generate_session_id()

        all_mappings = {}
        total_stats = {
            "phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0,
            "person": 0, "location": 0, "org": 0, "organization": 0, 
            "plate": 0, "ip": 0, "url": 0, "date": 0, "amount": 0, "postcode": 0
        }

        messages = body.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue

            masked_content, mappings, stats = self.mask_engine.mask(content)
            msg["content"] = masked_content
            all_mappings.update(mappings)

            for k, v in stats.items():
                if k in total_stats:
                    total_stats[k] += v

        total_count = sum(total_stats.values())
        logger.info(f"[网关拦截] 会话 {session_id}，拦截敏感信息 {total_count} 条")
        
        # 记录审计日志
        db.log_audit(session_id, "mask_request", {
            "entity_count": total_count,
            "stats": total_stats
        })

        return body, all_mappings, total_stats, session_id

    def unmask_response(self, text: str, mappings: Dict[str, str], session_id: str = None) -> str:
        """
        下行还原处理
        """
        if not mappings:
            return text

        result = self.mask_engine.unmask(text, mappings)
        return result

    async def proxy_request(
        self,
        body: Dict[str, Any],
        headers: Dict[str, str],
        mappings: Dict[str, str],
        session_id: str = None
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        代理转发请求到目标 LLM
        返回: (status_code, response_body, response_headers)
        """
        target_url = f"{self.target_url}/v1/chat/completions"
        start_time = time.time()

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

                latency_ms = int((time.time() - start_time) * 1000)
                
                # 记录审计日志
                db.log_audit(session_id, "proxy_request", {
                    "status_code": response.status_code,
                    "latency_ms": latency_ms
                })

                return response.status_code, response.content, dict(response.headers)

            except httpx.TimeoutException:
                logger.error(f"[网关错误] 请求超时")
                db.log_audit(session_id, "proxy_error", {"error": "Timeout"})
                return 504, {"error": "Gateway Timeout"}, {}
            except httpx.RequestError as e:
                logger.error(f"[网关错误] 请求失败: {e}")
                db.log_audit(session_id, "proxy_error", {"error": str(e)})
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
