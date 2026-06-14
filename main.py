"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional, Set, Union

from fastapi import Depends, FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from jose import JWTError, jwt
import uuid as _uuid

from payment import get_paypal_client, PayPalError
from license import get_license_service, LicenseError
from oauth import (
    OAuthError,
    oauth_config,
    generate_state,
    get_oauth_url,
    exchange_code,
    SUPPORTED_PROVIDERS,
)
from reports import (get_daily_report, get_weekly_report, get_monthly_report, export_report_csv, get_summary_stats)
from alerts import get_alert_engine
from redis_cache import get_redis_cache
from team import (
    create_team, get_team, get_team_members, get_member_count,
    create_user, authenticate_user, get_user_by_id, get_user_by_api_key,
    remove_user, update_user_role, regenerate_api_key,
    create_session, validate_session, delete_session,
    find_or_create_oauth_user,
    update_team_settings, get_team_settings,
    ROLE_ADMIN, ROLE_MEMBER, ROLE_VIEWER, VALID_ROLES,
    TeamError,
)
import bcrypt

from config import config, get_config
from database import db
from gateway_core import get_gateway_core
from mask_engine import get_mask_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="AI隐私网关",
    description="边缘侧本地隐私网关 - 拦截AI请求自动脱敏",
    version="2.0"
)

# 挂载静态文件 - 管理面板
app.mount("/admin/static", StaticFiles(directory="static"), name="admin_static")

# 速率限制 — 使用 client.host 忽略 X-Forwarded-For 防伪造
def _get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"

limiter = Limiter(key_func=_get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9999", "http://127.0.0.1:9999"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 请求体大小上限
MAX_REQUEST_BODY = 1024 * 1024  # 1MB

# 代理请求头白名单 — 只转发 Content-Type 和 Authorization
ALLOWED_PROXY_HEADERS = {"content-type", "authorization"}

def filter_proxy_headers(headers: Any) -> Dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in ALLOWED_PROXY_HEADERS}

# Token 黑名单 (登出后失效)
_token_blacklist: Set[str] = set()


# ==================== 认证依赖 ====================

def create_jwt_token() -> str:
    """创建 JWT 令牌 — 1 小时有效"""
    expire = datetime.now(UTC) + timedelta(hours=1)
    to_encode = {"sub": "admin", "exp": expire, "iat": datetime.now(UTC)}
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


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


# Tier enum and gating
from enum import Enum

class Tier(str, Enum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def order(self) -> int:
        _order = {"lite": 0, "pro": 1, "enterprise": 2}
        return _order[self.value]

    def __ge__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() >= other.order()
        return NotImplemented

    def __lt__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() < other.order()
        return NotImplemented

    def __le__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() <= other.order()
        return NotImplemented

    def __gt__(self, other: "Tier") -> bool:
        if isinstance(other, Tier):
            return self.order() > other.order()
        return NotImplemented


def require_tier(minimum: str):
    """FastAPI dependency that requires a minimum license tier.

    Returns 402 Payment Required if the current tier is too low.
    Use with ``Depends()``: ``_=require_tier("pro")``
    """
    order = {"lite": 0, "pro": 1, "enterprise": 2}

    async def _check(request: Request) -> None:
        current = config.tier
        if order.get(current, 0) < order.get(minimum, 0):
            raise HTTPException(
                status_code=402,
                detail=f"This feature requires at least {minimum.upper()} tier. Current: {current.upper()}"
            )
    return Depends(_check)


# ==================== Team-based Auth Functions ====================


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get the currently authenticated team user from session token.

    Checks Authorization header (Bearer), then falls back to user_session cookie.
    Uses validate_session() from team.py to verify the token and return the user.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        user = validate_session(token)
        if user:
            return user

    session_token = request.cookies.get("user_session")
    if session_token:
        user = validate_session(session_token)
        if user:
            return user

    return None


def require_role(*roles: str):
    """FastAPI dependency that checks if the authenticated user has one of the specified roles.

    Uses get_current_user (session/api-key based auth) to find the user,
    then checks their role. Returns 403 if the role does not match.

    This is separate from require_admin (JWT-based admin auth) and can be
    used alongside it on the same endpoint when needed.
    Use with ``Depends()``: ``_=require_role("admin")``
    """
    async def _check(request: Request) -> Dict[str, Any]:
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="未授权 - 需要登录")
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足 - 需要角色: {', '.join(roles)}",
            )
        return user
    return Depends(_check)


# ==================== 主代理路由 ====================

@app.post("/v1/chat/completions")
@limiter.limit("60/minute")
async def chat_completions(request: Request) -> Response:
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()

    body = await request.json()

    # 验证客户端 Authorization 头
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return JSONResponse(status_code=401, content={"error": "未授权 - 需要 API Key"})

    # Check for gateway API key authentication
    api_key_user = None
    if auth_header.startswith("gw_api_"):
        api_key_user = get_user_by_api_key(auth_header)
        if not api_key_user:
            return JSONResponse(status_code=401, content={"error": "无效的 API Key"})
        request.state.team_id = api_key_user["team_id"]
        # Gateway API key is not forwarded to upstream
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() in ALLOWED_PROXY_HEADERS and k.lower() != "authorization"}
    else:
        headers = filter_proxy_headers(request.headers)

    # 上行脱敏
    masked_body, mappings, stats, session_id, used_placeholders = gateway.mask_request(body)

    # 保存映射到数据库（带 team_id 实现数据隔离）
    if mappings:
        team_id_for_storage = api_key_user["team_id"] if api_key_user else None
        db.save_mappings(session_id, mappings, data_type="unknown", team_id=team_id_for_storage)
        db.update_stats(stats)

    # 判断是否流式请求
    if body.get("stream", False):
        async def generate():
            async for chunk in gateway.proxy_stream_request(masked_body, headers, mappings, used_placeholders):
                yield chunk

        return EventSourceResponse(generate())
    else:
        status_code, resp_body, resp_headers = await gateway.proxy_request(masked_body, headers, mappings, session_id)

        # 还原响应内容
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
            headers={"Content-Type": resp_headers.get("content-type", "application/json")}
        )


