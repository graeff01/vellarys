"""
ROTAS: WEBHOOK GUPSHUP
=======================

Endpoint específico para receber mensagens do Gupshup.
Converte o formato Gupshup para o formato interno do Velaris.

FLUXO:
1. Gupshup envia POST com mensagem
2. Validamos assinatura (segurança)
3. Identificamos o tenant correto
4. Criamos GupshupService específico daquele tenant
5. Parseamos para formato Velaris
6. Chamamos process_message()
7. Enviamos resposta da IA via Gupshup
8. Retornamos ACK para o Gupshup

CONFIGURAÇÃO NO GUPSHUP:
- Webhook URL: https://seu-dominio.com/webhook/gupshup
- Método: POST
- Content-Type: application/json
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant
from src.application.use_cases import process_message
from src.infrastructure.services.gupshup_service import (
    get_gupshup_service,              # ainda usado no /health
    GupshupService,
    ParsedIncomingMessage,
    build_gupshup_service_from_settings,  # MULTI-TENANT
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook Gupshup"])


# ==========================================
# HELPERS
# ==========================================

async def get_tenant_by_phone(
    db: AsyncSession,
    phone_number: str,
) -> Optional[Tenant]:
    """
    Busca tenant pelo número de WhatsApp configurado.
    
    settings.whatsapp_number = "5511999999999"
    """
    result = await db.execute(
        select(Tenant).where(Tenant.active == True)
    )
    tenants = result.scalars().all()

    for tenant in tenants:
        settings = tenant.settings or {}
        tenant_whatsapp = settings.get("whatsapp_number", "")

        tenant_digits = "".join(filter(str.isdigit, tenant_whatsapp))
        phone_digits = "".join(filter(str.isdigit, phone_number))

        if tenant_digits and tenant_digits == phone_digits:
            return tenant

    return None


async def get_tenant_by_gupshup_app(
    db: AsyncSession,
    app_name: str,
) -> Optional[Tenant]:
    """
    Busca tenant pelo nome do app no Gupshup.
    
    settings.gupshup_app_name = "meu-app"
    """
    result = await db.execute(
        select(Tenant).where(Tenant.active == True)
    )
    tenants = result.scalars().all()

    for tenant in tenants:
        settings = tenant.settings or {}
        tenant_app = settings.get("gupshup_app_name", "")

        if tenant_app and tenant_app == app_name:
            return tenant

    return None


async def send_response_async(
    gupshup: GupshupService,
    to: str,
    message: str,
):
    """Envia resposta em background."""
    try:
        result = await gupshup.send_text(to, message)
        if not result.success:
            logger.error(f"Erro ao enviar resposta: {result.error}")
    except Exception as e:
        logger.error(f"Exceção ao enviar resposta: {str(e)}")


# ==========================================
# MAIN WEBHOOK ENDPOINT
# ==========================================

@router.post("/gupshup")
async def gupshup_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_gupshup_signature: Optional[str] = Header(None, alias="x-gupshup-signature"),
):
    """
    WEBHOOK PRINCIPAL - multi-tenant

    1. Lê body e JSON
    2. Identifica tenant
    3. Cria GupshupService configurado para aquele tenant
    4. Valida assinatura individual
    5. Roteia evento (message/message-event/user-event)
    """
    try:
        body = await request.body()
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao ler payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Payload inválido")

    event_type = payload.get("type", "unknown")
    app_name = payload.get("app", "")

    

    # ==========================================
    # 1) Identificar tenant
    # ==========================================
    tenant: Optional[Tenant] = None

    if app_name:
        tenant = await get_tenant_by_gupshup_app(db, app_name)

    if not tenant:
        dest_phone = (
    payload.get("payload", {})
    .get("destination", "")
    .replace("+", "")
    .strip()
)

        if dest_phone:
            tenant = await get_tenant_by_phone(db, dest_phone)

    if not tenant:
        logger.error(f"Tenant não encontrado para webhook Gupshup. app={app_name}")
        return {"success": True, "ignored": True}

    # ==========================================
    # 2) Criar serviço Gupshup exclusivo do tenant
    # ==========================================
    settings = tenant.settings or {}
    gupshup = build_gupshup_service_from_settings(settings)

    # ==========================================
    # 3) Validar assinatura do webhook
    # ==========================================
    if x_gupshup_signature and gupshup.config.webhook_secret:
        if not gupshup.validate_webhook_signature(body, x_gupshup_signature):
            logger.warning(
                f"Assinatura inválida no webhook Gupshup (tenant={tenant.slug})"
            )
            raise HTTPException(status_code=401, detail="Assinatura inválida")

    logger.info(
    f"[{tenant.slug.upper()}] Evento Gupshup: {event_type}"
)


    # ==========================================
    # 4) Roteamento de eventos
    # ==========================================
    if event_type == "message":
        await handle_incoming_message(
            payload=payload,
            gupshup=gupshup,
            tenant=tenant,
            db=db,
            background_tasks=background_tasks,
        )

    elif event_type == "message-event":
        await handle_message_status(payload)

    elif event_type == "user-event":
        await handle_user_event(payload)

    else:
        logger.debug(f"Evento ignorado: {event_type}")

    return {"success": True}


# ==========================================
# PROCESSADORES DE EVENTOS
# ==========================================

async def handle_incoming_message(
    payload: dict,
    gupshup: GupshupService,
    tenant: Tenant,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
):
    """
    Processa mensagem recebida para um tenant específico.
    """
    parsed = gupshup.parse_incoming_message(payload)

    if not parsed:
        logger.warning("Mensagem não parseável")
        return

    logger.info(
        f"Mensagem de {parsed.sender_phone} para tenant={tenant.slug}: "
        f"{parsed.content[:80]}..."
    )

    try:
        result = await process_message(
            db=db,
            tenant_slug=tenant.slug,
            channel_type="whatsapp",
            external_id="".join(filter(str.isdigit, parsed.sender_phone)),
            content=parsed.content,
            sender_name=parsed.sender_name,
            sender_phone=parsed.sender_phone,
            source="whatsapp",
            campaign=None,
        )

        if result.get("success") and result.get("reply"):
            background_tasks.add_task(
                send_response_async,
                gupshup,
                parsed.sender_phone,
                result["reply"],
            )
            logger.info(
                f"Resposta enviada para {parsed.sender_phone} "
                f"(tenant={tenant.slug})"
            )

        elif not result.get("success"):
            logger.error(f"Erro no process_message: {result.get('error')}")

    except Exception as e:
        logger.error(f"Exceção ao processar mensagem: {str(e)}")


async def handle_message_status(payload: dict):
    """
    Processa update de status de envio (sent/delivered/read/failed)
    """
    gupshup = get_gupshup_service()
    status_info = gupshup.parse_status_update(payload)

    if status_info:
        logger.info(
            f"Status da mensagem {status_info.get('message_id')}: "
            f"{status_info.get('status')} -> {status_info.get('destination')}"
        )

        if status_info.get("status") == "failed":
            logger.error(f"Mensagem falhou: {status_info.get('error')}")


async def handle_user_event(payload: dict):
    """
    Processa opt-in/opt-out do usuário.
    """
    event_payload = payload.get("payload", {})
    event_type = event_payload.get("type")
    phone = event_payload.get("phone")

    logger.info(f"User event: {event_type} para {phone}")

    # Futuro: registrar opt-out no banco


# ==========================================
# VERIFICAÇÃO E HEALTHCHECK
# ==========================================

@router.get("/gupshup")
async def gupshup_webhook_verify(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    """
    Verificação do webhook (se necessário).
    """
    if hub_challenge:
        return int(hub_challenge)

    return {"status": "ok", "service": "gupshup-webhook"}


@router.get("/gupshup/health")
async def gupshup_health():
    """
    Health check do webhook Gupshup.
    """
    gupshup = get_gupshup_service()
    health = await gupshup.check_health()

    return {
        "status": "ok",
        "gupshup": health,
        "configured": gupshup.is_configured,
    }


