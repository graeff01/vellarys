"""
SERVIÇO DE WHATSAPP (MULTI-TENANT)
=================================

Responsável por enviar mensagens via WhatsApp
usando o provider configurado no Channel.

Provider atual:
- Z-API (produção)

Estrutura preparada para:
- Evolution API
- WhatsApp Official API
"""

import logging
from typing import Optional

from src.domain.entities import Channel
from src.infrastructure.services.zapi_service import ZAPIService

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Serviço de envio de mensagens WhatsApp
    baseado no Channel (multi-tenant).
    """

    def __init__(self, channel: Channel):
        self.channel = channel
        self.provider = channel.config.get("provider", "zapi")

    async def send_text(
        self,
        to: str,
        message: str,
    ) -> dict:
        """
        Envia mensagem de texto.
        """

        # Sanitiza número
        to_clean = "".join(filter(str.isdigit, to))

        if self.provider == "zapi":
            return await self._send_zapi(to_clean, message)

        raise RuntimeError(f"Provider WhatsApp não suportado: {self.provider}")

    async def _send_zapi(self, to: str, message: str) -> dict:
        """
        Envia mensagem via Z-API.
        """

        instance_id = self.channel.config.get("zapi_instance_id")
        token = self.channel.config.get("zapi_token")

        if not instance_id or not token:
            logger.error("Z-API não configurado corretamente no channel")
            return {
                "success": False,
                "error": "Z-API não configurado no channel"
            }

        zapi = ZAPIService(
            instance_id=instance_id,
            token=token,
        )

        await zapi.send_text(
            phone=to,
            message=message,
        )

        return {
            "success": True,
            "provider": "zapi",
            "to": to,
        }
