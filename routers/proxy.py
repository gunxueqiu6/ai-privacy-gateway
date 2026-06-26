"""
核心代理路由 — chat/completions + v1 通用代理。
"""
import json
import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from routers.dependencies import BAD_ENCODING_RESPONSE, filter_proxy_headers, limiter, safe_json
from gateway_core import get_gateway_core
from database import db
from config import config

logger = logging.getLogger(__name__)

proxy_router = APIRouter(tags=["proxy"])

ALLOWED_V1_PROXY_PATHS = {"models", "embeddings", "moderations"}


def _resolve_auth_and_headers(request: Request):
    """Extract auth header and build forwarding headers (Lite version).

    Backward-compatible: checks Authorization first, then falls back
    to X-API-Key for older SDKs that haven't migrated yet.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            auth_header = f"Bearer {api_key}"
    if not auth_header:
        return None

    headers = filter_proxy_headers(request.headers)
    return headers


@proxy_router.post("/v1/chat/completions")
@limiter.limit("60/minute")
async def chat_completions(request: Request) -> Response:
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE

    headers = _resolve_auth_and_headers(request)
    if headers is None:
        return JSONResponse(status_code=401, content={"error": "未授权 - 需要 API Key"})

    masked_body, mappings, stats, session_id, used_placeholders = gateway.mask_request(body)

    if mappings:
        db.save_mappings(session_id, mappings, data_type="unknown", team_id=None)
        db.update_stats(stats, team_id=None)

    if body.get("stream", False):
        from sse_starlette.sse import EventSourceResponse

        async def generate():
            async for chunk in gateway.proxy_stream_request(
                masked_body, headers, mappings, used_placeholders
            ):
                yield chunk

        return EventSourceResponse(generate())

    status_code, resp_body, resp_headers = await gateway.proxy_request(
        masked_body, headers, mappings, session_id
    )

    if isinstance(resp_body, bytes):
        try:
            resp_json = json.loads(resp_body)
            if "choices" in resp_json:
                for choice in resp_json["choices"]:
                    if "message" in choice:
                        choice["message"]["content"] = gateway.unmask_response(
                            choice["message"]["content"], mappings, session_id, used_placeholders
                        )
                resp_body = json.dumps(resp_json).encode()
        except json.JSONDecodeError:
            pass

    return Response(
        content=resp_body,
        status_code=status_code,
        headers={"Content-Type": resp_headers.get("content-type", "application/json")},
    )


@proxy_router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v1(request: Request, path: str) -> Response:
    """通用 v1 路由代理（仅白名单路径）"""
    if path not in ALLOWED_V1_PROXY_PATHS:
        logger.warning(f"拒绝代理未知路径: /v1/{path}")
        return JSONResponse(status_code=404, content={"error": "未知的 API 路径"})

    gateway = get_gateway_core()

    headers = _resolve_auth_and_headers(request)
    if headers is None:
        return JSONResponse(status_code=401, content={"error": "未授权 - 需要 API Key"})

    method = request.method
    body_bytes = await request.body() if method in ["POST", "PUT", "PATCH"] else None

    status_code, resp_body, resp_headers = await gateway.proxy_generic_request(
        method, f"/v1/{path}", headers, body_bytes
    )

    return Response(content=resp_body, status_code=status_code)
