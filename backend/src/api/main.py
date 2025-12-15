"""
VELARIS API - Ponto de Entrada
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from src.api.routes.debug_portal import router as debug_portal_router

from src.config import get_settings
from src.infrastructure.database import init_db, async_session

# Routers
from src.api.routes.messages import router as messages_router
from src.api.routes.zapi_routes import router as zapi_router
from src.api.routes import (
    empreendimentos_router,
    dialog360_webhook_router,
    twilio_webhook_router,
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
    simulator_router,
    handoff_router,  # ← IMPORTADO
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
)

# Domain
from src.domain.entities import User, Tenant
from src.domain.entities.enums import UserRole
from src.infrastructure.services.auth_service import hash_password

settings = get_settings()

# ============================================================
# 🚀 Criar superadmin automaticamente
# ============================================================
async def create_superadmin():
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == settings.superadmin_email)
        )
        user = result.scalars().first()

        if user:
            print("👑 Superadmin já existe. Pulando criação.")
            return

        print("🔧 Criando superadmin...")

        tenant = Tenant(
            name=settings.superadmin_tenant_name,
            slug=settings.superadmin_tenant_slug,
            active=True,
        )
        session.add(tenant)
        await session.flush()

        superadmin = User(
            name="Superadmin",
            email=settings.superadmin_email,
            password_hash=hash_password(settings.superadmin_password),
            role=UserRole.SUPERADMIN.value,
            tenant_id=tenant.id,
            active=True,
        )

        session.add(superadmin)
        await session.commit()
        print("✅ Superadmin criado com sucesso!")


@app.get("/api/v1/version")
async def version():
    return {"version": "2024-12-15-DEBUG-PORTAL", "timestamp": "03:30"}

# ============================================================
# 🔁 LIFESPAN
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando Velaris API...")

    await init_db()
    print("✅ Tabelas criadas!")

    await create_superadmin()

    yield

    print("👋 Encerrando Velaris API...")


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Velaris API",
    description="IA atendente B2B multi-tenant",
    version="0.1.0",
    lifespan=lifespan,
)

# ============================================================
# ⭐ CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vellarys-production.up.railway.app",
        "https://hopeful-purpose-production-3a2b.up.railway.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROTAS
# ============================================================
app.include_router(zapi_router, prefix="/api")
app.include_router(debug_portal_router, prefix="/api/v1/debug", tags=["debug"])
app.include_router(empreendimentos_router, prefix="/api/v1")
app.include_router(dialog360_webhook_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(sellers_router, prefix="/api/v1")
app.include_router(reengagement_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(simulator_router, prefix="/api/v1")
app.include_router(twilio_webhook_router, prefix="/api/v1")

# ⭐ HANDOFF - FALTAVA ESTE!
app.include_router(handoff_router, prefix="/api/v1")

# Admin
app.include_router(admin_dashboard_router, prefix="/api/v1")
app.include_router(admin_tenants_router, prefix="/api/v1")
app.include_router(admin_niches_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")
app.include_router(admin_plans_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": "Velaris API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}