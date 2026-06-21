"""
独立 API 路由 — 脱敏/还原/批量/实体类型查询。
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mask_engine import get_mask_engine, HAS_NER
from .dependencies import safe_json, BAD_ENCODING_RESPONSE

api_router = APIRouter(tags=["api"])


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
