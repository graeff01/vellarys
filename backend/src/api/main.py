"""
VELARIS API - Ponto de Entrada novo
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.database import init_db, async_session
from src.api.routes.messages import router as messages_router

from src.config import get_settings
from src.infrastructure.database import init_db, async_session
from src.infrastructure.services.gupshup_init import init_gupshup_service, shutdown_gupshup_service
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
    gupshup_webhook_router,
    simulator_router,
    # Admin
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
)

from src.domain.entities import User, Tenant
from src.domain.entities.enums import UserRole
from src.infrastructure.services.auth_service import hash_password
from sqlalchemy import select


settings = get_settings()


# ============================================================
# 🚀 Função que cria o superadmin automaticamente
# ============================================================
async def create_superadmin():
    async with async_session() as session:
        # Verifica se já existe
        result = await session.execute(
            select(User).where(User.email == settings.superadmin_email)
        )
        user = result.scalars().first()

        if user:
            print("👑 Superadmin já existe. Pulando criação.")
            return

        print("🔧 Criando superadmin...")

        # Criar tenant principal
        tenant = Tenant(
            name=settings.superadmin_tenant_name,
            slug=settings.superadmin_tenant_slug,
            active=True
        )
        session.add(tenant)
        await session.flush()

        # Criar superadmin
        superadmin = User(
            name="Superadmin",
            email=settings.superadmin_email,
            password_hash=hash_password(settings.superadmin_password),
            role=UserRole.SUPERADMIN.value,
            tenant_id=tenant.id,
            active=True
        )

        session.add(superadmin)
        await session.commit()

        print("✅ Superadmin criado com sucesso!")


# ============================================================
# LIFESPAN (Startup + Shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando Velaris API...")

    await init_db()
    print("✅ Tabelas criadas!")

    # Criar superadmin (apenas se não existir)
    await create_superadmin()

    # Inicializa Gupshup
    init_gupshup_service()

    yield

    await shutdown_gupshup_service()
    print("👋 Encerrando...")


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Velaris API",
    description="IA atendente B2B multi-tenant",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# ⭐ CORS - CORRIGIDO PARA USAR CONFIG
# ============================================================
# Lista padrão (fallback se não tiver no .env)
default_origins = [
    "https://vellarys-production.up.railway.app",
    "https://hopeful-purpose-production-3a2b.up.railway.app",
    "http://localhost:3000",
    "http://localhost:8000",
]


# Pega do config (que vem do .env) ou usa default
allowed_origins = (
    settings.cors_origins_list 
    if getattr(settings, "cors_origins_list", None) 
    else default_origins
)

# Garantir que lista do settings existe e tem itens válidos
if getattr(settings, "cors_origins_list", None):
    allowed_origins = [orig for orig in settings.cors_origins_list if orig.strip()]
else:
    allowed_origins = default_origins




print(f"🔒 CORS configurado para: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROTASSssssss
# ============================================================
# Públicas / Tenant
app.include_router(empreendimentos_router, prefix="/api/v1")
app.include_router(dialog360_webhook_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(gupshup_webhook_router, prefix="/api/v1")
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

# Admin
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