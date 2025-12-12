"""
Z-API Service
=============

Responsável por enviar mensagens via Z-API
Documentação: https://developer.z-api.io
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ZAPIService:
    def __init__(
        self,
        instance_id: str,
        token: str,
        base_url: str = "https://api.z-api.io",
    ):
        self.instance_id = instance_id
        self.token = token
        self.base_url = base_url.rstrip("/")

    # ======================================================
    # MÉTODO PADRÃO (IGUAL GUPSHUP)
    # ======================================================
    async def send_text(self, phone: str, message: str) -> bool:
        """
        Envia mensagem de texto simples via Z-API
        """
        phone_clean = "".join(filter(str.isdigit, phone))

        url = (
            f"{self.base_url}/instances/"
            f"{self.instance_id}/token/{self.token}/send-text"
        )

        payload = {
            "phone": phone_clean,
            "message": message,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload)

            if response.status_code in (200, 201):
                logger.info(
                    f"📤 Z-API mensagem enviada | phone={phone_clean}"
                )
                return True

            logger.error(
                f"❌ Z-API erro {response.status_code} — {response.text}"
            )
            return False

        except Exception as e:
            logger.exception("🔥 Erro ao enviar mensagem via Z-API")
            return False