# 允许代理的 v1 API 路径白名单
ALLOWED_V1_PROXY_PATHS = {"models", "embeddings", "moderations"}


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("60/minute")
async def proxy_v1(request: Request, path: str) -> Response:
    """通用 v1 路由代理（仅白名单路径）"""
    # 路径白名单校验
    if path not in ALLOWED_V1_PROXY_PATHS:
        logger.warning(f"拒绝代理未知路径: /v1/{path}")
        raise HTTPException(status_code=404, detail="未知的 API 路径")

    gateway = get_gateway_core()

    # 验证客户端 Authorization 头
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return JSONResponse(status_code=401, content={"error": "未授权 - 需要 API Key"})

    # Check for gateway API key authentication
    api_key_user = None
    if auth_header.startswith("gw_api_"):
        api_key_user = get_user_by_api_key(auth_header)
        if not api_key_user:
            return JSONResponse(status_code=401, content={"error": "无效的 API Key"})
        request.state.team_id = api_key_user["team_id"]
        # Gateway API key is not forwarded to upstream
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() in ALLOWED_PROXY_HEADERS and k.lower() != "authorization"}
    else:
        headers = filter_proxy_headers(request.headers)

    method = request.method
    body = await request.body() if method in ["POST", "PUT", "PATCH"] else None

    status_code, resp_body, resp_headers = await gateway.proxy_generic_request(
        method, f"/v1/{path}", headers, body
    )

    return Response(content=resp_body, status_code=status_code)


# ==================== 独立 API 层 ====================

@app.post("/api/mask")
@limiter.limit("60/minute")
async def api_mask(request: Request):
    """独立脱敏 API - 输入文本返回脱敏结果"""
    body = await request.json()
    text = body.get("text", "")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text 参数不能为空"})

    # 限制输入大小
    if len(text) > 102400:
        return JSONResponse(status_code=413, content={"error": "输入文本过长，最大支持 100KB"})

    engine = get_mask_engine()
    masked_text, mappings, stats = engine.mask(text)

    entities = []
    for placeholder, value in mappings.items():
        entity_type = "unknown"
        if "PHONE" in placeholder:
            entity_type = "PII_PHONE"
        elif "EMAIL" in placeholder:
            entity_type = "PII_EMAIL"
        elif "IDCARD" in placeholder:
            entity_type = "PII_IDCARD"
        elif "BANK" in placeholder:
            entity_type = "PII_BANK"
        elif "PER" in placeholder:
            entity_type = "PII_PER"
        elif "LOC" in placeholder:
            entity_type = "PII_LOC"
        elif "ORG" in placeholder:
            entity_type = "PII_ORG"
        elif "PLATE" in placeholder:
            entity_type = "PII_PLATE"
        elif "IP" in placeholder:
            entity_type = "PII_IP"
        elif "URL" in placeholder:
            entity_type = "PII_URL"
        elif "DATE" in placeholder:
            entity_type = "PII_DATE"
        elif "AMOUNT" in placeholder:
            entity_type = "PII_AMOUNT"
        elif "POSTCODE" in placeholder:
            entity_type = "PII_POSTCODE"
        elif "CUST" in placeholder:
            entity_type = "PII_CUST"

        entities.append({
            "type": entity_type,
            "value": value,
            "placeholder": placeholder,
            "position": text.find(value)
        })

    return {
        "masked_text": masked_text,
        "entities": entities,
        "stats": stats
    }


@app.post("/api/restore")
@limiter.limit("60/minute")
async def api_restore(request: Request):
    """独立还原 API - 输入脱敏文本返回原始文本"""
    body = await request.json()
    masked_text = body.get("text", "")
    mappings = body.get("mappings", {})

    if not masked_text:
        return JSONResponse(status_code=400, content={"error": "text 参数不能为空"})

    # 限制输入大小
    if len(masked_text) > 102400:
        return JSONResponse(status_code=413, content={"error": "输入文本过长，最大支持 100KB"})

    engine = get_mask_engine()
    original_text = engine.unmask(masked_text, mappings)

    return {
        "original_text": original_text
    }


