"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import config, get_config
from database import db
from gateway_core import get_gateway_core
try:
    from integrity_checker import get_integrity_checker, start_integrity_checker
    _has_integrity_checker = True
except ImportError:
    _has_integrity_checker = False
    def get_integrity_checker():
        raise NotImplementedError("integrity_checker not available in Lite")
    def start_integrity_checker(app_dir=None):
        pass
from mask_engine import get_mask_engine
from rbac import get_rbac_manager, Permission
from audit_log import get_audit_logger
from alert_manager import get_alert_manager
from decay_manager import get_decay_manager

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

# 速率限制
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# RBAC 管理器
rbac = get_rbac_manager()

# 全局映射缓存
_mappings_cache: Dict[str, str] = {}
_cache_lock = asyncio.Lock()


# ==================== 衰减中间件 ====================

@app.middleware("http")
async def decay_middleware(request: Request, call_next):
    """衰减中间件 — 检查 License 验证状态并注入衰减行为"""
    decay = get_decay_manager()
    level = decay.update()

    if decay.should_shutdown():
        return JSONResponse(
            status_code=503,
            content={"error": "Service shut down due to license expiration"}
        )

    if decay.should_drop_request():
        return JSONResponse(
            status_code=503,
            content={"error": "Service degraded, please try again later"}
        )

    response = await call_next(request)

    # 注入衰减警告头
    warning_msg = decay.get_warning_message()
    if warning_msg:
        response.headers["X-Decay-Level"] = str(level.value)
        response.headers["X-Decay-Warning"] = warning_msg

    return response


# ==================== 认证依赖 ====================

async def get_current_user_token(request: Request) -> Optional[str]:
    """从请求中获取用户令牌"""
    # 从 Authorization header 获取
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    # 从 cookie 获取
    return request.cookies.get("session_token")


async def require_admin(request: Request) -> str:
    """要求管理员权限"""
    token = await get_current_user_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="未授权 - 需要登录")
    
    user = rbac.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="会话已过期或无效")
    
    return token


async def require_permission(permission: Permission):
    """要求特定权限"""
    def dependency(request: Request):
        token = get_current_user_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="未授权")
        
        if not rbac.check_permission(token, permission):
            raise HTTPException(status_code=403, detail="权限不足")
        return token
    return dependency


async def refresh_cache():
    """刷新映射缓存"""
    global _mappings_cache
    async with _cache_lock:
        _mappings_cache = db.get_all_mappings()


# ==================== 主代理路由 ====================

@app.post("/v1/chat/completions")
@limiter.limit("60/minute")
async def chat_completions(request: Request):
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()

    body = await request.json()

    # 获取用户上下文
    user_id = None
    token = await get_current_user_token(request)
    if token:
        user = rbac.get_user_by_token(token)
        if user:
            user_id = user.get("username")

    # 上行脱敏
    masked_body, mappings, stats, session_id = gateway.mask_request(
        body,
        user_id=user_id,
        ip_address=request.client.host if request.client else None
    )

    # 保存映射到数据库
    if mappings:
        db.save_mappings(session_id, mappings)
        db.update_stats(stats)
        asyncio.create_task(refresh_cache())

    headers = dict(request.headers)

    # 判断是否流式请求
    if body.get("stream", False):
        # 流式响应
        async def generate():
            async for chunk in gateway.proxy_stream_request(masked_body, headers, mappings):
                yield chunk

        return EventSourceResponse(generate())
    else:
        # 非流式响应
        status_code, resp_body, resp_headers = await gateway.proxy_request(masked_body, headers, mappings)

        # 还原响应内容
        if isinstance(resp_body, bytes):
            try:
                resp_json = json.loads(resp_body)
                if "choices" in resp_json:
                    for choice in resp_json["choices"]:
                        if "message" in choice:
                            choice["message"]["content"] = gateway.unmask_response(
                                choice["message"]["content"], mappings, session_id
                            )
                    resp_body = json.dumps(resp_json).encode()
            except json.JSONDecodeError:
                pass

        return Response(
            content=resp_body,
            status_code=status_code,
            headers={"Content-Type": resp_headers.get("content-type", "application/json")}
        )


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v1(request: Request, path: str):
    """通用 v1 路由代理"""
    gateway = get_gateway_core()

    method = request.method
    headers = dict(request.headers)
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
    
    engine = get_mask_engine()
    masked_text, mappings, stats = engine.mask(text)

    # 审计日志
    if config.feature_audit_log:
        audit = get_audit_logger()
        audit.log_mask_action(
            session_id=f"api_{int(time.time() * 1000)}",
            original_content=text,
            masked_content=masked_text,
            mappings=mappings,
            stats=stats,
            ip_address=request.client.host if request.client else None
        )

    # 高频告警
    total_count = sum(stats.values())
    if total_count >= 100:
        alert = get_alert_manager()
        alert.check_high_frequency("api_direct", total_count)

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
async def api_get_entities(request: Request):
    """获取支持的实体类型列表"""
    entities = [
        {"type": "PII_PHONE", "name": "手机号", "description": "中国大陆手机号", "enabled": True},
        {"type": "PII_EMAIL", "name": "邮箱", "description": "电子邮箱地址", "enabled": True},
        {"type": "PII_IDCARD", "name": "身份证", "description": "中国身份证号码", "enabled": True},
        {"type": "PII_BANK", "name": "银行卡", "description": "银行卡号码", "enabled": True},
        {"type": "PII_PER", "name": "人名", "description": "中文人名", "enabled": True},
        {"type": "PII_LOC", "name": "地名", "description": "省份、城市、区县等", "enabled": True},
        {"type": "PII_ORG", "name": "机构名", "description": "公司、组织名称", "enabled": False},
        {"type": "PII_PLATE", "name": "车牌号", "description": "中国车牌号", "enabled": False},
        {"type": "PII_IP", "name": "IP地址", "description": "IPv4 地址", "enabled": False},
        {"type": "PII_URL", "name": "URL", "description": "网址链接", "enabled": False},
        {"type": "PII_DATE", "name": "日期", "description": "日期格式", "enabled": False},
        {"type": "PII_AMOUNT", "name": "金额", "description": "货币金额", "enabled": False},
        {"type": "PII_POSTCODE", "name": "邮编", "description": "邮政编码", "enabled": False},
        {"type": "PII_CUST", "name": "自定义", "description": "自定义敏感词", "enabled": True},
    ]
    
    return {
        "entities": entities,
        "total": len(entities),
        "version": config.get_version_display()
    }


