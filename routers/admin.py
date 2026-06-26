"""Admin panel routes — login, stats, keywords, version, integrity checks, audit stream,
vault backup/restore, dry-run toggle."""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Request, Response
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

    response = JSONResponse({"status": "ok", "message": "登录成功"})
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
        "version": "2.0.0",
        "tier": config.tier,
        "target_llm": config.TARGET_LLM,
    }


@router.get("/admin/integrity")
@limiter.limit("10/minute")
async def check_integrity(request: Request) -> dict:
    """完整性检查"""
    await require_admin(request)

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


# ==================== Vault Backup & Recovery ====================


@router.get("/admin/vault/integrity")
@limiter.limit("10/minute")
async def vault_integrity(request: Request) -> dict:
    """Vault 数据库完整性检查 - 需要认证"""
    await require_admin(request)

    result = db.check_integrity()
    return {"status": "ok" if result else "error", "integrity_ok": result}


@router.post("/admin/vault/backup")
@limiter.limit("5/minute")
async def vault_backup(request: Request) -> dict:
    """备份 Vault 数据库 - 需要认证"""
    await require_admin(request)

    backup_dir = os.path.join(os.path.dirname(config.DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"vault_backup_{timestamp}.db")

    size = db.backup_vault(backup_path)
    db.log_audit(None, "vault_backup", {"path": backup_path, "size": size})
    logger.info("管理员触发 Vault 备份: %s (%d 字节)", backup_path, size)
    return {"status": "ok", "path": backup_path, "size": size}


@router.post("/admin/vault/restore")
@limiter.limit("3/minute")
async def vault_restore(request: Request):
    """从备份文件恢复 Vault 数据库 - 需要认证"""
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    backup_path = (body.get("path") or "").strip()
    force = body.get("force", False)

    if not backup_path:
        return JSONResponse(status_code=400, content={"error": "备份路径不能为空"})
    if not os.path.exists(backup_path):
        return JSONResponse(status_code=404, content={"error": "备份文件不存在"})

    try:
        db.restore_vault(backup_path, force=bool(force))
        db.log_audit(None, "vault_restore", {"path": backup_path})
        logger.info("管理员从 %s 恢复 Vault", backup_path)
        return {"status": "ok", "message": "Vault 恢复成功"}
    except (ValueError, RuntimeError) as e:
        logger.error("Vault 恢复失败: %s", e)
        return JSONResponse(status_code=400, content={"error": str(e)})


# ==================== Dry-Run Mode ====================


@router.post("/admin/dry-run/toggle")
@limiter.limit("10/minute")
async def toggle_dry_run(request: Request):
    """启用/禁用 Dry-Run 模式 - 需要认证"""
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    enable = body.get("enable", not config.DRY_RUN_MODE)
    config.DRY_RUN_MODE = bool(enable)

    status_text = "启用" if config.DRY_RUN_MODE else "禁用"
    logger.info("管理员%s Dry-Run 模式", status_text)
    db.log_audit(None, "dry_run_toggle", {"dry_run": config.DRY_RUN_MODE})
    return {"status": "ok", "dry_run": config.DRY_RUN_MODE, "message": f"Dry-Run 模式已{status_text}"}


# ==================== Config Hot-Reload ====================


def _sanitize_config() -> dict:
    """Return non-sensitive configuration fields (exclude passwords, keys)."""
    return {
        "listen_port": config.LISTEN_PORT,
        "target_llm": config.TARGET_LLM,
        "upstream_llm_urls": config.UPSTREAM_LLM_URLS,
        "upstream_lb_strategy": config.UPSTREAM_LB_STRATEGY,
        "upstream_health_check_interval": config.UPSTREAM_HEALTH_CHECK_INTERVAL,
        "db_path": config.DB_PATH,
        "db_type": config.DB_TYPE,
        "mask_engine_type": config.MASK_ENGINE_TYPE,
        "mapping_ttl": config.MAPPING_TTL,
        "stateless_mode": config.STATELESS_MODE,
        "max_concurrent_requests": config.MAX_CONCURRENT_REQUESTS,
        "tier": config.tier,
    }


@router.post("/admin/config/reload")
@limiter.limit("5/minute")
async def config_reload(request: Request) -> dict:
    """Reload configuration from environment variables — requires admin auth.

    Re-reads .env / environment, updates Config singleton, GatewayCore's
    timeout/retry settings, and the LoadBalancer's upstream list/strategy.
    Returns sanitized config (no secrets).
    """
    await require_admin(request)
    logger.info("管理员触发热重载配置")

    config.reload()

    from gateway_core import get_gateway_core
    core = get_gateway_core()
    await core.reload_config()

    return _sanitize_config()


# ==================== Historical Stats ====================


@router.get("/admin/stats/history")
@limiter.limit("10/minute")
async def get_stats_history(
    request: Request,
    from_date: Optional[str] = Query(default=None, description="起始日期 YYYY-MM-DD"),
    to_date: Optional[str] = Query(default=None, description="结束日期 YYYY-MM-DD"),
) -> dict:
    """Get historical daily stats for a date range — requires admin auth.

    Defaults to the last 7 days if neither date is provided.
    Returns daily aggregates: total_requests, total_tokens, pii_detected, etc.
    """
    await require_admin(request)

    if not from_date:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    records = db.get_stats_range(from_date, to_date)

    summary = {}
    if records:
        for col in ("phone", "email", "idcard", "bankcard", "custom",
                     "person", "location", "org", "plate", "ip",
                     "url", "date", "amount", "postcode", "total"):
            summary[col] = sum(r.get(f"{col}_count", 0) for r in records)

    return {
        "from": from_date,
        "to": to_date,
        "records": records,
        "total_days": len(records),
        "summary": summary,
    }


# ==================== Rules Import/Export ====================


@router.get("/admin/rules/export")
@limiter.limit("10/minute")
async def export_rules(request: Request) -> dict:
    """Export all custom keywords and regex rules — requires admin auth."""
    await require_admin(request)

    engine = get_mask_engine()
    keywords = engine.get_custom_keywords()

    rules = db.get_custom_regex_rules()
    regex_rules = [
        {
            "name": r["name"],
            "pattern": r["pattern"],
            "entity_type": r["entity_type"],
        }
        for r in rules
    ]

    return {"keywords": keywords, "regex_rules": regex_rules}


@router.post("/admin/rules/import")
@limiter.limit("10/minute")
async def import_rules(request: Request) -> dict:
    """Bulk-import custom keywords and regex rules — requires admin auth.

    Accepts the same JSON format as /admin/rules/export returns:
        {"keywords": [...], "regex_rules": [{"name": "...", "pattern": "...", "entity_type": "..."}]}
    Skips duplicates. Returns count of imported items.
    """
    await require_admin(request)

    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE

    keywords = body.get("keywords", [])
    regex_rules = body.get("regex_rules", [])

    if not isinstance(keywords, list) or not isinstance(regex_rules, list):
        return JSONResponse(
            status_code=400,
            content={"error": "无效的格式：keywords 和 regex_rules 应为数组"},
        )

    engine = get_mask_engine()
    imported_count = 0
    errors: List[str] = []

    for kw in keywords:
        if not isinstance(kw, str) or not kw.strip():
            continue
        if engine.add_custom_keyword(kw.strip()):
            db.add_custom_keyword(kw.strip())
            imported_count += 1

    for rule in regex_rules:
        name = (rule.get("name") or "").strip()
        pattern = (rule.get("pattern") or "").strip()
        entity_type = (rule.get("entity_type") or "").strip().lower()

        if not name or not pattern:
            errors.append("跳过无效规则（名称或正则缺失）")
            continue
        if entity_type not in KNOWN_ENTITY_TYPES:
            errors.append(f"跳过规则 '{name}': 未知实体类型 '{entity_type}'")
            continue

        try:
            re.compile(pattern)
        except re.error as e:
            errors.append(f"跳过规则 '{name}': 无效正则 — {e}")
            continue

        rule_id = db.add_custom_regex_rule(name, pattern, entity_type)
        if rule_id == -1:
            continue  # duplicate name, skip gracefully

        try:
            engine.add_custom_regex_rule(name, pattern, entity_type)
            imported_count += 1
        except (ValueError, re.error) as e:
            db.delete_custom_regex_rule(rule_id)
            errors.append(f"引擎添加规则 '{name}' 失败: {e}")

    logger.info(f"管理员导入规则: {imported_count} 条成功, {len(errors)} 条错误")
    return {
        "status": "ok",
        "imported": imported_count,
        "errors": errors if errors else None,
        "message": f"成功导入 {imported_count} 条规则",
    }