@app.post("/api/mask/batch")
@limiter.limit("30/minute")
async def api_mask_batch(request: Request):
    """批量脱敏 API"""
    body = await request.json()
    texts = body.get("texts", [])

    if not isinstance(texts, list) or len(texts) == 0:
        return JSONResponse(status_code=400, content={"error": "texts 必须是非空数组"})

    if len(texts) > 50:
        return JSONResponse(status_code=400, content={"error": "单次批量处理最多 50 条"})

    # 限制每条输入大小
    for i, t in enumerate(texts):
        if len(t) > 102400:
            return JSONResponse(status_code=413, content={"error": f"第 {i+1} 条文本过长，最大支持 100KB"})

    engine = get_mask_engine()
    results = []

    for text in texts:
        masked_text, mappings, stats = engine.mask(text)
        entities = []
        for placeholder, value in mappings.items():
            entities.append({
                "value": value,
                "placeholder": placeholder
            })
        results.append({
            "original": text,
            "masked": masked_text,
            "entities": entities,
            "stats": stats
        })

    return {
        "results": results,
        "total_count": len(results)
    }


@app.get("/api/entities")
async def api_get_entities(request: Request) -> dict:
    """获取支持的实体类型列表"""
    from mask_engine import HAS_NER

    entities = [
        {"type": "PII_PHONE", "name": "手机号", "description": "中国大陆手机号", "enabled": True, "engine": "regex"},
        {"type": "PII_EMAIL", "name": "邮箱", "description": "电子邮箱地址", "enabled": True, "engine": "regex"},
        {"type": "PII_IDCARD", "name": "身份证", "description": "中国身份证号码", "enabled": True, "engine": "regex"},
        {"type": "PII_BANK", "name": "银行卡", "description": "银行卡号码", "enabled": True, "engine": "regex"},
        {"type": "PII_PER", "name": "人名", "description": "中文人名", "enabled": HAS_NER, "engine": "ner" if HAS_NER else "unavailable"},
        {"type": "PII_LOC", "name": "地名", "description": "省份、城市、区县等", "enabled": HAS_NER, "engine": "ner" if HAS_NER else "unavailable"},
        {"type": "PII_ORG", "name": "机构名", "description": "公司、组织名称", "enabled": HAS_NER, "engine": "ner" if HAS_NER else "unavailable"},
        {"type": "PII_PLATE", "name": "车牌号", "description": "中国车牌号", "enabled": True, "engine": "regex"},
        {"type": "PII_IP", "name": "IP地址", "description": "IPv4 地址", "enabled": True, "engine": "regex"},
        {"type": "PII_URL", "name": "URL", "description": "网址链接", "enabled": True, "engine": "regex"},
        {"type": "PII_DATE", "name": "日期", "description": "日期格式", "enabled": True, "engine": "regex"},
        {"type": "PII_AMOUNT", "name": "金额", "description": "货币金额", "enabled": True, "engine": "regex"},
        {"type": "PII_POSTCODE", "name": "邮编", "description": "邮政编码", "enabled": True, "engine": "regex"},
        {"type": "PII_CUST", "name": "自定义", "description": "自定义敏感词", "enabled": True, "engine": "regex"},
    ]

    return {
        "entities": entities,
        "total": len(entities),
        "version": "Lite",
        "ner_available": HAS_NER
    }


# ==================== 管理后台 API ====================

@app.get("/")
async def root() -> dict:
    """Root - health check with tier info."""
    return {
        "status": "healthy",
        "service": "AI Privacy Gateway",
        "version": config.tier.capitalize() if config.tier != "lite" else "Lite",
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
    }



# ==================== Payment API ====================

@app.post("/api/payment/create-order")
@limiter.limit("10/minute")
async def payment_create_order(request: Request) -> JSONResponse:
    """Create a PayPal order for a Pro or Enterprise license."""
    paypal = get_paypal_client()
    if not paypal:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    body = await request.json()
    tier = body.get("tier", "pro")
    email = body.get("email", "")

    if tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid tier. Must be 'pro' or 'enterprise'")

    try:
        order = await paypal.create_order(amount=0, tier=tier, email=email)
        return JSONResponse({
            "id": order["id"],
            "status": order["status"],
            "tier": tier,
        })
    except PayPalError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@app.get("/api/payment/paypal-config")
@limiter.limit("30/minute")
async def payment_paypal_config(request: Request) -> JSONResponse:
    """Return PayPal client configuration for the frontend."""
    client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
    if not client_id:
        return JSONResponse({
            "client_id": "",
            "mode": config.PAYPAL_MODE,
            "configured": False,
        })
    return JSONResponse({
        "client_id": client_id,
        "mode": config.PAYPAL_MODE,
        "configured": True,
    })


@app.post("/api/payment/capture-order")
@limiter.limit("10/minute")
async def payment_capture_order(request: Request) -> JSONResponse:
    """Capture a PayPal payment and issue a license."""
    paypal = get_paypal_client()
    if not paypal:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    body = await request.json()
    order_id = body.get("order_id", "")
    email = body.get("email", "")
    tier = body.get("tier", "pro")

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    if tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    try:
        # Capture payment
        capture = await paypal.capture_order(order_id)

        if capture.get("status") != "COMPLETED":
            return JSONResponse(
                status_code=402,
                content={"status": "failed", "message": "Payment not completed"}
            )

        # Generate license
        license_svc = get_license_service()
        team_id = f"T{int(_uuid.uuid4().hex[:8], 16) % 10**8:08d}"
        license_token = license_svc.sign_license(
            team_id=team_id,
            tier=tier,
            email=email,
        )

        # Decode to get expiration
        from datetime import datetime, timezone
        payload = license_svc.verify_license(license_token)[1]
        expires_at = datetime.fromtimestamp(
            payload["exp"], tz=timezone.utc
        ).strftime("%Y-%m-%d") if payload else "Unknown"

        # Save to database
        license_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.save_license(
            license_id=license_id,
            team_id=team_id,
            tier=tier,
            seats=payload["seats"] if payload else 20,
            email=email,
            issued_at=now,
            expires_at=expires_at,
            jwt_token=license_token,
            payment_id=order_id,
        )

        db.log_audit(None, "license_issued", {
            "team_id": team_id,
            "tier": tier,
            "email": email,
            "payment_id": order_id,
        })

        tier_name = "Pro (Team)" if tier == "pro" else "Enterprise"
        return JSONResponse({
            "status": "completed",
            "license_key": license_token,
            "team_id": team_id,
            "tier": tier,
            "tier_name": tier_name,
            "expires_at": expires_at,
        })

    except PayPalError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except LicenseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/payment/webhook")
