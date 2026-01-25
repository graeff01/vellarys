"""
Message Status Service
=======================

Processa webhooks do Z-API para atualizar status de mensagens.

Status possíveis:
- sent: Enviada ao WhatsApp
- delivered: Entregue ao dispositivo do lead (✓✓)
- read: Lida pelo lead (✓✓ azul)
- failed: Falha no envio

Webhooks Z-API:
- MESSAGE_RECEIVED: Nova mensagem do lead
- MESSAGE_DELIVERED: Mensagem entregue
- MESSAGE_READ: Mensagem lida
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from ...domain.entities.models import Message, Lead
from .sse_service import broadcast_message_status

logger = logging.getLogger(__name__)


class MessageStatusService:
    """Serviço para processar status de mensagens."""

    async def process_status_webhook(
        self,
        db: AsyncSession,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Processa webhook do Z-API com atualização de status.

        Formato esperado do webhook:
        {
            "event": "MESSAGE_DELIVERED" | "MESSAGE_READ",
            "messageId": "3EB...",
            "timestamp": "2026-01-25T10:00:00Z",
            "phone": "5511999999999"
        }

        Returns:
            True se processado com sucesso
        """
        try:
            event = webhook_data.get("event")
            whatsapp_message_id = webhook_data.get("messageId")
            timestamp_str = webhook_data.get("timestamp")

            if not whatsapp_message_id:
                logger.warning("[MessageStatus] Webhook sem messageId")
                return False

            # Converte timestamp
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except Exception as e:
                    logger.error(f"[MessageStatus] Erro ao parsear timestamp: {e}")

            # Mapeia evento para status
            status_map = {
                "MESSAGE_DELIVERED": "delivered",
                "MESSAGE_READ": "read",
                "MESSAGE_FAILED": "failed"
            }

            new_status = status_map.get(event)
            if not new_status:
                logger.debug(f"[MessageStatus] Evento ignorado: {event}")
                return False

            # Busca mensagem no banco
            stmt = select(Message).where(Message.whatsapp_message_id == whatsapp_message_id)
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()

            if not message:
                logger.warning(f"[MessageStatus] Mensagem não encontrada: {whatsapp_message_id}")
                return False

            # Atualiza status
            update_data = {"status": new_status}

            if new_status == "delivered" and not message.delivered_at:
                update_data["delivered_at"] = timestamp or datetime.utcnow()

            if new_status == "read" and not message.read_at:
                update_data["read_at"] = timestamp or datetime.utcnow()
                # Se foi lida, também foi entregue
                if not message.delivered_at:
                    update_data["delivered_at"] = timestamp or datetime.utcnow()

            # Update no banco
            stmt = (
                update(Message)
                .where(Message.id == message.id)
                .values(**update_data)
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"[MessageStatus] Mensagem {message.id} → {new_status}")

            # Broadcast via SSE para clientes conectados
            await broadcast_message_status(
                lead_id=message.lead_id,
                message_id=message.id,
                status=new_status,
                timestamp=update_data.get("delivered_at") or update_data.get("read_at")
            )

            return True

        except Exception as e:
            logger.error(f"[MessageStatus] Erro ao processar webhook: {e}", exc_info=True)
            return False

    async def update_message_status(
        self,
        db: AsyncSession,
        message_id: int,
        status: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Atualiza status de mensagem manualmente.

        Usado quando recebemos confirmação direta do Z-API após envio.
        """
        try:
            # Busca mensagem
            stmt = select(Message).where(Message.id == message_id)
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()

            if not message:
                logger.warning(f"[MessageStatus] Mensagem {message_id} não encontrada")
                return

            # Prepara update
            update_data = {"status": status}

            if status == "delivered":
                update_data["delivered_at"] = timestamp or datetime.utcnow()

            if status == "read":
                update_data["read_at"] = timestamp or datetime.utcnow()
                if not message.delivered_at:
                    update_data["delivered_at"] = timestamp or datetime.utcnow()

            # Atualiza
            stmt = (
                update(Message)
                .where(Message.id == message_id)
                .values(**update_data)
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"[MessageStatus] Mensagem {message_id} atualizada para {status}")

            # Broadcast
            await broadcast_message_status(
                lead_id=message.lead_id,
                message_id=message_id,
                status=status,
                timestamp=(timestamp or datetime.utcnow()).isoformat()
            )

        except Exception as e:
            logger.error(f"[MessageStatus] Erro ao atualizar status: {e}", exc_info=True)

    async def mark_as_sent(
        self,
        db: AsyncSession,
        message_id: int,
        whatsapp_message_id: str
    ):
        """
        Marca mensagem como enviada e registra ID do WhatsApp.

        Chamado imediatamente após envio bem-sucedido via Z-API.
        """
        try:
            stmt = (
                update(Message)
                .where(Message.id == message_id)
                .values(
                    status="sent",
                    whatsapp_message_id=whatsapp_message_id
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"[MessageStatus] Mensagem {message_id} marcada como enviada")

            # Busca lead_id para broadcast
            stmt = select(Message.lead_id).where(Message.id == message_id)
            result = await db.execute(stmt)
            lead_id = result.scalar_one_or_none()

            if lead_id:
                await broadcast_message_status(
                    lead_id=lead_id,
                    message_id=message_id,
                    status="sent"
                )

        except Exception as e:
            logger.error(f"[MessageStatus] Erro ao marcar como enviada: {e}", exc_info=True)


# Singleton global
message_status_service = MessageStatusService()