# ==================== 管理后台 API ====================

@app.get("/")
async def root():
    """根路由 - 健康检查"""
    return {
        "status": "healthy",
        "service": "AI隐私网关",
        "version": config.get_version_display(),
        "license": config.LICENSE_KEY[:8] + "..." if len(config.LICENSE_KEY) > 8 else config.LICENSE_KEY
    }


@app.get("/health")
async def health():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(request: Request):
    """管理员登录"""
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    
    token = rbac.authenticate(username, password)
    if token:
        response = JSONResponse({"status": "ok", "token": token, "message": "登录成功"})
        response.set_cookie(key="session_token", value=token, httponly=True, secure=False)
        return response
    
    raise HTTPException(status_code=401, detail="用户名或密码错误")


@app.post("/admin/logout")
@limiter.limit("10/minute")
async def admin_logout(request: Request):
    """管理员登出"""
    token = await get_current_user_token(request)
    if token:
        rbac.logout(token)
    
    response = JSONResponse({"status": "ok", "message": "登出成功"})
    response.delete_cookie(key="session_token")
    return response


@app.get("/admin/stats")
@limiter.limit("10/minute")
async def get_stats(request: Request, date: str = None):
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
async def list_keywords(request: Request):
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


@app.post("/admin/clear")
@limiter.limit("10/minute")
async def clear_mappings(request: Request):
    """清除所有映射记录 - 需要认证"""
    await require_admin(request)
    
    db.clear_all_mappings()
    return {"status": "ok", "message": "所有映射记录已清除"}


@app.get("/admin/version")
@limiter.limit("10/minute")
async def get_version_info(request: Request):
    """获取版本信息 - 需要认证"""
    await require_admin(request)
    
    return {
        "version": config.VERSION,
        "version_type": config.VERSION_TYPE.value,
        "version_display": config.get_version_display(),
        "features": {
            "team_dashboard": config.feature_team_dashboard,
            "concurrent_wal": config.feature_concurrent_wal,
            "redis_storage": config.feature_redis_storage,
            "ac_automaton": config.feature_ac_automaton,
            "audit_log": config.feature_audit_log,
            "cloud_rules": config.feature_cloud_rules,
            "license_verify": config.feature_license_verify
        }
    }


@app.get("/admin/integrity")
@limiter.limit("10/minute")
async def get_integrity_status(request: Request):
    """获取运行时完整性检查状态 - 需要认证"""
    await require_admin(request)
    
    if not _has_integrity_checker:
        return {"available": False, "message": "完整性检查仅在 Pro/Enterprise 版可用"}
    checker = get_integrity_checker()
    last = checker.last_result
    return {
        "available": checker.is_available,
        "last_result": last,
        "anomaly_count": checker._anomaly_count
    }


@app.get("/admin/users")
@limiter.limit("10/minute")
async def list_users(request: Request):
    """列出所有用户 - 需要认证"""
    await require_admin(request)
    
    return {"users": rbac.list_users()}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"AI隐私网关启动")
    logger.info(f"版本: {config.get_version_display()}")
    logger.info(f"监听端口: {config.LISTEN_PORT}")
    logger.info(f"目标AI服务: {config.TARGET_LLM}")
    logger.info(f"数据库: {config.DB_PATH}")

    # 启动运行时完整性检查（仅 Pro/Enterprise）
    if _has_integrity_checker:
        start_integrity_checker()
    else:
        logger.info("完整性检查模块未加载（Lite 版跳过）")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.LISTEN_PORT,
        log_level="info"
    )