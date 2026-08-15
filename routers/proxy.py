"""
核心代理路由 — chat/completions + v1 通用代理。
"""

import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from routers.dependencies import (
    BAD_ENCODING_RESPONSE,
    filter_proxy_headers,
    limiter,
    safe_json,
)
from gateway_core import get_gateway_core
from database import db
from config import config
from mask_engine import dominant_compliance_tag

logger = logging.getLogger(__name__)

proxy_router = APIRouter(tags=["proxy"])

ALLOWED_V1_PROXY_PATHS = {
    "models",
    "embeddings",
    "moderations",
    "messages",
    "images",
    "audio",
}


def _resolve_auth_and_headers(request: Request):
    """Extract auth header, validate the API key, and build forwarding headers.

    Returns (headers_dict, raw_api_key, team_id).

    Raises HTTPException(401) if the API key is missing or not registered.

    Backward-compatible: checks Authorization first, then falls back
    to X-API-Key for older SDKs that haven't migrated yet.
    """
    raw_api_key = ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        if auth_header.startswith("Bearer "):
            raw_api_key = auth_header[7:]
    else:
        raw_api_key = request.headers.get("X-API-Key", "")
        if raw_api_key:
            auth_header = f"Bearer {raw_api_key}"
    if not auth_header:
        raise HTTPException(status_code=401, detail="未授权 - 需要 API Key")

    team_id = _lookup_team_id(raw_api_key)
    headers = filter_proxy_headers(request.headers)
    return headers, raw_api_key, team_id


def _lookup_team_id(raw_api_key: str) -> str:
    """Look up team_id from user_api_keys by hashing the raw API key.

    Unknown keys are rejected with 401 unless ALLOW_ANONYMOUS=true, in
    which case they fall back to the 'default' team.
    """
    if not raw_api_key:
        return _anonymous_or_reject()
    try:
        key_hash = hashlib.sha256(raw_api_key.encode()).hexdigest()
        row = db.verify_api_key(key_hash)
        if row:
            try:
                db.update_api_key_last_used(key_hash)
            except Exception:
                logger.warning("Failed to update API key last_used", exc_info=True)
            return row.get("team_id") or "default"
    except Exception:
        logger.warning("API key lookup failed", exc_info=True)
    return _anonymous_or_reject()


def _anonymous_or_reject() -> str:
    """Return 'default' when anonymous access is enabled, otherwise reject with 401."""
    if config.ALLOW_ANONYMOUS:
        logger.warning("未知 API Key，ALLOW_ANONYMOUS=true 回退到 default 团队")
        return "default"
    raise HTTPException(status_code=401, detail="未授权 - 无效的 API Key")


@proxy_router.post("/v1/chat/completions")
@limiter.limit("60/minute")
async def chat_completions(request: Request) -> Response:
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE

    headers, raw_api_key, team_id = _resolve_auth_and_headers(request)

    audit_ctx = {
        "team_id": team_id,
        "key_hash": (
            hashlib.sha256(raw_api_key.encode()).hexdigest() if raw_api_key else None
        ),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

    masked_body, mappings, stats, session_id, used_placeholders = gateway.mask_request(
        body, audit_ctx
    )

    # 脱敏透明度响应头（所有请求都注入）
    total_masked = sum(v for k, v in stats.items() if k != "total")
    masked_types = sorted(k for k, v in stats.items() if v > 0 and k != "total")
    masking_headers = {
        "X-Masked-Count": str(total_masked),
        "X-Masked-Types": ",".join(masked_types),
        "X-Masked-Session-ID": session_id,
    }

    # Dry-Run 模式：添加检测结果响应头，不写 Vault
    dry_run_headers = {}
    if config.DRY_RUN_MODE:
        total_detected = sum(stats.values())
        if total_detected > 0:
            detected_types = [k for k, v in stats.items() if v > 0]
            dry_run_headers["X-Dry-Run-Detected"] = str(total_detected)
            dry_run_headers["X-Dry-Run-Detected-Types"] = ",".join(detected_types)

    if mappings and not config.DRY_RUN_MODE:
        db.save_mappings(
            session_id,
            mappings,
            data_type=dominant_compliance_tag(stats),
            team_id=team_id,
        )
        db.update_stats(stats, team_id=team_id)

    if body.get("stream", False):
        from sse_starlette.sse import EventSourceResponse
        import json as _json

        async def generate():
            async for chunk in gateway.proxy_stream_request(
                masked_body, headers, mappings, used_placeholders, session_id, audit_ctx
            ):
                data = chunk.get("data", "")
                if data == "[DONE]":
                    yield {
                        "event": "masked",
                        "data": _json.dumps(
                            {
                                "count": total_masked,
                                "types": masked_types,
                                "session_id": session_id,
                            }
                        ),
                    }
                yield chunk

        return EventSourceResponse(generate())

    status_code, resp_body, resp_headers = await gateway.proxy_request(
        masked_body, headers, mappings, session_id, audit_ctx
    )

    if isinstance(resp_body, bytes):
        try:
            resp_json = json.loads(resp_body)
            if "choices" in resp_json:
                for choice in resp_json["choices"]:
                    if "message" in choice:
                        content = choice["message"].get("content")
                        if content is not None:
                            choice["message"]["content"] = gateway.unmask_response(
                                content, mappings, session_id, used_placeholders
                            )
                resp_body = json.dumps(resp_json).encode()
        except json.JSONDecodeError:
            pass

    return Response(
        content=resp_body,
        status_code=status_code,
        headers={
            "Content-Type": resp_headers.get("content-type", "application/json"),
            **masking_headers,
            **dry_run_headers,
        },
    )


@proxy_router.api_route(
    "/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_v1(request: Request, path: str) -> Response:
    """通用 v1 路由代理（仅白名单路径）"""
    if path not in ALLOWED_V1_PROXY_PATHS:
        logger.warning(f"拒绝代理未知路径: /v1/{path}")
        return JSONResponse(status_code=404, content={"error": "未知的 API 路径"})

    gateway = get_gateway_core()

    headers, _raw_api_key, _team_id = _resolve_auth_and_headers(request)

    method = request.method
    body_bytes = await request.body() if method in ["POST", "PUT", "PATCH"] else None

    status_code, resp_body, resp_headers = await gateway.proxy_generic_request(
        method, f"/v1/{path}", headers, body_bytes
    )

    return Response(content=resp_body, status_code=status_code)
