"""
SERVIÇO Z-API - Integração WhatsApp
===================================
Adapter oficial de WhatsApp para o core do sistema.
"""

import httpx
import logging
from typing import List, Dict, Optional
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CLIENTE Z-API
# =============================================================================
class ZAPIService:
    """Cliente para integração com Z-API WhatsApp."""

    def __init__(self, instance_id: str, token: str):
        if not instance_id or not token:
            raise ValueError("Z-API instance_id ou token não configurados")

        self.base_url = f"https://api.z-api.io/instances/{instance_id}/token/{token}"

    async def _post(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/{endpoint}", json=payload)
            response.raise_for_status()
            return response.json()

    async def _get(self, endpoint: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base_url}/{endpoint}")
            response.raise_for_status()
            return response.json()

    async def send_text(self, phone: str, message: str) -> dict:
        return await self._post(
            "send-text",
            {
                "phone": self._format_phone(phone),
                "message": message,
            },
        )

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> dict:
        return await self._post(
            "send-image",
            {
                "phone": self._format_phone(phone),
                "image": image_url,
                "caption": caption,
            },
        )

    async def send_document(
        self, phone: str, document_url: str, filename: str
    ) -> dict:
        return await self._post(
            "send-document",
            {
                "phone": self._format_phone(phone),
                "document": document_url,
                "fileName": filename,
            },
        )

    async def send_button_list(
        self, phone: str, message: str, buttons: List[str]
    ) -> dict:
        return await self._post(
            "send-button-list",
            {
                "phone": self._format_phone(phone),
                "message": message,
                "buttonList": {
                    "buttons": [{"label": btn} for btn in buttons]
                },
            },
        )

    async def check_connection(self) -> dict:
        data = await self._get("status")
        return {
            "connected": data.get("connected", False),
            "data": data,
        }

    @staticmethod
    def _format_phone(phone: str) -> str:
        return "".join(filter(str.isdigit, phone))


# =============================================================================
# FACTORY
# =============================================================================
def get_zapi_client(
    instance_id: Optional[str] = None,
    token: Optional[str] = None,
) -> ZAPIService:
    return ZAPIService(
        instance_id=instance_id or settings.zapi_instance_id,
        token=token or settings.zapi_token,
    )


# =============================================================================
# FUNÇÕES PADRÃO ESPERADAS PELO CORE (CONTRATO)
# =============================================================================
async def send_whatsapp_message(phone: str, message: str) -> dict:
    """
    Envio padrão de mensagem WhatsApp (texto).
    Usado pelo core do sistema.
    """
    client = get_zapi_client()
    return await client.send_text(phone, message)


async def check_zapi_connection() -> dict:
    """
    Verifica se a instância Z-API está conectada.
    """
    client = get_zapi_client()
    return await client.check_connection()
