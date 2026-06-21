"""Admin panel routes — login, stats, keywords, version, integrity checks, audit stream."""

import asyncio
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from .dependencies import (
    BAD_ENCODING_RESPONSE,
    _token_blacklist,
    create_jwt_token,
    get_current_user_token,
    limiter,
    require_admin,
    safe_json,
)
from config import config
from database import db
from gateway_core import get_gateway_core
from mask_engine import get_mask_engine, KNOWN_ENTITY_TYPES

import bcrypt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ==================== Admin Auth ====================


@router.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(request: Request) -> JSONResponse:
    """管理员登录"""
    client_ip = request.client.host if request.client else "unknown"

    is_locked, remaining = db.check_login_attempt(client_ip)
    if is_locked:
        raise HTTPException(status_code=429, detail="登录尝试次数过多，请稍后再试")

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    password = body.get("password", "")

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

    db.record_login_attempt(client_ip, success=True)
    db.log_audit(None, "admin_login", {"ip": client_ip})

    token = create_jwt_token()

    response = JSONResponse({"status": "ok", "message": "登录成功", "token": token})
    response.set_cookie(key="session_token", value=token, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=86400)
    return response


@router.post("/admin/logout")
@limiter.limit("10/minute")
async def admin_logout(request: Request) -> JSONResponse:
    """管理员登出"""
    client_ip = request.client.host if request.client else "unknown"

    token = await get_current_user_token(request)
    if token:
        _token_blacklist.add(token)

    db.log_audit(None, "admin_logout", {"ip": client_ip})

    response = JSONResponse({"status": "ok", "message": "登出成功"})
    response.delete_cookie(key="session_token")
    return response


# ==================== Stats & Keywords ====================


@router.get("/admin/stats")
@limiter.limit("10/minute")
async def get_stats(request: Request, date: Optional[str] = None) -> dict:
    """获取统计信息 - 需要认证"""
    await require_admin(request)

    stats = db.get_today_stats()
    return stats


@router.get("/admin/keywords")
@limiter.limit("10/minute")
async def list_keywords(request: Request) -> dict:
    """获取自定义敏感词列表 - 需要认证"""
    await require_admin(request)

    engine = get_mask_engine()
    return {"keywords": engine.get_custom_keywords()}


@router.post("/admin/keywords/add")
@limiter.limit("10/minute")
async def add_keyword(request: Request):
    """添加自定义敏感词 - 需要认证"""
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
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


@router.post("/admin/keywords/delete")
@limiter.limit("10/minute")
async def delete_keyword(request: Request):
    """删除自定义敏感词 - 需要认证"""
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    keyword = body.get("keyword", "").strip()

    if not keyword:
        return JSONResponse(status_code=400, content={"error": "关键词不能为空"})

    engine = get_mask_engine()
    if engine.remove_custom_keyword(keyword):
        db.delete_custom_keyword(keyword)
        return {"status": "ok", "message": f"关键词 '{keyword}' 已删除"}

    return JSONResponse(status_code=404, content={"error": "关键词不存在"})


@router.get("/admin/upstreams")
@limiter.limit("10/minute")
async def get_upstreams(request: Request) -> dict:
    """获取上游节点健康状态 - 需要认证"""
    await require_admin(request)

    core = get_gateway_core()
    stats = core.load_balancer.get_stats()
    return {
        "strategy": config.UPSTREAM_LB_STRATEGY,
        "nodes": stats,
    }


@router.get("/admin/version")
@limiter.limit("10/minute")
async def get_version(request: Request) -> dict:
    """Get version info."""
    await require_admin(request)

    return {
        "version": "1.1.0",
        "tier": config.tier,
        "target_llm": config.TARGET_LLM,
    }


@router.get("/admin/integrity")
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


@router.post("/admin/clear")
@limiter.limit("10/minute")
async def clear_mappings(request: Request) -> dict:
    """清除所有映射记录 - 需要认证"""
    await require_admin(request)

    db.clear_all_mappings()
    return {"status": "ok", "message": "所有映射记录已清除"}


