"""
认证路由 — Lite 版本（管理员登录在 admin.py，团队/OAuth 在 Pro 版本中）。
"""

import hashlib
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config import config
from database import db

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["auth"])


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """验证 API Key，返回 {team_id, key_hash, tier, key_prefix}。"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    row = db.get_api_key(key_hash)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not row.get("is_active"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    db.update_api_key_last_used(key_hash)
    return {
        "team_id": row["team_id"],
        "key_hash": key_hash,
        "tier": row.get("tier", "free"),
        "key_prefix": row.get("key_prefix", ""),
    }


@auth_router.get("/auth/status")
async def auth_status(request: Request) -> JSONResponse:
    """认证状态 — Lite 版本仅支持管理员认证（见 /admin/login）"""
    return JSONResponse(
        {
            "tier": config.tier,
            "auth_methods": ["admin_login", "api_key"],
            "message": "Lite版本支持管理员密码认证 + API Key",
        }
    )
