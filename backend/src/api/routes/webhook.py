"""
ROTAS: WEBHOOK
===============

Endpoint para receber mensagens de canais externos.
WhatsApp, site, etc. enviam mensagens para cá.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.api.schemas import WebhookMessage, WebhookResponse
from src.application.use_cases import process_message

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/message", response_model=WebhookResponse)
async def receive_message(
    payload: WebhookMessage,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagem de um canal externo.
    
    Este endpoint é chamado por:
    - Integrações WhatsApp (Evolution API, Z-API, etc)
    - Widget de chat do site
    - Outras integrações futuras
    
    O payload deve conter:
    - tenant_slug: identificador do tenant
    - channel_type: tipo do canal (whatsapp, web)
    - external_id: ID único do contato no canal
    - content: conteúdo da mensagem
    """
    
    result = await process_message(
        db=db,
        tenant_slug=payload.tenant_slug,
        channel_type=payload.channel_type,
        external_id=payload.external_id,
        content=payload.content,
        sender_name=payload.sender_name,
        sender_phone=payload.sender_phone,
        source=payload.source or "organic",
        campaign=payload.campaign,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao processar mensagem"))
    
    return WebhookResponse(
        success=True,
        reply=result["reply"],
        lead_id=result["lead_id"],
        is_new_lead=result["is_new_lead"],
        qualification=result.get("qualification"),
    )


@router.get("/health")
async def webhook_health():
    """Health check do webhook."""
    return {"status": "ok", "service": "webhook"}
