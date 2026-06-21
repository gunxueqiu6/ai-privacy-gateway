"""
独立 API 路由 — 脱敏/还原/批量/实体类型查询。
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mask_engine import get_mask_engine, HAS_NER, KNOWN_ENTITY_TYPES
import re
import logging

from .dependencies import safe_json, BAD_ENCODING_RESPONSE

api_router = APIRouter(tags=["api"])

logger = logging.getLogger(__name__)


def _entity_type_from_placeholder(placeholder: str) -> str:
    mapping = {
        "PHONE": "PII_PHONE", "EMAIL": "PII_EMAIL", "IDCARD": "PII_IDCARD",
        "BANK": "PII_BANK", "PER": "PII_PER", "LOC": "PII_LOC", "ORG": "PII_ORG",
        "PLATE": "PII_PLATE", "IP": "PII_IP", "URL": "PII_URL",
        "DATE": "PII_DATE", "AMOUNT": "PII_AMOUNT", "POSTCODE": "PII_POSTCODE",
        "CUST": "PII_CUST",
    }
    for key, entity in mapping.items():
        if key in placeholder:
            return entity
    return "unknown"


@api_router.post("/api/mask")
async def api_mask(request: Request):
    """独立脱敏 API"""
    body, ok = await safe_json(request)
    if not ok:
        return BAD_ENCODING_RESPONSE
    text = body.get("text", "")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text 参数不能为空"})
    if len(text) > 102400:
        return JSONResponse(status_code=413, content={"error": "输入文本过长，最大支持 100KB"})

    engine = get_mask_engine()
    masked_text, mappings, stats = engine.mask(text)

    entities = []
    for placeholder, value in mappings.items():
        entities.append({
            "type": _entity_type_from_placeholder(placeholder),
            "value": value,
            "placeholder": placeholder,
            "position": text.find(value),
        })

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
        return JSONResponse(status_code=413, content={"error": "输入文本过长，最大支持 100KB"})

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
        return JSONResponse(status_code=400, content={"error": "单次批量处理最多 50 条"})

    for i, t in enumerate(texts):
        if len(t) > 102400:
            return JSONResponse(status_code=413, content={"error": f"第 {i+1} 条文本过长，最大支持 100KB"})

    engine = get_mask_engine()
    results = []
    for text in texts:
        masked_text, mappings, stats = engine.mask(text)
        entities = [{"type": _entity_type_from_placeholder(p), "value": v, "placeholder": p, "position": text.find(v)} for p, v in mappings.items()]
        results.append({"original": text, "masked": masked_text, "entities": entities, "stats": stats})

    return {"results": results, "total_count": len(results)}


@api_router.get("/api/entities")
async def api_get_entities(request: Request) -> dict:
    """获取支持的实体类型列表"""
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
    return {"entities": entities, "total": len(entities), "version": "Lite", "ner_available": HAS_NER}


# ==================== Custom Regex Rules API ====================


@api_router.get("/api/custom-regex-rules")
async def api_list_custom_regex_rules(request: Request) -> dict:
    """获取所有自定义正则规则"""
    from database import db
    rules = db.get_custom_regex_rules()
    return {"rules": rules, "total": len(rules)}


@api_router.post("/api/custom-regex-rules")
async def api_add_custom_regex_rule(request: Request):
    """添加自定义正则规则"""
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

    # 验证正则表达式合法性
    try:
        re.compile(pattern)
    except re.error as e:
        return JSONResponse(status_code=400, content={"error": f"无效的正则表达式: {e}"})

    from database import db
    rule_id = db.add_custom_regex_rule(name, pattern, entity_type)
    if rule_id == -1:
        return JSONResponse(status_code=409, content={"error": f"规则名称 '{name}' 已存在"})

    # 同步到引擎
    engine = get_mask_engine()
    try:
        engine.add_custom_regex_rule(name, pattern, entity_type)
    except (ValueError, re.error) as e:
        # 引擎错误不应发生（已在前面验证），但以防万一回滚 DB
        db.delete_custom_regex_rule(rule_id)
        return JSONResponse(status_code=500, content={"error": f"引擎添加规则失败: {e}"})

    logger.info(f"API 添加自定义正则规则: {name} (type={entity_type})")
    return {"status": "ok", "id": rule_id, "message": f"规则 '{name}' 已添加"}


@api_router.delete("/api/custom-regex-rules/{rule_id}")
async def api_delete_custom_regex_rule(request: Request, rule_id: int):
    """删除自定义正则规则"""
    from database import db
    rules = db.get_custom_regex_rules()
    target = next((r for r in rules if r["id"] == rule_id), None)
    if target is None:
        return JSONResponse(status_code=404, content={"error": f"规则 ID {rule_id} 不存在"})

    # 先删除 DB，再从引擎移除
    if not db.delete_custom_regex_rule(rule_id):
        return JSONResponse(status_code=500, content={"error": "数据库删除失败"})

    engine = get_mask_engine()
    engine.remove_custom_regex_rule(target["name"])

    logger.info(f"API 删除自定义正则规则: {target['name']} (id={rule_id})")
    return {"status": "ok", "message": f"规则 '{target['name']}' 已删除"}


@api_router.put("/api/custom-regex-rules/{rule_id}/toggle")
async def api_toggle_custom_regex_rule(request: Request, rule_id: int):
    """启用/禁用自定义正则规则"""
    from database import db
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
    logger.info(f"API {status_text}自定义正则规则: {target['name']} (id={rule_id})")
    return {"status": "ok", "id": rule_id, "enabled": new_enabled, "message": f"规则 '{target['name']}' 已{status_text}"}