@limiter.limit("30/minute")
async def payment_webhook(request: Request) -> JSONResponse:
    """Handle PayPal webhook events."""
    paypal = get_paypal_client()
    if not paypal:
        return JSONResponse(status_code=200, content={"status": "ignored"})

    body = await request.json()
    headers = dict(request.headers)

    verified, event_data = await paypal.handle_webhook(body, headers)

    if verified:
        logger.info(f"Verified PayPal webhook: {event_data}")
        db.log_audit(None, "payment_webhook", event_data or {})

    return JSONResponse({"status": "received"})


# ==================== License Management API ====================

@app.get("/admin/license")
@limiter.limit("10/minute")
async def admin_license_status(request: Request) -> JSONResponse:
    """View current license status (requires admin auth)."""
    await require_admin(request)

    from datetime import datetime, timezone

    license_svc = get_license_service()
    current_token = config.LICENSE_KEY

    if not current_token:
        return JSONResponse({
            "tier": config.tier,
            "status": "lite",
            "seats": 1,
            "message": "No license activated. Running in Lite mode.",
        })

    valid, payload, error = license_svc.verify_license(current_token)
    revoked = db.is_token_revoked(payload["tid"] if payload else "")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    expires_ts = payload.get("exp", 0) if payload else 0
    days_left = max(0, (expires_ts - now_ts) // 86400)

    return JSONResponse({
        "tier": config.tier,
        "status": "active" if valid and not revoked else "invalid",
        "seats": config.license_seats,
        "team_id": config.license_team_id,
        "expires_at": datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat() if expires_ts else None,
        "days_left": days_left,
        "revoked": revoked,
        "error": error if not valid else None,
    })


@app.post("/admin/license/activate")
@limiter.limit("5/minute")
async def admin_license_activate(request: Request) -> JSONResponse:
    """Activate a license key (requires admin auth)."""
    await require_admin(request)

    body = await request.json()
    license_key = body.get("license_key", "").strip()

    if not license_key:
        raise HTTPException(status_code=400, detail="license_key is required")

    license_svc = get_license_service()

    # Verify the license
    valid, payload, error = license_svc.verify_license(license_key)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid license: {error}")

    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid license payload")

    team_id = payload.get("tid", "")
    tier = payload.get("tier", "")
    seats = payload.get("seats", 1)

    # Check if this team's license is revoked
    if db.is_token_revoked(team_id):
        raise HTTPException(status_code=403, detail="This license has been revoked")

    # Save to file
    license_file = config.LICENSE_FILE
    with open(license_file, "w", encoding="utf-8") as f:
        f.write(license_key)

    # Update runtime config
    config.tier = tier
    config.license_seats = seats
    config.license_team_id = team_id
    config.LICENSE_KEY = license_key

    from datetime import datetime, timezone
    expires_ts = payload.get("exp", 0)
    config.license_expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat()

    db.log_audit(None, "license_activated", {
        "team_id": team_id,
        "tier": tier,
        "seats": seats,
    })

    logger.info(f"License activated: tier={tier}, team={team_id}, seats={seats}")

    return JSONResponse({
        "status": "ok",
        "message": "License activated successfully",
        "tier": tier,
        "team_id": team_id,
        "seats": seats,
    })


@app.post("/admin/license/refresh")
@limiter.limit("5/minute")
async def admin_license_refresh(request: Request) -> JSONResponse:
    """Refresh the current license status (re-read from file)."""
    await require_admin(request)

    # Reload from file if exists
    import os as _os
    license_file = config.LICENSE_FILE
    if not _os.path.exists(license_file):
        # Reset to lite
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "No license file found. Running in Lite mode.",
        })

    with open(license_file, "r", encoding="utf-8") as f:
        license_key = f.read().strip()

    if not license_key:
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "Empty license file. Running in Lite mode.",
        })

    license_svc = get_license_service()
    valid, payload, error = license_svc.verify_license(license_key)

    if not valid:
        logger.warning(f"License refresh failed: {error}")
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": f"License invalid: {error}. Downgraded to Lite.",
        })

    if payload is None:
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "License payload is empty. Running in Lite mode.",
        })

    team_id = payload.get("tid", "")
    if db.is_token_revoked(team_id):
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "License has been revoked. Downgraded to Lite.",
        })

    config.tier = payload.get("tier", "lite")
    config.license_seats = payload.get("seats", 1)
    config.license_team_id = team_id
    config.LICENSE_KEY = license_key

    from datetime import datetime, timezone
    expires_ts = payload.get("exp", 0)
    config.license_expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat()

    return JSONResponse({
        "status": "ok",
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
        "expires_at": config.license_expires_at,
    })


