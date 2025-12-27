"""Rotas do Painel Admin."""

from .ceo_dashboard import router as admin_ceo_router
from .dashboard import router as admin_dashboard_router
from .tenants import router as admin_tenants_router
from .niches import router as admin_niches_router
from .logs import router as admin_logs_router
from .plans import router as admin_plans_router

__all__ = [
    "admin_dashboard_router",
    "admin_tenants_router",
    "admin_niches_router",
    "admin_logs_router",
    "admin_plans_router",
    "admin_ceo_router",
]
