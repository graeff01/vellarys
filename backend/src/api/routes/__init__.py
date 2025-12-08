"""Rotas da API."""

from .twilio_webhook import router as twilio_webhook_router
from .webhook import router as webhook_router
from .gupshup_webhook import router as gupshup_webhook_router
from .leads import router as leads_router
from .metrics import router as metrics_router
from .tenants import router as tenants_router
from .auth import router as auth_router
from .settings import router as settings_router
from .notifications import router as notifications_router
from .sellers import router as sellers_router
from .reengagement import router as reengagement_router
from .export import router as export_router
from .usage import router as usage_router
from .simulator import router as simulator_router
from .dialog360_webhook import router as dialog360_webhook_router
from .empreendimentos import router as empreendimentos_router

# Admin routes
from .admin import (
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
)

__all__ = [
    "dialog360_webhook_router",
    "twilio_webhook_router",
    "webhook_router",
    "gupshup_webhook_router",
    "leads_router",
    "metrics_router",
    "tenants_router",
    "auth_router",
    "settings_router",
    "notifications_router",
    "sellers_router",
    "reengagement_router",
    "export_router",
    "usage_router",
    "simulator_router",
    "empreendimentos_router",
    # Admin
    "admin_dashboard_router",
    "admin_tenants_router",
    "admin_niches_router",
    "admin_logs_router",
    "admin_plans_router",
]