@app.get("/admin/license/check")
@limiter.limit("30/minute")
async def admin_license_check(request: Request) -> JSONResponse:
    """Public endpoint to check license status (no auth required)."""
    return JSONResponse({
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
        "expires_at": config.license_expires_at,
    })

@app.get("/health")
async def health() -> dict:
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(request: Request) -> JSONResponse:
    """管理员登录"""
    # 获取客户端 IP
    client_ip = request.client.host if request.client else "unknown"
    
    # 检查是否被锁定
    is_locked, remaining = db.check_login_attempt(client_ip)
    if is_locked:
        raise HTTPException(status_code=429, detail="登录尝试次数过多，请稍后再试")
    
    body = await request.json()
    password = body.get("password", "")

    # 验证密码
    try:
        password_bytes = password.encode()
        hash_bytes = config.ADMIN_PASSWORD_HASH.encode()
        if not bcrypt.checkpw(password_bytes, hash_bytes):
            db.record_login_attempt(client_ip, success=False)
            _, remaining = db.check_login_attempt(client_ip)
            logger.warning(f"管理员登录失败 (IP: {client_ip}), 剩余尝试次数: {remaining}")
            raise HTTPException(status_code=401, detail="密码错误")
    except HTTPException:
        raise
    except Exception as e:
        db.record_login_attempt(client_ip, success=False)
        logger.error(f"管理员登录异常 (IP: {client_ip}): {e}")
        raise HTTPException(status_code=401, detail="密码错误")

    # 登录成功，清除尝试记录
    db.record_login_attempt(client_ip, success=True)
    
    # 记录审计日志
    db.log_audit(None, "admin_login", {"ip": client_ip})
    
    # 生成 JWT 令牌
    token = create_jwt_token()

    response = JSONResponse({"status": "ok", "message": "登录成功", "token": token})
    response.set_cookie(key="session_token", value=token, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=86400)
    return response


@app.post("/admin/logout")
@limiter.limit("10/minute")
async def admin_logout(request: Request) -> JSONResponse:
    """管理员登出"""
    client_ip = request.client.host if request.client else "unknown"

    # 将当前 token 加入黑名单
    token = await get_current_user_token(request)
    if token:
        _token_blacklist.add(token)

    # 记录审计日志
    db.log_audit(None, "admin_logout", {"ip": client_ip})

    response = JSONResponse({"status": "ok", "message": "登出成功"})
    response.delete_cookie(key="session_token")
    return response


@app.get("/admin/stats")
@limiter.limit("10/minute")
async def get_stats(request: Request, date: Optional[str] = None) -> dict:
    """获取统计信息 - 需要认证"""
    await require_admin(request)

    if date:
        target_date = date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")

    stats = db.get_today_stats()
    return stats


@app.get("/admin/keywords")
@limiter.limit("10/minute")
async def list_keywords(request: Request) -> dict:
    """获取自定义敏感词列表 - 需要认证"""
    await require_admin(request)

    engine = get_mask_engine()
    return {"keywords": engine.get_custom_keywords()}


@app.post("/admin/keywords/add")
@limiter.limit("10/minute")
async def add_keyword(request: Request):
    """添加自定义敏感词 - 需要认证"""
    await require_admin(request)

    body = await request.json()
    keyword = body.get("keyword", "").strip()

    if not keyword:
        return JSONResponse(status_code=400, content={"error": "关键词不能为空"})

    if len(keyword) > 200:
        return JSONResponse(status_code=400, content={"error": "关键词长度不能超过 200 个字符"})

    if not keyword.isprintable():
        return JSONResponse(status_code=400, content={"error": "关键词包含不可见字符"})

    engine = get_mask_engine()
    if engine.add_custom_keyword(keyword):
        db.add_custom_keyword(keyword)
        return {"status": "ok", "message": f"关键词 '{keyword}' 已添加"}

    return JSONResponse(status_code=400, content={"error": "关键词已存在"})


@app.post("/admin/keywords/delete")
@limiter.limit("10/minute")
async def delete_keyword(request: Request):
    """删除自定义敏感词 - 需要认证"""
    await require_admin(request)

    body = await request.json()
    keyword = body.get("keyword", "").strip()

    if not keyword:
        return JSONResponse(status_code=400, content={"error": "关键词不能为空"})

    engine = get_mask_engine()
    if engine.remove_custom_keyword(keyword):
        db.delete_custom_keyword(keyword)
        return {"status": "ok", "message": f"关键词 '{keyword}' 已删除"}

    return JSONResponse(status_code=404, content={"error": "关键词不存在"})


@app.get("/admin/version")
@limiter.limit("10/minute")
async def get_version(request: Request) -> dict:
    """Get version info with license tier."""
    await require_admin(request)

    tier_display = {"lite": "Lite (Open Core)", "pro": "Pro (Team)", "enterprise": "Enterprise"}
    return {
        "version": "2.0",
        "version_type": tier_display.get(config.tier, "Unknown"),
        "version_display": config.tier.capitalize(),
        "tier": config.tier,
        "target_llm": config.TARGET_LLM,
        "license": {
            "team_id": config.license_team_id,
            "seats": config.license_seats,
            "expires_at": config.license_expires_at,
        },
    }


