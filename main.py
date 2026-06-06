"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from config import config, get_config
from database import db
from gateway_core import get_gateway_core
from integrity_checker import get_integrity_checker, start_integrity_checker
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

# 全局映射缓存
_mappings_cache: Dict[str, str] = {}
_cache_lock = asyncio.Lock()


async def refresh_cache():
    """刷新映射缓存"""
    global _mappings_cache
    async with _cache_lock:
        _mappings_cache = db.get_all_mappings()


# ==================== 主代理路由 ====================

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """聊天完成接口 - 核心脱敏代理"""
    gateway = get_gateway_core()

    body = await request.json()

    # 上行脱敏
    masked_body, mappings, stats, session_id = gateway.mask_request(body)

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
                                choice["message"]["content"], mappings
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


@app.get("/admin/stats")
async def get_stats(date: str = None):
    """获取统计信息"""
    if date:
        target_date = date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")

    stats = db.get_today_stats()
    return stats


@app.get("/admin/keywords")
async def list_keywords():
    """获取自定义敏感词列表"""
    engine = get_mask_engine()
    return {"keywords": engine.get_custom_keywords()}


@app.post("/admin/keywords/add")
async def add_keyword(request: Request):
    """添加自定义敏感词"""
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
async def delete_keyword(request: Request):
    """删除自定义敏感词"""
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
async def clear_mappings():
    """清除所有映射记录"""
    db.clear_all_mappings()
    return {"status": "ok", "message": "所有映射记录已清除"}


@app.get("/admin/version")
async def get_version_info():
    """获取版本信息"""
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
async def get_integrity_status():
    """获取运行时完整性检查状态"""
    checker = get_integrity_checker()
    last = checker.last_result
    return {
        "available": checker.is_available,
        "last_result": last,
        "anomaly_count": checker._anomaly_count
    }


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"AI隐私网关启动")
    logger.info(f"版本: {config.get_version_display()}")
    logger.info(f"监听端口: {config.LISTEN_PORT}")
    logger.info(f"目标AI服务: {config.TARGET_LLM}")
    logger.info(f"数据库: {config.DB_PATH}")

    # 启动运行时完整性检查
    start_integrity_checker()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.LISTEN_PORT,
        log_level="info"
    )