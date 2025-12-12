"""
ROTAS Z-API - Webhooks
======================
Recebe eventos do Z-API (mensagens, status, conexao)

Documentacao: https://developer.z-api.io/webhooks/introduction
"""

import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, Channel
from src.application.use_cases.process_message import process_message
from src.infrastructure.services.zapi_service import ZAPIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zapi", tags=["Z-API Webhooks"])


# =============================================================================
# WEBHOOK: MENSAGEM RECEBIDA
# =============================================================================

@router.post("/receive")
async def zapi_receive_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.json()

        logger.info(f"Z-API webhook recebido: {payload.get('phone')}")

        # Ignora grupos
        if payload.get("isGroup"):
            return {"status": "ignored", "reason": "group_message"}

        # Ignora mensagens enviadas pelo próprio bot
        if payload.get("fromMe"):
            return {"status": "ignored", "reason": "from_me"}

        phone = payload.get("phone")
        instance_id = payload.get("instanceId")
        sender_name = payload.get("pushName") or payload.get("senderName")

        if not phone or not instance_id:
            logger.warning("Payload incompleto")
            return {"status": "ignored", "reason": "invalid_payload"}

        # ===============================
        # EXTRAI TEXTO DA MENSAGEM
        # ===============================
        message_text = None

        if payload.get("text"):
            message_text = payload["text"].get("message")
        elif payload.get("image"):
            message_text = payload["image"].get("caption") or "[Imagem recebida]"
        elif payload.get("audio"):
            message_text = "[Áudio recebido]"
        elif payload.get("document"):
            message_text = payload["document"].get("caption") or "[Documento recebido]"
        elif payload.get("video"):
            message_text = payload["video"].get("caption") or "[Vídeo recebido]"
        elif payload.get("sticker"):
            message_text = "[Sticker recebido]"
        elif payload.get("location"):
            message_text = "[Localização recebida]"
        elif payload.get("contact"):
            message_text = "[Contato recebido]"
        elif payload.get("buttonsResponseMessage"):
            message_text = payload["buttonsResponseMessage"].get("selectedButtonId")
        elif payload.get("listResponseMessage"):
            message_text = payload["listResponseMessage"].get("title")

        if not message_text:
            return {"status": "ignored", "reason": "empty_message"}

        # ===============================
        # BUSCA CANAL PELO INSTANCE_ID
        # ===============================
        result = await db.execute(
            select(Channel)
            .where(Channel.type == "whatsapp")
            .where(Channel.active.is_(True))
            .where(Channel.config["zapi_instance_id"].astext == instance_id)
            .order_by(Channel.created_at.asc())
        )

        channel = result.scalars().first()

        if not channel:
            logger.error(f"Nenhum canal encontrado para instance_id={instance_id}")
            return {"status": "error", "reason": "channel_not_found"}

        # ===============================
        # BUSCA TENANT
        # ===============================
        result = await db.execute(
            select(Tenant)
            .where(Tenant.id == channel.tenant_id)
            .where(Tenant.active.is_(True))
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.error("Tenant não encontrado")
            return {"status": "error", "reason": "tenant_not_found"}

        logger.info(f"Mensagem atribuída ao tenant: {tenant.slug}")

        # ===============================
        # PROCESSA MENSAGEM (CORE)
        # ===============================
        result = await process_message(
            db=db,
            tenant_slug=tenant.slug,
            channel_type="whatsapp",
            external_id=phone,
            content=message_text,
            sender_name=sender_name,
            sender_phone=phone,
            source="zapi",
        )

        # ===============================
        # ENVIA RESPOSTA (SE EXISTIR)
        # ===============================
        if result.get("reply"):
            zapi = ZAPIService(
                instance_id=channel.config["zapi_instance_id"],
                token=channel.config["zapi_token"],
            )

            await zapi.send_text(
                phone=phone,
                message=result["reply"],
            )

        return {
            "status": "processed",
            "lead_id": result.get("lead_id"),
            "is_new": result.get("is_new_lead"),
            "qualification": result.get("qualification"),
        }

    except Exception:
        logger.exception("Erro crítico no webhook Z-API")
        raise


# =============================================================================
# WEBHOOK: STATUS DA MENSAGEM
# =============================================================================

@router.post("/status")
async def zapi_message_status(request: Request):
    payload = await request.json()
    logger.debug(f"Status Z-API recebido: {payload}")
    return {"status": "received"}


# =============================================================================
# WEBHOOK: CONECTADO
# =============================================================================

@router.post("/connect")
async def zapi_connected(request: Request):
    payload = await request.json()
    logger.info(f"Z-API conectado: {payload}")
    return {"status": "received"}


# =============================================================================
# WEBHOOK: DESCONECTADO
# =============================================================================

@router.post("/disconnect")
async def zapi_disconnected(request: Request):
    payload = await request.json()
    logger.warning(f"Z-API desconectado: {payload}")
    return {"status": "received"}


# =============================================================================
# ENDPOINTS GLOBAIS DESATIVADOS (MULTI-TENANT)
# =============================================================================

@router.get("/status-check")
async def disabled_status_check():
    return {
        "success": False,
        "error": "Endpoint desativado. Z-API agora é multi-tenant."
    }
