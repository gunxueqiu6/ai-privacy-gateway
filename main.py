"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from jose import JWTError, jwt
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

def filter_proxy_headers(headers: dict) -> dict:
    return {k: v for k, v in headers.items() if k.lower() in ALLOWED_PROXY_HEADERS}

# Token 黑名单 (登出后失效)
_token_blacklist: set = set()


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


# ==================== 主代理路由 ====================

@app.post("/v1/chat/completions")
@limiter.limit("60/minute")
async def chat_completions(request: Request):
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()

    body = await request.json()

    # 验证客户端 Authorization 头
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return JSONResponse(status_code=401, content={"error": "未授权 - 需要 API Key"})

    # 上行脱敏
    masked_body, mappings, stats, session_id, used_placeholders = gateway.mask_request(body)

    # 保存映射到数据库
    if mappings:
        db.save_mappings(session_id, mappings)
        db.update_stats(stats)

    headers = filter_proxy_headers(request.headers)

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
async def proxy_v1(request: Request, path: str):
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

    method = request.method
    headers = filter_proxy_headers(request.headers)
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
async def api_get_entities(request: Request):
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
async def root():
    """根路由 - 健康检查"""
    return {
        "status": "healthy",
        "service": "AI隐私网关",
        "version": "Lite"
    }


@app.get("/health")
async def health():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(request: Request):
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
async def admin_logout(request: Request):
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
async def get_version(request: Request):
    """获取版本信息"""
    await require_admin(request)

    return {
        "version": "2.0",
        "version_type": "Lite (Open Core)",
        "version_display": "Lite",
        "target_llm": config.TARGET_LLM
    }


@app.get("/admin/integrity")
@limiter.limit("10/minute")
async def check_integrity(request: Request):
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
async def clear_mappings(request: Request):
    """清除所有映射记录 - 需要认证"""
    await require_admin(request)

    db.clear_all_mappings()
    return {"status": "ok", "message": "所有映射记录已清除"}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    logger.info("AI隐私网关启动")
    logger.info(f"监听端口: {config.LISTEN_PORT}")
    logger.info(f"目标AI服务: {config.TARGET_LLM}")
    logger.info(f"数据库: {config.DB_PATH}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.LISTEN_PORT,
        log_level="info"
    )
