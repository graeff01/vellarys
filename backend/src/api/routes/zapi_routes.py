"""
ROTAS Z-API - Webhooks
======================
Recebe eventos do Z-API (mensagens, status, conexao)

Documentacao: https://developer.z-api.io/webhooks/introduction
"""

import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, or_
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

        phone = payload.get("phone")
        instance_id = payload.get("instanceId")
        sender_name = payload.get("pushName") or payload.get("senderName")

        logger.info(f"📩 Z-API webhook recebido | phone={phone} | instance={instance_id}")

        # --------------------------------------------------
        # Ignora mensagens inválidas
        # --------------------------------------------------
        if payload.get("isGroup"):
            return {"status": "ignored", "reason": "group_message"}

        if payload.get("fromMe"):
            return {"status": "ignored", "reason": "from_me"}

        if not phone or not instance_id:
            logger.warning("Payload incompleto")
            return {"status": "ignored", "reason": "invalid_payload"}

        # --------------------------------------------------
        # Extrai texto da mensagem
        # --------------------------------------------------
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

        # --------------------------------------------------
        # Busca CANAL pelo instance_id (fallback seguro)
        # --------------------------------------------------
        result = await db.execute(
            select(Channel)
            .where(Channel.type == "whatsapp")
            .where(Channel.active.is_(True))
            .where(
                or_(
                    Channel.config["zapi_instance_id"].astext == instance_id,
                    Channel.config["instance_id"].astext == instance_id,
                )
            )
            .order_by(Channel.created_at.asc())
        )

        channel = result.scalars().first()

        if not channel:
            logger.error(f"❌ Nenhum canal encontrado para instance_id={instance_id}")
            return {"status": "error", "reason": "channel_not_found"}

        # --------------------------------------------------
        # Busca TENANT
        # --------------------------------------------------
        result = await db.execute(
            select(Tenant)
            .where(Tenant.id == channel.tenant_id)
            .where(Tenant.active.is_(True))
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.error(f"❌ Tenant não encontrado para channel_id={channel.id}")
            return {"status": "error", "reason": "tenant_not_found"}

        logger.info(f"🏷️ Mensagem atribuída ao tenant: {tenant.slug}")

        # --------------------------------------------------
        # Processa mensagem no CORE
        # --------------------------------------------------
        core_result = await process_message(
            db=db,
            tenant_slug=tenant.slug,
            channel_type="whatsapp",
            external_id=phone,
            content=message_text,
            sender_name=sender_name,
            sender_phone=phone,
            source="zapi",
        )

        # --------------------------------------------------
        # Envia resposta (se existir)
        # --------------------------------------------------
        if core_result.get("reply"):
            instance = (
                channel.config.get("zapi_instance_id")
                or channel.config.get("instance_id")
            )
            token = channel.config.get("token") or channel.config.get("zapi_token")

            if instance and token:
                zapi = ZAPIService(
                    instance_id=instance,
                    token=token,
                )

                await zapi.send_text(
                    phone=phone,
                    message=core_result["reply"],
                )
            else:
                logger.error(
                    f"❌ Credenciais Z-API ausentes no channel {channel.id}"
                )

        return {
            "status": "processed",
            "lead_id": core_result.get("lead_id"),
            "is_new": core_result.get("is_new_lead"),
            "qualification": core_result.get("qualification"),
        }

    except Exception:
        logger.exception("🔥 Erro crítico no webhook Z-API")
        raise


# =============================================================================
# WEBHOOK: STATUS DA MENSAGEM
# =============================================================================
@router.post("/status")
async def zapi_message_status(request: Request):
    payload = await request.json()
    logger.debug(f"📦 Status Z-API recebido: {payload}")
    return {"status": "received"}


# =============================================================================
# WEBHOOK: CONECTADO
# =============================================================================
@router.post("/connect")
async def zapi_connected(request: Request):
    payload = await request.json()
    logger.info(f"✅ Z-API conectado: {payload}")
    return {"status": "received"}


# =============================================================================
# WEBHOOK: DESCONECTADO
# =============================================================================
@router.post("/disconnect")
async def zapi_disconnected(request: Request):
    payload = await request.json()
    logger.warning(f"⚠️ Z-API desconectado: {payload}")
    return {"status": "received"}


# =============================================================================
# ENDPOINT DESATIVADO (GLOBAL)
# =============================================================================
@router.get("/status-check")
async def disabled_status_check():
    return {
        "success": False,
        "error": "Endpoint desativado. Z-API opera exclusivamente em modo multi-tenant."
    }