@router.get("/admin/audit/stream")
async def audit_stream():
    """实时审计事件流 (SSE)"""
    from audit import audit_bus

    async def event_generator():
        q = audit_bus.subscribe()
        try:
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            audit_bus.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ==================== Admin Custom Regex Rules ====================


@router.get("/admin/regex-rules")
@limiter.limit("10/minute")
async def admin_list_regex_rules(request: Request) -> dict:
    """获取所有自定义正则规则 - 需要认证"""
    await require_admin(request)

    rules = db.get_custom_regex_rules()
    return {"rules": rules, "total": len(rules)}


@router.post("/admin/regex-rules")
@limiter.limit("10/minute")
async def admin_add_regex_rule(request: Request):
    """添加自定义正则规则 - 需要认证"""
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE

    name = (body.get("name") or "").strip()
    pattern = (body.get("pattern") or "").strip()
    entity_type = (body.get("entity_type") or "").strip().lower()

    if not name:
        return JSONResponse(status_code=400, content={"error": "规则名称不能为空"})
    if len(name) > 100:
        return JSONResponse(status_code=400, content={"error": "规则名称不能超过 100 个字符"})
    if not pattern:
        return JSONResponse(status_code=400, content={"error": "正则表达式不能为空"})
    if entity_type not in KNOWN_ENTITY_TYPES:
        return JSONResponse(status_code=400, content={"error": f"未知实体类型: {entity_type}，支持的实体类型: {', '.join(sorted(KNOWN_ENTITY_TYPES))}"})

    try:
        re.compile(pattern)
    except re.error as e:
        return JSONResponse(status_code=400, content={"error": f"无效的正则表达式: {e}"})

    rule_id = db.add_custom_regex_rule(name, pattern, entity_type)
    if rule_id == -1:
        return JSONResponse(status_code=409, content={"error": f"规则名称 '{name}' 已存在"})

    engine = get_mask_engine()
    try:
        engine.add_custom_regex_rule(name, pattern, entity_type)
    except (ValueError, re.error) as e:
        db.delete_custom_regex_rule(rule_id)
        return JSONResponse(status_code=500, content={"error": f"引擎添加规则失败: {e}"})

    logger.info(f"管理员添加自定义正则规则: {name} (type={entity_type})")
    return {"status": "ok", "id": rule_id, "message": f"规则 '{name}' 已添加"}


@router.delete("/admin/regex-rules/{rule_id}")
@limiter.limit("10/minute")
async def admin_delete_regex_rule(request: Request, rule_id: int):
    """删除自定义正则规则 - 需要认证"""
    await require_admin(request)

    rules = db.get_custom_regex_rules()
    target = next((r for r in rules if r["id"] == rule_id), None)
    if target is None:
        return JSONResponse(status_code=404, content={"error": f"规则 ID {rule_id} 不存在"})

    if not db.delete_custom_regex_rule(rule_id):
        return JSONResponse(status_code=500, content={"error": "数据库删除失败"})

    engine = get_mask_engine()
    engine.remove_custom_regex_rule(target["name"])

    logger.info(f"管理员删除自定义正则规则: {target['name']} (id={rule_id})")
    return {"status": "ok", "message": f"规则 '{target['name']}' 已删除"}


@router.put("/admin/regex-rules/{rule_id}/toggle")
@limiter.limit("10/minute")
async def admin_toggle_regex_rule(request: Request, rule_id: int):
    """启用/禁用自定义正则规则 - 需要认证"""
    await require_admin(request)

    rules = db.get_custom_regex_rules()
    target = next((r for r in rules if r["id"] == rule_id), None)
    if target is None:
        return JSONResponse(status_code=404, content={"error": f"规则 ID {rule_id} 不存在"})

    new_enabled = not target["enabled"]

    if not db.toggle_custom_regex_rule(rule_id, new_enabled):
        return JSONResponse(status_code=500, content={"error": "数据库更新失败"})

    engine = get_mask_engine()
    engine.toggle_custom_regex_rule(target["name"], new_enabled)

    status_text = "启用" if new_enabled else "禁用"
    logger.info(f"管理员{status_text}自定义正则规则: {target['name']} (id={rule_id})")
    return {"status": "ok", "id": rule_id, "enabled": new_enabled, "message": f"规则 '{target['name']}' 已{status_text}"}
