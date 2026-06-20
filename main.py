"""
AI隐私网关 - FastAPI 入口 + 路由注册 + 管理后台
"""
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import config
from database import db
from routers import register_routers
from routers.dependencies import limiter

# PyInstaller bundle: resolve paths relative to the extracted bundle or CWD
if getattr(sys, 'frozen', False):
    _app_dir = sys._MEIPASS
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时的生命周期管理。"""
    # 启动后台清理任务，每 24 小时清理过期映射
    async def cleanup_loop():
        while True:
            await asyncio.sleep(86400)
            try:
                deleted = db.cleanup_expired_mappings()
                logger.info(f"定时清理: 删除了 {deleted} 条过期映射")
            except Exception:
                logger.exception("定时清理过期映射失败")

    cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("已启动 vault_mappings 定时清理任务 (间隔 24h)")
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# 创建 FastAPI 应用
app = FastAPI(
    title="AI隐私网关",
    description="边缘侧本地隐私网关 - 拦截AI请求自动脱敏",
    version="1.1.0",
    lifespan=lifespan,
)

# 挂载静态文件 - 管理面板
app.mount("/admin/static", StaticFiles(directory=os.path.join(_app_dir, "static")), name="admin_static")

# 速率限制
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


@app.get("/")
async def root() -> dict:
    """Root - health check."""
    return {
        "status": "healthy",
        "service": "AI Privacy Gateway",
        "version": "Lite",
        "tier": config.tier,
    }


@app.get("/health")
async def health() -> dict:
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/admin")
async def admin_panel():
    """Redirect to admin panel."""
    return RedirectResponse(url="/admin/static/index.html")


@app.get("/admin/")
async def admin_panel_slash():
    """Redirect to admin panel."""
    return RedirectResponse(url="/admin/static/index.html")


# 注册所有路由模块（必须在 /admin 之后，否则 /admin/* API 路由优先）
register_routers(app)


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import sys
    import uvicorn

    banner = [
        "=" * 56,
        "  AI Privacy Gateway  v1.1.0",
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

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 — gateway intentionally binds all interfaces
        port=config.LISTEN_PORT,
        log_level="info"
    )
