"""Routers package — domain-specific FastAPI route modules."""

from .proxy import proxy_router
from .api import api_router
from .auth import auth_router
from .admin import router as admin_router


def register_routers(app):
    """Register all domain routers on the FastAPI app."""
    app.include_router(proxy_router)
    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
