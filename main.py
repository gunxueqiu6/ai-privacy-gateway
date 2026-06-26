"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import config
from database import db
from routers import register_routers
from routers.dependencies import limiter
from logging_config import setup_logging
from metrics import (
    request_count,
    request_latency_seconds,
    upstream_health_status,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from gateway_core import get_gateway_core

# 配置结构化日志（LOG_FORMAT=json 或 text，通过环境变量控制）
setup_logging()
import logging

logger = logging.getLogger(__name__)

# PyInstaller bundle: resolve paths relative to the extracted bundle or CWD
if getattr(sys, 'frozen', False):
    _app_dir = sys._MEIPASS
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))

# 启动时间戳（用于计算 uptime）
_start_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时的生命周期管理。"""
    # --- 后台清理任务：每 24 小时清理过期映射 ---
    async def cleanup_loop():
        while True:
            await asyncio.sleep(86400)
            try:
                deleted = db.cleanup_expired_mappings()
                logger.info("定时清理: 删除了 %d 条过期映射", deleted)
            except Exception:
                logger.exception("定时清理过期映射失败")

    # --- 后台指标更新任务：每 15 秒刷新上游健康状态 gauge ---
    async def metrics_loop():
        while True:
            await asyncio.sleep(15)
            try:
                core = get_gateway_core()
                for node in core.load_balancer.get_stats():
                    upstream_health_status.labels(upstream_url=node["url"]).set(
                        1 if node["healthy"] else 0
                    )
            except Exception:
                pass

    # --- 启动时数据库完整性检查 ---
    try:
        if db.check_integrity():
            logger.info("启动时数据库完整性检查通过")
        else:
            logger.warning("启动时数据库完整性检查失败 — 数据库可能已损坏")
    except Exception as e:
        logger.warning("启动时数据库完整性检查异常: %s", e)

    cleanup_task = asyncio.create_task(cleanup_loop())
    metrics_task = asyncio.create_task(metrics_loop())
    logger.info("已启动 vault_mappings 定时清理任务 (间隔 24h)")
    logger.info("已启动上游健康指标更新任务 (间隔 15s)")
    yield
    # --- 优雅关闭 ---
    logger.info("正在优雅关闭...")
    core = get_gateway_core()
    core.shutdown_flag = True

    cleanup_task.cancel()
    metrics_task.cancel()
    try:
        await cleanup_task
        await metrics_task
    except asyncio.CancelledError:
        pass

    # 排空活跃请求
    timeout = config.SHUTDOWN_TIMEOUT
    deadline = time.time() + timeout
    while core.active_requests > 0 and time.time() < deadline:
        logger.info("等待 %d 个活跃请求完成...", core.active_requests)
        await asyncio.sleep(0.5)

    if core.active_requests > 0:
        logger.warning("关闭超时 (%ds)，强制终止 %d 个活跃请求", timeout, core.active_requests)
    else:
        logger.info("所有活跃请求已完成，安全关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI隐私网关",
    description="边缘侧本地隐私网关 - 拦截AI请求自动脱敏",
    version="2.0.0",
    lifespan=lifespan,
)


# ==================== 请求指标中间件 ====================

@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:
    """记录请求计数和延迟到 Prometheus 指标。"""
    # 跳过 /metrics 自身以避免循环
    path = request.url.path
    if path == "/metrics":
        return await call_next(request)

    method = request.method
    start = time.time()

    try:
        response: Response = await call_next(request)
    except Exception:
        # 即使请求处理异常也要记录
        request_count.labels(endpoint=path, method=method, status_code="500").inc()
        raise

    latency = time.time() - start
    status_code = str(response.status_code)
    request_count.labels(endpoint=path, method=method, status_code=status_code).inc()
    request_latency_seconds.labels(endpoint=path).observe(latency)
    return response


# ==================== 挂载静态文件 ====================

app.mount("/admin/static", StaticFiles(directory=os.path.join(_app_dir, "static")), name="admin_static")

# ==================== 速率限制 ====================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==================== Body 大小限制中间件 ====================


@app.middleware("http")
async def body_size_middleware(request: Request, call_next) -> Response:
    """限制请求体大小，防止内存溢出。"""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > config.MAX_REQUEST_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"error": f"Request body too large, max {config.MAX_REQUEST_BODY_SIZE} bytes"}
                )
        except ValueError:
            pass
    return await call_next(request)


# ==================== CORS 中间件 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9999", "http://127.0.0.1:9999"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ==================== 健康检查 ====================

@app.get("/")
async def root() -> dict:
    """Root - 详细健康检查。"""
    return await _build_health_response()


@app.get("/health")
async def health() -> dict:
    """独立健康检查接口。"""
    return await _build_health_response()


async def _build_health_response() -> dict:
    """构建统一的健康检查响应体（含上游连通性检测）。"""
    components = {
        "database": "ok",
        "mask_engine": "ok",
        "ner_engine": "ok",
        "upstream": "ok",
    }
    # 检查 NER 引擎
    try:
        from mask_engine import HAS_NER  # noqa: F811
        if not HAS_NER:
            components["ner_engine"] = "unavailable"
    except Exception:
        components["ner_engine"] = "error"

    # 检查数据库连接
    try:
        db._ensure_initialized()
    except Exception:
        components["database"] = "error"

    # 上游连通性检测
    try:
        upstream_ok = await _check_upstream_connectivity()
        if not upstream_ok:
            components["upstream"] = "unreachable"
    except Exception:
        components["upstream"] = "error"

    status = "healthy"
    if components.get("upstream") == "unreachable":
        status = "degraded"

    uptime = int(time.time() - _start_time)

    return {
        "status": status,
        "service": "AI Privacy Gateway",
        "version": "2.0.0",
        "tier": "lite",
        "uptime_seconds": uptime,
        "timestamp": datetime.now().isoformat(),
        "components": components,
    }


async def _check_upstream_connectivity() -> bool:
    """Check if at least one upstream LLM endpoint is reachable.
    Returns True if at least one responds with a <500 status."""
    try:
        if config.UPSTREAM_LLM_URLS:
            upstream_urls = [u.strip() for u in config.UPSTREAM_LLM_URLS.split(",") if u.strip()]
        else:
            upstream_urls = [config.TARGET_LLM]

        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
            for url in upstream_urls:
                try:
                    head_url = url.rstrip("/")
                    resp = await client.head(head_url)
                    if resp.status_code < 500:
                        return True
                except Exception:
                    continue
        return False
    except Exception:
        return False


@app.get("/healthz")
async def healthz() -> dict:
    """Liveness probe — lightweight, no upstream check.

    Returns 200 immediately if the process is alive.
    Use for container/k8s liveness checks where you only care if the
    process is running, not whether it can serve traffic.
    """
    return {"status": "alive"}


# ==================== Prometheus 指标 ====================

@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus 指标抓取端点（无需认证）。"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ==================== 管理面板 ====================

def _env_exists() -> bool:
    """Check whether a non-empty .env file exists (first-run detection)."""
    if getattr(sys, 'frozen', False):
        env_path = Path.cwd() / ".env"
    else:
        env_path = Path(__file__).resolve().parent / ".env"
    return env_path.exists() and env_path.stat().st_size > 0


@app.get("/admin")
async def admin_panel():
    """Redirect to admin panel or setup wizard (first-run detection)."""
    if _env_exists():
        return RedirectResponse(url="/admin/static/index.html")
    return RedirectResponse(url="/admin/static/setup.html")


@app.get("/admin/")
async def admin_panel_slash():
    """Redirect to admin panel or setup wizard (first-run detection)."""
    if _env_exists():
        return RedirectResponse(url="/admin/static/index.html")
    return RedirectResponse(url="/admin/static/setup.html")


# 注册所有路由模块（必须在 /admin 之后，否则 /admin/* API 路由优先）
register_routers(app)


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    banner = [
        "=" * 56,
        "  AI Privacy Gateway  v2.0.0",
        "  Your AI Data Privacy Firewall",
        "=" * 56,
        f"  API:          http://localhost:{config.LISTEN_PORT}/v1",
        f"  Admin:        http://localhost:{config.LISTEN_PORT}/admin",
        f"  Target:       {config.TARGET_LLM}",
        f"  Admin PW:     {config.ADMIN_PASSWORD}",
        "-" * 56,
        "  [!] Save the admin password above immediately!",
        "  Configure your AI client to use the API URL above.",
        "=" * 56,
    ]
    sys.stdout.write("\n".join(banner) + "\n")
    sys.stdout.flush()

    uv_kwargs = {
        "app": app,
        "host": "0.0.0.0",  # nosec B104 — gateway intentionally binds all interfaces
        "port": config.LISTEN_PORT,
        "log_level": "info",
        "timeout_graceful_shutdown": config.SHUTDOWN_TIMEOUT,
    }
    if config.SSL_CERTFILE and config.SSL_KEYFILE:
        uv_kwargs["ssl_certfile"] = config.SSL_CERTFILE
        uv_kwargs["ssl_keyfile"] = config.SSL_KEYFILE
        logger.info("TLS 已启用: cert=%s", config.SSL_CERTFILE)
    uvicorn.run(**uv_kwargs)