# Old version endpoint (replaced above)
@app.get("/admin/version")


@app.get("/admin/integrity")
@limiter.limit("10/minute")
async def check_integrity(request: Request) -> dict:
    """完整性检查"""
    await require_admin(request)

    import os
    db_path = config.DB_PATH
    config_path = "config.py"

    issues = []
    if not os.path.exists(db_path):
        issues.append("数据库文件缺失")

    try:
        stats = db.get_today_stats()
        if stats.get("total_count", 0) < 0:
            issues.append("统计数据异常")
    except Exception as e:
        issues.append(f"数据库查询异常: {str(e)}")

    status = "ok" if not issues else "error"
    return {
        "available": True,
        "last_result": {"status": status},
        "message": "所有检查通过" if status == "ok" else "; ".join(issues)
    }


@app.post("/admin/clear")
@limiter.limit("10/minute")
async def clear_mappings(request: Request) -> dict:
    """清除所有映射记录 - 需要认证"""
    await require_admin(request)

    db.clear_all_mappings()
    return {"status": "ok", "message": "所有映射记录已清除"}


# ==================== User Auth API ====================

@app.post("/auth/login")
@limiter.limit("10/minute")
async def user_login(request: Request) -> JSONResponse:
    """User login with username, password, and optional team_id."""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    team_id = body.get("team_id", "").strip() or None

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    client_ip = request.client.host if request.client else "unknown"
    is_locked, _ = db.check_login_attempt(client_ip)
    if is_locked:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    success, user, error = authenticate_user(username, password, team_id)
    if not success:
        db.record_login_attempt(client_ip, success=False)
        raise HTTPException(status_code=401, detail=error or "Login failed")

    db.record_login_attempt(client_ip, success=True)
    session_token = create_session(user["id"])
    db.log_audit(None, "user_login", {"user_id": user["id"], "team_id": user["team_id"]})

    response = JSONResponse({
        "status": "ok", "message": "Login successful",
        "user": user, "token": session_token,
    })
    response.set_cookie(key="user_session", value=session_token, httponly=True, samesite="strict", max_age=86400)
    return response


@app.post("/auth/logout")
@limiter.limit("10/minute")
async def user_logout(request: Request) -> JSONResponse:
    """User logout."""
    session_token = request.cookies.get("user_session")
    if not session_token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            session_token = auth[7:]
    if session_token:
        delete_session(session_token)
    response = JSONResponse({"status": "ok", "message": "Logged out"})
    response.delete_cookie("user_session")
    return response


@app.post("/auth/register")
@limiter.limit("5/minute")
async def user_register(request: Request) -> JSONResponse:
    """Register a new user account.

    Accepts username, password, and optional team_id.
    - If team_id is provided, the user is added to that existing team
      (seat limits from license config are enforced).
    - If team_id is not provided, a new team is created with the user as admin.
    Returns user info, API key, and session token.
    """
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    team_id = body.get("team_id", "").strip() or None

    # Validate username
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少需要 3 个字符")
    if len(username) > 50:
        raise HTTPException(status_code=400, detail="用户名不能超过 50 个字符")

    # Validate password
    if not password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码至少需要 8 个字符")

    try:
        if team_id:
            # Joining an existing team — check it exists
            team = get_team(team_id)
            if not team:
                raise HTTPException(status_code=404, detail="团队不存在")
            # Enforce seat limits when tier is pro or enterprise
            if config.tier in ("pro", "enterprise"):
                member_count = get_member_count(team_id)
                if member_count >= config.license_seats:
                    raise HTTPException(
                        status_code=402,
                        detail=f"团队已达到座位上限 ({config.license_seats})",
                    )
            user = create_user(team_id, username, password, ROLE_MEMBER)
        else:
            # Create a new team with this user as admin
            team_name = f"{username} 的团队"
            team = create_team(team_name)
            team_id = team["id"]
            user = create_user(team_id, username, password, ROLE_ADMIN)
    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create a session for the new user
    session_token = create_session(user["id"])
    db.log_audit(None, "user_registered", {
        "user_id": user["id"],
        "team_id": team_id,
        "username": username,
    })

    return JSONResponse({
        "status": "ok",
        "message": "注册成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "team_id": user["team_id"],
        },
        "api_key": user["api_key"],
        "token": session_token,
    }, status_code=201)


@app.get("/auth/me")
@limiter.limit("30/minute")
async def auth_me(request: Request) -> JSONResponse:
    """Get current user info (session or API key based auth)."""
    # Try session-based auth first
    user = await get_current_user(request)
    if not user:
        # Fall back to API key auth
        auth = request.headers.get("Authorization", "")
        if auth and auth.startswith("gw_api_"):
            user = get_user_by_api_key(auth)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Return safe user info (password_hash already removed by get_user_by_api_key / validate_session)
    safe_user = {
        "id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role"),
        "team_id": user.get("team_id"),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
        "is_active": user.get("is_active"),
    }
    return JSONResponse(safe_user)


# ==================== OAuth / SSO Routes (Enterprise) ====================


