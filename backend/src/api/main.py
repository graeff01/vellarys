"""
VELARIS API - Ponto de Entrada
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.infrastructure.database import init_db
from src.infrastructure.services.gupshup_init import init_gupshup_service, shutdown_gupshup_service
from src.api.routes import (
    webhook_router,
    leads_router,
    metrics_router,
    tenants_router,
    auth_router,
    settings_router,
    notifications_router,
    sellers_router,
    reengagement_router,
    export_router,
    usage_router,
    gupshup_webhook_router,
    # Admin
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando Velaris API...")
    if settings.is_development:
        await init_db()
        print("✅ Tabelas criadas!")
    
    # Inicializa Gupshup
    init_gupshup_service()
    
    yield
    
    # Shutdown
    await shutdown_gupshup_service()
    print("👋 Encerrando...")


app = FastAPI(
    title="Velaris API",
    description="IA atendente B2B multi-tenant",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ROTAS PÚBLICAS / TENANT
# ============================================
app.include_router(auth_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(gupshup_webhook_router, prefix="/api/v1")  # Webhook Gupshup
app.include_router(leads_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(sellers_router, prefix="/api/v1")
app.include_router(reengagement_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")

# ============================================
# ROTAS ADMIN (Superadmin apenas)
# ============================================
app.include_router(admin_dashboard_router, prefix="/api/v1")
app.include_router(admin_tenants_router, prefix="/api/v1")
app.include_router(admin_niches_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")
app.include_router(admin_plans_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": "Velaris API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}