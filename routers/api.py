"""
独立 API 路由 — 脱敏/还原/批量/实体类型查询。
"""

import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from mask_engine import get_mask_engine, HAS_NER, placeholder_to_token
from database import db, STATS_ENTITY_COLUMNS

from .dependencies import safe_json, BAD_ENCODING_RESPONSE, limiter
from .auth import verify_api_key

api_router = APIRouter(tags=["api"])


def _entity_type_from_placeholder(placeholder: str) -> str:
    return placeholder_to_token(placeholder)


@api_router.post("/api/mask")
@limiter.limit("60/minute")
async def api_mask(request: Request):
    """独立脱敏 API"""
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    text = body.get("text", "")
    custom_keywords = body.get("custom_keywords", [])

    if not text:
        return JSONResponse(status_code=400, content={"error": "text 参数不能为空"})
    if len(text) > 102400:
        return JSONResponse(
            status_code=413, content={"error": "输入文本过长，最大支持 100KB"}
        )

    engine = get_mask_engine()

    # Temporarily inject custom keywords from the request into the engine
    added = []
    if isinstance(custom_keywords, list):
        for kw in custom_keywords:
            if isinstance(kw, str) and kw.strip():
                kw = kw.strip()
                if engine.add_custom_keyword(kw):
                    added.append(kw)

    try:
        masked_text, mappings, stats = engine.mask(text)
    finally:
        # Remove temporarily added keywords to keep engine state clean
        for kw in added:
            engine.remove_custom_keyword(kw)

    entities = []
    for placeholder, value in mappings.items():
        entities.append(
            {
                "type": _entity_type_from_placeholder(placeholder),
                "value": value,
                "placeholder": placeholder,
                "position": text.find(value),
            }
        )

    return {"masked_text": masked_text, "entities": entities, "stats": stats}


@api_router.post("/api/restore")
async def api_restore(request: Request):
    """独立还原 API"""
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    masked_text = body.get("text", "")
    mappings = body.get("mappings", {})

    if not masked_text:
        return JSONResponse(status_code=400, content={"error": "text 参数不能为空"})
    if len(masked_text) > 102400:
        return JSONResponse(
            status_code=413, content={"error": "输入文本过长，最大支持 100KB"}
        )

    engine = get_mask_engine()
    original_text = engine.unmask(masked_text, mappings)
    return {"original_text": original_text}


@api_router.post("/api/mask/batch")
async def api_mask_batch(request: Request):
    """批量脱敏 API"""
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    texts = body.get("texts", [])

    if not isinstance(texts, list) or len(texts) == 0:
        return JSONResponse(status_code=400, content={"error": "texts 必须是非空数组"})
    if len(texts) > 50:
        return JSONResponse(
            status_code=400, content={"error": "单次批量处理最多 50 条"}
        )

    for i, t in enumerate(texts):
        if len(t) > 102400:
            return JSONResponse(
                status_code=413,
                content={"error": f"第 {i+1} 条文本过长，最大支持 100KB"},
            )

    engine = get_mask_engine()
    results = []
    for text in texts:
        masked_text, mappings, stats = engine.mask(text)
        entities = [
            {
                "type": _entity_type_from_placeholder(p),
                "value": v,
                "placeholder": p,
                "position": text.find(v),
            }
            for p, v in mappings.items()
        ]
        results.append(
            {
                "original": text,
                "masked": masked_text,
                "entities": entities,
                "stats": stats,
            }
        )

    return {"results": results, "total_count": len(results)}


@api_router.get("/api/entities")
async def api_get_entities(request: Request) -> dict:
    """获取支持的实体类型列表（数据驱动）"""
    engine = get_mask_engine()
    entities = engine.get_entity_catalog()
    return {
        "entities": entities,
        "total": len(entities),
        "version": "Lite",
        "ner_available": HAS_NER,
    }


# ==================== 用户可见性仪表盘 ====================

STATS_TYPE_KEYS = [f"{c}_count" for c in STATS_ENTITY_COLUMNS]


def _strip_count_suffix(stats_row: dict) -> dict:
    """将 phone_count → phone 等映射，返回简洁键名的类型统计。"""
    types = {}
    for key in STATS_TYPE_KEYS:
        val = stats_row.get(key, 0) or 0
        if val > 0:
            types[key.replace("_count", "")] = val
    return types


@api_router.get("/api/me/stats")
@limiter.limit("30/minute")
async def me_stats(request: Request, api_key: dict = Depends(verify_api_key)):
    """当前用户的脱敏统计（今日 + 本周）。"""
    team_id = api_key["team_id"]
    today = db.get_stats_by_team_today(team_id)

    today_data = {"total": 0, "types": {}}
    if today:
        today_data["total"] = today.get("total_count", 0) or 0
        today_data["types"] = _strip_count_suffix(today)

    sessions = db.get_user_sessions(team_id, limit=1000, offset=0)
    week_total = sum(s.get("masked_count", 0) or 0 for s in sessions)

    return {"today": today_data, "week": {"total": week_total}}


@api_router.get("/api/me/history")
@limiter.limit("30/minute")
async def me_history(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    api_key: dict = Depends(verify_api_key),
):
    """当前用户的脱敏历史（分页）。"""
    team_id = api_key["team_id"]
    offset = (page - 1) * limit
    sessions = db.get_user_sessions(team_id, limit=limit, offset=offset)
    total = db.get_user_sessions_count(team_id)

    items = []
    for s in sessions:
        items.append(
            {
                "session_id": s.get("session_id"),
                "timestamp": s.get("created_at"),
                "masked_count": s.get("masked_count", 0) or 0,
                "types": [],
            }
        )

    return {"items": items, "total": total, "page": page, "limit": limit}


@api_router.get("/api/me/sessions")
@limiter.limit("30/minute")
async def me_sessions(request: Request, api_key: dict = Depends(verify_api_key)):
    """当前用户的 session 列表。"""
    team_id = api_key["team_id"]
    sessions = db.get_user_sessions(team_id, limit=50, offset=0)
    return {
        "sessions": [
            {
                "session_id": s["session_id"],
                "created_at": s.get("created_at"),
                "total_masked": s.get("masked_count", 0) or 0,
            }
            for s in sessions
        ]
    }


@api_router.get("/api/me/session/{session_id}")
@limiter.limit("30/minute")
async def me_session_detail(
    request: Request, session_id: str, api_key: dict = Depends(verify_api_key)
):
    """单个 session 的详细审计链。"""
    if not session_id or len(session_id) > 128:
        return JSONResponse(status_code=400, content={"error": "无效的 session_id"})
    team_id = api_key.get("team_id", "default")
    events = db.get_session_audit_log(session_id, team_id=team_id)
    if not events:
        return {"session_id": session_id, "created_at": None, "events": []}

    return {
        "session_id": session_id,
        "created_at": events[0].get("created_at") if events else None,
        "events": [
            {
                "timestamp": e.get("created_at"),
                "action": e.get("action"),
                "detail": json.loads(e["detail_json"]) if e.get("detail_json") else {},
            }
            for e in events
        ],
    }
