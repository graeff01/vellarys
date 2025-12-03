"""
ROTAS: WEBHOOK GUPSHUP
=======================

Endpoint específico para receber mensagens do Gupshup.
Converte o formato Gupshup para o formato interno do Velaris.

FLUXO:
1. Gupshup envia POST com mensagem
2. Validamos assinatura (segurança)
3. Parseamos para formato Velaris
4. Chamamos process_message()
5. Enviamos resposta da IA via Gupshup
6. Retornamos ACK para Gupshup

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
from src.domain.entities import Tenant, Channel
from src.application.use_cases import process_message
from src.infrastructure.services.gupshup_service import (
    get_gupshup_service,
    GupshupService,
    ParsedIncomingMessage,
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
    
    O número do WhatsApp Business é armazenado nas settings do tenant:
    settings.whatsapp_number = "5511999999999"
    """
    # Busca todos os tenants ativos
    result = await db.execute(
        select(Tenant).where(Tenant.active == True)
    )
    tenants = result.scalars().all()
    
    # Procura o tenant com esse número configurado
    for tenant in tenants:
        settings = tenant.settings or {}
        tenant_whatsapp = settings.get("whatsapp_number", "")
        
        # Compara só os dígitos
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
    
    O app_name é armazenado nas settings do tenant:
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
# ENDPOINTS
# ==========================================

@router.post("/gupshup")
async def gupshup_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_gupshup_signature: Optional[str] = Header(None, alias="x-gupshup-signature"),
):
    """
    Recebe mensagens do Gupshup.
    
    Este endpoint:
    1. Valida a assinatura do webhook (se configurado)
    2. Identifica o tenant pelo app_name ou número
    3. Processa a mensagem com a IA
    4. Envia a resposta via Gupshup
    5. Retorna ACK imediato para o Gupshup
    
    Headers esperados:
    - Content-Type: application/json
    - x-gupshup-signature: HMAC signature (opcional)
    """
    # 1. Lê o body
    try:
        body = await request.body()
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao ler payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Payload inválido")
    
    # 2. Pega serviço Gupshup
    gupshup = get_gupshup_service()
    
    # 3. Valida assinatura (se configurado)
    if x_gupshup_signature and gupshup.config.webhook_secret:
        if not gupshup.validate_webhook_signature(body, x_gupshup_signature):
            logger.warning("Assinatura inválida no webhook Gupshup")
            raise HTTPException(status_code=401, detail="Assinatura inválida")
    
    # 4. Log do evento
    event_type = payload.get("type", "unknown")
    logger.info(f"Webhook Gupshup recebido: {event_type}")
    
    # 5. Processa baseado no tipo de evento
    if event_type == "message":
        # Nova mensagem recebida
        await handle_incoming_message(
            payload=payload,
            gupshup=gupshup,
            db=db,
            background_tasks=background_tasks,
        )
        
    elif event_type == "message-event":
        # Status de mensagem enviada (sent, delivered, read, failed)
        await handle_message_status(payload)
        
    elif event_type == "user-event":
        # Opt-in/opt-out do usuário
        await handle_user_event(payload)
        
    else:
        logger.debug(f"Evento ignorado: {event_type}")
    
    # 6. Retorna ACK imediato
    return {"success": True}


async def handle_incoming_message(
    payload: dict,
    gupshup: GupshupService,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
):
    """
    Processa mensagem recebida.
    """
    # 1. Parseia a mensagem
    parsed = gupshup.parse_incoming_message(payload)
    
    if not parsed:
        logger.warning("Mensagem não parseável")
        return
    
    logger.info(f"Mensagem de {parsed.sender_phone}: {parsed.content[:50]}...")
    
    # 2. Identifica o tenant
    app_name = payload.get("app", "")
    tenant = await get_tenant_by_gupshup_app(db, app_name)
    
    if not tenant:
        # Tenta pelo número destino (se disponível no payload)
        dest_phone = payload.get("payload", {}).get("destination", "")
        if dest_phone:
            tenant = await get_tenant_by_phone(db, dest_phone)
    
    if not tenant:
        logger.error(f"Tenant não encontrado para app: {app_name}")
        # Envia mensagem genérica
        background_tasks.add_task(
            send_response_async,
            gupshup,
            parsed.sender_phone,
            "Desculpe, não foi possível processar sua mensagem. Tente novamente mais tarde.",
        )
        return
    
    # 3. Processa com a IA
    try:
        result = await process_message(
            db=db,
            tenant_slug=tenant.slug,
            channel_type="whatsapp",
            external_id=parsed.sender_phone,
            content=parsed.content,
            sender_name=parsed.sender_name,
            sender_phone=parsed.sender_phone,
            source="whatsapp",
            campaign=None,
        )
        
        # 4. Envia resposta (se houver)
        if result.get("success") and result.get("reply"):
            background_tasks.add_task(
                send_response_async,
                gupshup,
                parsed.sender_phone,
                result["reply"],
            )
            logger.info(f"Resposta enviada para {parsed.sender_phone}")
        
        elif not result.get("success"):
            logger.error(f"Erro no process_message: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Exceção ao processar mensagem: {str(e)}")
        # Não envia mensagem de erro para não confundir o usuário


async def handle_message_status(payload: dict):
    """
    Processa atualização de status de mensagem enviada.
    
    Status possíveis:
    - enqueued: Na fila para envio
    - sent: Enviada para o WhatsApp
    - delivered: Entregue ao destinatário
    - read: Lida pelo destinatário
    - failed: Falha no envio
    """
    gupshup = get_gupshup_service()
    status_info = gupshup.parse_status_update(payload)
    
    if status_info:
        logger.info(
            f"Status da mensagem {status_info.get('message_id')}: "
            f"{status_info.get('status')} para {status_info.get('destination')}"
        )
        
        # Se falhou, loga o erro
        if status_info.get("status") == "failed":
            logger.error(f"Mensagem falhou: {status_info.get('error')}")
        
        # TODO: Atualizar status no banco (Message.status)
        # Isso permite mostrar no dashboard se mensagem foi entregue/lida


async def handle_user_event(payload: dict):
    """
    Processa eventos do usuário (opt-in/opt-out).
    
    Eventos:
    - opted-in: Usuário aceitou receber mensagens
    - opted-out: Usuário não quer mais receber mensagens
    """
    event_payload = payload.get("payload", {})
    event_type = event_payload.get("type")
    phone = event_payload.get("phone")
    
    logger.info(f"User event: {event_type} para {phone}")
    
    # TODO: Atualizar Lead.opted_out no banco se necessário


@router.get("/gupshup")
async def gupshup_webhook_verify(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    """
    Verificação do webhook (se Gupshup solicitar).
    
    Alguns providers fazem uma verificação GET antes de ativar o webhook.
    """
    # Retorna o challenge para verificação
    if hub_challenge:
        return int(hub_challenge)
    
    return {"status": "ok", "service": "gupshup-webhook"}


@router.get("/gupshup/health")
async def gupshup_health():
    """
    Health check do webhook Gupshup.
    Verifica se o serviço está configurado e funcionando.
    """
    gupshup = get_gupshup_service()
    health = await gupshup.check_health()
    
    return {
        "status": "ok",
        "gupshup": health,
        "configured": gupshup.is_configured,
    }