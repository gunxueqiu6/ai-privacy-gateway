"""Routers package — domain-specific FastAPI route modules."""

from .proxy import proxy_router
from .api import api_router
from .auth import auth_router
from .admin import router as admin_router
from .setup import router as setup_router


def register_routers(app):
    """Register all domain routers on the FastAPI app."""
    app.include_router(proxy_router)
    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(setup_router)

    # 企业版（付费）路由 — 仅私有仓库存在 routers/enterprise.py 时注册。
    # 公开（免费）版无此文件，这里安全跳过，保证公开版可独立运行。
    try:
        from .enterprise import router as enterprise_router
    except ImportError:
        enterprise_router = None
    if enterprise_router is not None:
        app.include_router(enterprise_router)