@app.get("/auth/oauth/login/{provider}")
@limiter.limit("10/minute")
async def oauth_login(provider: str, request: Request,
                      _=require_tier("enterprise")) -> Response:
    """Initiate OAuth login with the given provider.

    Generates a state parameter for CSRF protection, stores it in a cookie,
    and redirects the user to the provider's OAuth authorization page.
    Enterprise tier required.
    """

    provider = provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}",
        )

    if not oauth_config.is_provider_configured(provider):
        raise HTTPException(
            status_code=503,
            detail=f"OAuth provider '{provider}' is not configured. Set environment variables.",
        )

    state = generate_state()
    auth_url = get_oauth_url(provider, state)

    response = RedirectResponse(url=auth_url, status_code=302)
    # Set state cookie for CSRF verification on callback
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,  # 10 minutes
        secure=request.url.scheme == "https",
    )
    logger.info("OAuth login initiated: provider=%s", provider)
    return response


@app.get("/auth/oauth/callback/{provider}")
@limiter.limit("10/minute")
async def oauth_callback(
    provider: str,
    request: Request,
    _=require_tier("enterprise"),
    code: Optional[str] = None,
    state: Optional[str] = None,
) -> Response:
    """Handle OAuth callback from the provider.

    Verifies the state parameter for CSRF protection, exchanges the
    authorization code for user info, creates or finds a user in the
    license team, creates a session, and redirects to the admin panel
    with a JWT token.
    """

    provider = provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}",
        )

    # Verify state for CSRF protection
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not state or stored_state != state:
        logger.warning(
            "OAuth state mismatch (CSRF detected): provider=%s", provider
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state. This may be a CSRF attack or the session expired.",
        )

    if not code:
        # Check for error in query params
        error = request.query_params.get("error", "access_denied")
        error_desc = request.query_params.get("error_description", "User denied authorization")
        logger.warning("OAuth callback error: provider=%s, error=%s", provider, error)
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {error_desc}")

    # Exchange code for user info
    try:
        user_info = await exchange_code(provider, code)
    except OAuthError as e:
        logger.error("OAuth code exchange failed: %s", str(e))
        raise HTTPException(status_code=502, detail=f"OAuth exchange failed: {str(e)}")

    # Get team_id for the OAuth user (use the license team)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(
            status_code=400,
            detail="No license team configured. Activate an Enterprise license first.",
        )

    # Find or create the user in the team
    try:
        user = find_or_create_oauth_user(
            team_id=team_id,
            email=user_info["email"],
            name=user_info["name"],
            provider=user_info["provider"],
            provider_id=user_info["provider_id"],
        )
    except TeamError as e:
        logger.error("Failed to find/create OAuth user: %s", str(e))
        raise HTTPException(status_code=500, detail=f"User management error: {str(e)}")

    # Create session and JWT token for admin access
    session_token = create_session(user["id"])
    jwt_token = create_jwt_token()

    db.log_audit(None, "oauth_login", {
        "provider": provider,
        "user_id": user["id"],
        "email": user_info.get("email", ""),
    })

    logger.info(
        "OAuth login successful: provider=%s, email=%s",
        provider, user_info.get("email", ""),
    )

    # Redirect to admin panel with JWT token
    redirect_url = f"/admin/static/admin.html?token={jwt_token}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,
        samesite="strict",
        max_age=86400,
        secure=request.url.scheme == "https",
    )
    response.set_cookie(
        key="user_session",
        value=session_token,
        httponly=True,
        samesite="strict",
        max_age=86400,
        secure=request.url.scheme == "https",
    )
    # Clear the oauth state cookie
    response.delete_cookie(key="oauth_state")
    return response


# ==================== Statistics Reports API ====================

@app.get("/admin/reports/daily")
@limiter.limit("10/minute")
async def admin_reports_daily(request: Request, date: Optional[str] = None, _=require_tier("pro")) -> JSONResponse:
    """Get daily statistics report."""
    await require_admin(request)
    team_id = config.license_team_id
    report = get_daily_report(team_id, date)
    return JSONResponse(report)


@app.get("/admin/reports/weekly")
@limiter.limit("10/minute")
async def admin_reports_weekly(request: Request, end_date: Optional[str] = None, _=require_tier("pro")) -> JSONResponse:
    """Get weekly statistics report (daily breakdown for 7 days)."""
    await require_admin(request)
    team_id = config.license_team_id
    report = get_weekly_report(team_id, end_date)
    return JSONResponse({"days": report, "count": len(report)})


@app.get("/admin/reports/monthly")
@limiter.limit("10/minute")
async def admin_reports_monthly(request: Request, year: Optional[int] = None, month: Optional[int] = None, _=require_tier("pro")) -> JSONResponse:
    """Get monthly statistics report."""
    await require_admin(request)
    team_id = config.license_team_id
    report = get_monthly_report(team_id, year, month)
    return JSONResponse({"days": report, "count": len(report)})


@app.get("/admin/reports/summary")
@limiter.limit("10/minute")
async def admin_reports_summary(request: Request, days: int = 30, _=require_tier("pro")) -> JSONResponse:
    """Get aggregated summary stats for the last N days."""
    await require_admin(request)
    team_id = config.license_team_id
    stats = get_summary_stats(team_id, days)
    return JSONResponse(stats)


