"""
共享依赖 — 认证、限流、请求过滤等跨路由依赖。
"""
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional, Set

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from slowapi import Limiter

from config import config


# ==================== Encoding Error Handler ====================

BAD_ENCODING_RESPONSE = JSONResponse(
    status_code=400,
    content={
        "error": "请求体编码错误",
        "detail": "请使用 UTF-8 编码发送 JSON 数据",
        "hint": "curl -X POST ... -H 'Content-Type: application/json; charset=utf-8' --data-binary @file.json",
    },
)


async def safe_json(request: Request):
    """Parse JSON body with proper error handling for non-UTF-8 encoding."""
    try:
        return await request.json(), True
    except Exception:
        return None, False


# ==================== Rate Limiter ====================

def _get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=_get_client_ip)

# NOTE: In-memory rate limiter — each uvicorn worker has its own counter.
# With multiple workers (`uvicorn --workers N`), a client can exceed the
# per-worker limit N-fold. For multi-worker deployments, swap in a shared
# backend such as `Limiter(key_func=..., storage_uri="redis://...")`.


def reset_limiter() -> None:
    """Reset the rate limiter storage. Used in tests to prevent
    state leakage between test cases that share the same limiter."""
    storage = getattr(limiter, "_storage", None) or getattr(limiter, "storage", None)
    if storage is not None:
        storage.reset()


# ==================== Proxy Helpers ====================

ALLOWED_PROXY_HEADERS = {"content-type", "authorization"}


def filter_proxy_headers(headers: Any) -> Dict[str, str]:
    return {k.lower(): v for k, v in headers.items() if k.lower() in ALLOWED_PROXY_HEADERS}


ALLOWED_V1_PROXY_PATHS = {"models", "embeddings", "moderations"}


# ==================== Token Blacklist ====================

_token_blacklist: Set[str] = set()


# ==================== JWT Auth ====================

def create_jwt_token() -> str:
    """创建 JWT 令牌 — 1 小时有效"""
    expire = datetime.now(UTC) + timedelta(hours=1)
    to_encode = {"sub": "admin", "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> bool:
    """验证 JWT 令牌"""
    if token in _token_blacklist:
        return False
    try:
        jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        return True
    except JWTError:
        return False


async def get_current_user_token(request: Request) -> Optional[str]:
    """从请求中获取用户令牌"""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("session_token")


async def require_admin(request: Request) -> str:
    """要求管理员权限"""
    token = await get_current_user_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="未授权 - 需要登录")
    if not verify_jwt_token(token):
        raise HTTPException(status_code=401, detail="无效的会话")
    return token
