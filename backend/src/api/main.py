"""
VELARIS API - Ponto de Entrada
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.database import init_db, async_session

from src.config import get_settings
from src.infrastructure.database import init_db, async_session
from src.infrastructure.services.gupshup_init import init_gupshup_service, shutdown_gupshup_service
from src.api.routes import (
    dialog360_webhook_router,  # ADICIONAR AQUI
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
            active=True  # CAMPO CORRETO
        )
        session.add(tenant)
        await session.flush()  # gerar ID

        # Criar superadmin
        superadmin = User(
            name="Superadmin",
            email=settings.superadmin_email,
            password_hash=hash_password(settings.superadmin_password),  # CAMPO CORRETO
            role=UserRole.SUPERADMIN.value,  # para não dar erro
            tenant_id=tenant.id,
            active=True  # CAMPO CORRETO
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

# CORS - Permitir origens de desenvolvimento e produção
allowed_origins = [
    # Produção Railway
    "https://vellarys-production.up.railway.app",
    "https://hopeful-purpose-production-3a2b.up.railway.app",
    # Domínio customizado (futuro)
    "https://vellarys.com",
    "https://www.vellarys.com",
    # Desenvolvimento local
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROTAS
# ============================================================
# Públicas / Tenant
app.include_router(auth_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(gupshup_webhook_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
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