@app.get("/admin/reports/export")
@limiter.limit("5/minute")
async def admin_reports_export(
    request: Request,
    _=require_tier("pro"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Response:
    """Export stats as CSV."""
    await require_admin(request)
    team_id = config.license_team_id
    csv_data = export_report_csv(team_id, start_date, end_date)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=privacy_gateway_report.csv"},
    )


# ==================== Alert Engine API ====================

@app.get("/admin/alerts/status")
@limiter.limit("10/minute")
async def admin_alerts_status(request: Request, _=require_tier("enterprise")) -> JSONResponse:
    """Get alert engine status."""
    await require_admin(request)
    engine = get_alert_engine()
    return JSONResponse({
        "rules_count": len(engine.rules),
        "rules": [{"name": r.name, "condition": r.condition, "actions": r.actions} for r in engine.rules],
    })


@app.post("/admin/alerts/test")
@limiter.limit("5/minute")
async def admin_alerts_test(request: Request, _=require_tier("enterprise")) -> JSONResponse:
    """Test alert notifications by triggering a sample alert."""
    await require_admin(request)
    engine = get_alert_engine()
    context = {
        "stats": {"5min": 15000},
        "license": {"expires_in": 3},
    }
    triggered = await engine.process(context)
    return JSONResponse({
        "triggered": len(triggered),
        "alerts": triggered,
    })


# ==================== Cache Status API ====================

@app.get("/admin/cache/status")
@limiter.limit("10/minute")
async def admin_cache_status(request: Request) -> JSONResponse:
    """Get cache (Redis) status."""
    await require_admin(request)
    cache = get_redis_cache()
    healthy = await cache.health_check() if cache.available else False
    return JSONResponse({
        "available": cache.available,
        "healthy": healthy,
        "type": "redis" if cache.available else "none",
    })


# ==================== Team Management API ====================

@app.get("/admin/team")
@limiter.limit("10/minute")
async def admin_team(request: Request) -> JSONResponse:
    """Get team info and member list (requires admin auth)."""
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team associated with this license")
    team = get_team(team_id)
    if not team:
        team = create_team(team_id[:16] if team_id else "Default Team", license_id=None)
    members = get_team_members(team_id)
    return JSONResponse({
        "team": team, "members": members,
        "member_count": get_member_count(team_id),
        "seat_limit": config.license_seats,
        "settings": get_team_settings(team_id),
    })


@app.post("/admin/team/members")
@limiter.limit("10/minute")
async def admin_team_add_member(request: Request, _=require_tier("pro")) -> JSONResponse:
    """Add a new team member (admin only)."""
    await require_admin(request)
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "member")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team associated. Activate a license first.")
    try:
        user = create_user(team_id, username, password, role)
        db.log_audit(None, "member_added", {"user_id": user["id"], "team_id": team_id})
        return JSONResponse({"status": "ok", "user": user})
    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/admin/team/members/{user_id}")
@limiter.limit("10/minute")
async def admin_team_remove_member(user_id: str, request: Request, _=require_tier("pro")) -> JSONResponse:
    """Remove a team member (admin only)."""
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    if remove_user(team_id, user_id):
        db.log_audit(None, "member_removed", {"user_id": user_id, "team_id": team_id})
        return JSONResponse({"status": "ok", "message": "Member removed"})
    raise HTTPException(status_code=404, detail="Member not found")


@app.put("/admin/team/members/{user_id}/role")
@limiter.limit("10/minute")
async def admin_team_update_role(user_id: str, request: Request, _=require_tier("pro")) -> JSONResponse:
    """Update a member role (admin only)."""
    await require_admin(request)
    body = await request.json()
    role = body.get("role", "").strip()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    if update_user_role(team_id, user_id, role):
        db.log_audit(None, "member_role_updated", {"user_id": user_id, "role": role})
        return JSONResponse({"status": "ok", "message": f"Role updated to {role}"})
    raise HTTPException(status_code=404, detail="Member not found")


@app.post("/admin/team/members/{user_id}/reset-api-key")
@limiter.limit("5/minute")
async def admin_team_reset_api_key(user_id: str, request: Request) -> JSONResponse:
    """Regenerate a member API key (admin only)."""
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    new_key = regenerate_api_key(user_id, team_id)
    if new_key:
        db.log_audit(None, "api_key_reset", {"user_id": user_id})
        return JSONResponse({"status": "ok", "api_key": new_key})
    raise HTTPException(status_code=404, detail="Member not found")


@app.get("/admin/team/settings")
@limiter.limit("10/minute")
async def admin_team_get_settings(request: Request) -> JSONResponse:
    """Get team settings (admin only)."""
    await require_admin(request)
    team_id = config.license_team_id
    if not team_id:
        return JSONResponse({})
    return JSONResponse(get_team_settings(team_id))


@app.put("/admin/team/settings")
@limiter.limit("10/minute")
async def admin_team_update_settings(request: Request) -> JSONResponse:
    """Update team settings (admin only)."""
    await require_admin(request)
    body = await request.json()
    team_id = config.license_team_id
    if not team_id:
        raise HTTPException(status_code=400, detail="No team configured")
    update_team_settings(team_id, body)
    db.log_audit(None, "team_settings_updated", {"team_id": team_id})
    return JSONResponse({"status": "ok", "message": "Settings updated"})


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    logger.info("AI隐私网关启动")
    logger.info(f"监听端口: {config.LISTEN_PORT}")
    logger.info(f"目标AI服务: {config.TARGET_LLM}")
    logger.info(f"数据库: {config.DB_PATH}")

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 — gateway intentionally binds all interfaces
        port=config.LISTEN_PORT,
        log_level="info"
    )
