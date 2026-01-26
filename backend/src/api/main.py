"""
VELARIS API - Ponto de Entrada
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.infrastructure.scheduler import create_scheduler, start_scheduler, stop_scheduler
from src.api.routes.debug_portal import router as debug_portal_router
from src.config import get_settings
from src.infrastructure.database import init_db, async_session

# Logger
logger = logging.getLogger(__name__)

# Sentry
import sentry_sdk

# Routers
from src.api.routes.messages import router as messages_router
from src.api.routes.zapi_routes import router as zapi_router
from src.api.routes import (
    admin_ceo_router,
    products_router,
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
    seller_inbox_router,
    seller_info_router,
    reengagement_router,
    export_router,
    usage_router,
    simulator_router,
    handoff_router,
    admin_dashboard_router,
    admin_tenants_router,
    admin_niches_router,
    admin_logs_router,
    admin_plans_router,
    health_router,
    data_sources_router,
    dashboard_config_router,
    sales_router,
    opportunities_router,
    opportunities_leads_router,
    appointments_router,
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


from src.infrastructure.logging_config import setup_logging

# ============================================================
# 🔁 LIFESPAN
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    
    # ============================================================
    # 🛡️ SENTRY (MONITORAMENTO)
    # ============================================================
    if settings.sentry_dsn:
        print(f"🛡️ Sentry ativo em: {settings.environment}")
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=1.0 if settings.is_development else 0.1,
            profiles_sample_rate=1.0 if settings.is_development else 0.1,
        )
    else:
        print("⚠️ Sentry DSN não configurado. Monitoramento desativado.")
        
    print("🚀 Iniciando Velaris API...")

    # ============================================================
    # 🔔 PUSH NOTIFICATIONS (VAPID)
    # ============================================================
    if settings.vapid_configured:
        print("🔔 Push Notifications (VAPID) configuradas!")
    else:
        print("⚠️ VAPID keys não configuradas. Push notifications desativadas.")

    await init_db()
    print("✅ Tabelas criadas!")

    await create_superadmin()

    # Inicia scheduler de jobs
    create_scheduler()
    start_scheduler()

    yield

    # Para scheduler
    stop_scheduler()


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
# Debug: Mostra origins carregadas no startup
logger.info(f"🌐 CORS Origins configuradas: {settings.cors_origins_list}")
logger.info(f"🌐 CORS Regex: ^https://[a-zA-Z0-9-]+\\.up\\.railway\\.app$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https://[a-zA-Z0-9-]+\.up\.railway\.app$", # CORRIGIDO: Aceita vellarys.up.railway.app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ============================================================
# EXCEPTION HANDLERS - Garantir CORS em respostas de erro
# ============================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Garante que HTTPExceptions incluam headers de CORS.
    Sem isso, erros 401/403/500 bloqueiam por CORS no browser.
    """
    origin = request.headers.get("origin")

    # Criar resposta JSON com o erro
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

    # Adicionar headers de CORS se a origin estiver permitida
    if origin:
        # Verificar se a origin está na lista ou match o regex
        allowed = False
        if origin in settings.cors_origins_list or "*" in settings.cors_origins_list:
            allowed = True
        elif origin.endswith(".up.railway.app"):
            allowed = True

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Vary"] = "Origin"

    return response


# ============================================================
# ROTAS
# ============================================================
app.include_router(health_router, prefix="/api") # ← ADICIONE ESTA LINHA (SEM PREFIX!)
app.include_router(zapi_router, prefix="/api")
app.include_router(debug_portal_router, prefix="/api/v1/debug", tags=["debug"])
app.include_router(products_router, prefix="/api/v1")
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
app.include_router(seller_inbox_router, prefix="/api/v1")
app.include_router(seller_info_router, prefix="/api/v1")
app.include_router(reengagement_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(simulator_router, prefix="/api/v1")
app.include_router(twilio_webhook_router, prefix="/api/v1")
app.include_router(handoff_router, prefix="/api/v1")
app.include_router(data_sources_router, prefix="/api/v1")
app.include_router(dashboard_config_router, prefix="/api/v1")
app.include_router(sales_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(opportunities_leads_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")

# Admin
app.include_router(admin_dashboard_router, prefix="/api/v1")
app.include_router(admin_tenants_router, prefix="/api/v1")
app.include_router(admin_niches_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")
app.include_router(admin_plans_router, prefix="/api/v1")
app.include_router(admin_ceo_router, prefix="/api/v1")  


@app.get("/")
async def root():
    return {"name": "Velaris API", "status": "running"}


@app.get("/api/v1/version")
async def version():
    return {"version": "2024-12-30-HEALTH-CHECK", "timestamp": "18:30"}
