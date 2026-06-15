"""Admin panel routes — login, stats, keywords, version, integrity checks."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .dependencies import (
    _token_blacklist,
    create_jwt_token,
    get_current_user_token,
    limiter,
    require_admin,
)
from config import config
from database import db
from mask_engine import get_mask_engine

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

    body = await request.json()
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


@router.post("/admin/keywords/delete")
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


@router.get("/admin/version")
@limiter.limit("10/minute")
async def get_version(request: Request) -> dict:
    """Get version info."""
    await require_admin(request)

    return {
        "version": "2.0",
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
