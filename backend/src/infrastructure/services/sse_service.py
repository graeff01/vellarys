"""
SSE Service - Server-Sent Events para Tempo Real
=================================================

Gerencia conexões SSE para atualizações em tempo real no CRM Inbox.

Eventos suportados:
- new_message: Nova mensagem recebida/enviada
- message_status: Status de entrega atualizado (✓✓)
- typing: Indicador de digitação
- lead_updated: Dados do lead alterados (status, tags, etc)
- handoff: Transferência de atendimento

Arquitetura:
- Múltiplas conexões por lead (vários vendedores vendo mesmo lead)
- Heartbeat a cada 30s para manter conexão
- Auto-cleanup em desconexão
"""
import asyncio
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SSEConnectionManager:
    """Gerenciador global de conexões SSE."""

    def __init__(self):
        # lead_id -> set de queues
        self._connections: Dict[int, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, lead_id: int) -> asyncio.Queue:
        """
        Registra nova conexão SSE para um lead.

        Returns:
            asyncio.Queue onde eventos serão enfileirados
        """
        async with self._lock:
            if lead_id not in self._connections:
                self._connections[lead_id] = set()

            queue = asyncio.Queue(maxsize=50)
            self._connections[lead_id].add(queue)

            logger.info(f"[SSE] Nova conexão para lead {lead_id}. Total: {len(self._connections[lead_id])}")
            return queue

    async def disconnect(self, lead_id: int, queue: asyncio.Queue):
        """Remove conexão quando cliente desconecta."""
        async with self._lock:
            if lead_id in self._connections:
                self._connections[lead_id].discard(queue)

                if not self._connections[lead_id]:
                    del self._connections[lead_id]
                    logger.info(f"[SSE] Todas conexões removidas para lead {lead_id}")
                else:
                    logger.info(f"[SSE] Conexão removida. Restantes: {len(self._connections[lead_id])}")

    async def broadcast(self, lead_id: int, event_type: str, data: Dict[str, Any]):
        """
        Envia evento para TODAS as conexões de um lead.

        Args:
            lead_id: ID do lead
            event_type: Tipo do evento (new_message, message_status, etc)
            data: Payload do evento
        """
        async with self._lock:
            if lead_id not in self._connections:
                logger.debug(f"[SSE] Sem conexões ativas para lead {lead_id}")
                return

            # Formata evento SSE
            event_data = {
                "type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Envia para todas as queues
            dead_queues = []
            for queue in self._connections[lead_id]:
                try:
                    # Non-blocking put (descarta se cheia)
                    queue.put_nowait(event_data)
                except asyncio.QueueFull:
                    logger.warning(f"[SSE] Queue cheia para lead {lead_id}, dropando evento")
                except Exception as e:
                    logger.error(f"[SSE] Erro ao enviar evento: {e}")
                    dead_queues.append(queue)

            # Limpa queues mortas
            for queue in dead_queues:
                self._connections[lead_id].discard(queue)

            logger.debug(f"[SSE] Evento '{event_type}' enviado para {len(self._connections[lead_id])} conexões")

    async def get_active_connections_count(self, lead_id: int) -> int:
        """Retorna número de conexões ativas para um lead."""
        async with self._lock:
            return len(self._connections.get(lead_id, set()))


# Singleton global
sse_manager = SSEConnectionManager()


# ============================================
# FUNÇÕES HELPER PARA BROADCAST
# ============================================

async def broadcast_new_message(lead_id: int, message_data: Dict[str, Any]):
    """Notifica nova mensagem."""
    await sse_manager.broadcast(lead_id, "new_message", message_data)


async def broadcast_message_status(lead_id: int, message_id: int, status: str, timestamp: Optional[str] = None):
    """Notifica mudança de status (sent → delivered → read)."""
    await sse_manager.broadcast(lead_id, "message_status", {
        "message_id": message_id,
        "status": status,
        "timestamp": timestamp or datetime.utcnow().isoformat()
    })


async def broadcast_typing_indicator(lead_id: int, is_typing: bool, user_name: str = "Cliente"):
    """Notifica que alguém está digitando."""
    await sse_manager.broadcast(lead_id, "typing", {
        "is_typing": is_typing,
        "user_name": user_name
    })


async def broadcast_lead_updated(lead_id: int, updated_fields: Dict[str, Any]):
    """Notifica que dados do lead foram alterados (status, tags, etc)."""
    await sse_manager.broadcast(lead_id, "lead_updated", updated_fields)


async def broadcast_handoff(lead_id: int, from_type: str, to_type: str, to_user_name: Optional[str] = None):
    """Notifica transferência de atendimento."""
    await sse_manager.broadcast(lead_id, "handoff", {
        "from": from_type,
        "to": to_type,
        "to_user_name": to_user_name
    })


# ============================================
# GENERATOR PARA FASTAPI
# ============================================

async def event_stream_generator(lead_id: int):
    """
    Generator assíncrono para endpoint SSE do FastAPI.

    Uso no endpoint:

    @router.get("/leads/{lead_id}/stream")
    async def stream_events(lead_id: int):
        return StreamingResponse(
            event_stream_generator(lead_id),
            media_type="text/event-stream"
        )
    """
    queue = await sse_manager.connect(lead_id)

    try:
        # Envia evento inicial de conexão
        yield f"data: {json.dumps({'type': 'connected', 'lead_id': lead_id})}\n\n"

        while True:
            try:
                # Aguarda evento ou timeout de 30s (heartbeat)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)

                # Envia evento no formato SSE
                yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                # Heartbeat para manter conexão viva
                yield f": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.info(f"[SSE] Cliente desconectou de lead {lead_id}")
    finally:
        await sse_manager.disconnect(lead_id, queue)
