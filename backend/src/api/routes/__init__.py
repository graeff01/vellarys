"""Rotas da API."""

from .twilio_webhook import router as twilio_webhook_router
from .webhook import router as webhook_router
from .gupshup_webhook import router as gupshup_webhook_router
from .leads import router as leads_router
from .metrics import router as metrics_router
from .tenants import router as tenants_router
from .auth import router as auth_router
from .settings import router as settings_router
from .settings_v2 import router as settings_v2_router  # ← NOVA ARQUITETURA
from .notifications import router as notifications_router
from .sellers import router as sellers_router
from .reengagement import router as reengagement_router
from .export import router as export_router
from .usage import router as usage_router
from .simulator import router as simulator_router
from .dialog360_webhook import router as dialog360_webhook_router
from .products import router as products_router
from .handoff_routes import router as handoff_router  # ← NOVO
from src.api.routes.health import router as health_router  # ← ADICIONADO
from .seller_inbox import router as seller_inbox_router  # ← SELLER INBOX (CRM)
from .seller_info import router as seller_info_router  # ← SELLER INFO (Helpers)
from .data_sources import router as data_sources_router  # ← DATA SOURCES
from .dashboard_config import router as dashboard_config_router  # ← DASHBOARD CONFIG
from .sales import router as sales_router  # ← SALES & GOALS
from .opportunities import router as opportunities_router, leads_router as opportunities_leads_router  # ← OPPORTUNITIES
from .appointments import router as appointments_router  # ← APPOINTMENTS (CALENDÁRIO)
from .manager_ai import router as manager_ai_router  # ← MANAGER AI (JARVIS)
from .templates import router as templates_router  # ← RESPONSE TEMPLATES (RESPOSTAS RÁPIDAS)

# Admin routes
from .admin import (
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
    admin_ceo_router,
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
    "settings_v2_router",  # ← NOVA ARQUITETURA
    "notifications_router",
    "sellers_router",
    "reengagement_router",
    "export_router",
    "usage_router",
    "simulator_router",
    "products_router",
    "handoff_router",
    "health_router",
    "seller_inbox_router",
    "seller_info_router",
    "data_sources_router",
    "dashboard_config_router",
    "sales_router",
    "opportunities_router",
    "opportunities_leads_router",
    "appointments_router",
    "manager_ai_router",
    "templates_router",
    # Admin
    "admin_dashboard_router",
    "admin_tenants_router",
    "admin_niches_router",
    "admin_logs_router",
    "admin_plans_router",
    "admin_ceo_router",
]
