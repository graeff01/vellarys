"""
ROTAS: WEBHOOK
===============
Endpoint para receber mensagens de canais externos.
WhatsApp, site, etc. enviam mensagens para cá.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.api.schemas import WebhookMessage, WebhookResponse
from src.application.use_cases.process_message import process_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/message", response_model=WebhookResponse)
async def receive_message(
    payload: WebhookMessage,
    verify_token: str = None, # Pode vir via query param ou header
    db: AsyncSession = Depends(get_db),
):
    from src.config import get_settings
    settings = get_settings()
    
    # 🛡️ PROTEÇÃO DE WEBHOOK
    # Se o token não bater, bloqueia (exceto se estivermos em modo de desenvolvimento SEM token configurado)
    if settings.webhook_verify_token and verify_token != settings.webhook_verify_token:
        # Tenta pegar do header se não veio no query param
        from fastapi import Header
        logger.warning(f"🚫 Tentativa de Webhook não autorizada! Token inválido.")
        raise HTTPException(status_code=401, detail="Invalid verify token")
        
    # 🔥 LOG CRÍTICO — PROVA DO TEXTO REAL QUE CHEGA
    logger.info(f"[WEBHOOK] Recebido de {payload.sender_phone} para tenant {payload.tenant_slug}")

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
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Erro ao processar mensagem")
        )
    
    return WebhookResponse(
        success=True,
        reply=result["reply"],
        lead_id=result["lead_id"],
        is_new_lead=result["is_new_lead"],
        qualification=result.get("qualification"),
        empreendimento_id=result.get("empreendimento_id"),
        empreendimento_nome=result.get("empreendimento_nome"),
    )


@router.get("/health")
async def webhook_health():
    return {"status": "ok", "service": "webhook"}
