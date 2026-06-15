"""
认证路由 — Lite 版本（管理员登录在 admin.py，团队/OAuth 在 Pro 版本中）。
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import config

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["auth"])


@auth_router.get("/auth/status")
async def auth_status(request: Request) -> JSONResponse:
    """认证状态 — Lite 版本仅支持管理员认证（见 /admin/login）"""
    return JSONResponse({
        "tier": config.tier,
        "auth_methods": ["admin_login"],
        "message": "Lite版本支持管理员密码认证",
    })
