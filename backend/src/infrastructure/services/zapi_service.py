"""
SERVIÇO Z-API - Integração WhatsApp (MULTI-TENANT)
=================================================
Adapter oficial Z-API desacoplado de settings globais.
Cada instância representa UM tenant.
"""

import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ZAPIService:
    """Cliente Z-API isolado por tenant."""

    def __init__(self, instance_id: str, token: str):
        if not instance_id or not token:
            raise ValueError("Z-API instance_id e token são obrigatórios")

        self.instance_id = instance_id
        self.token = token
        self.base_url = (
            f"https://api.z-api.io/instances/{instance_id}/token/{token}"
        )

    # ==========================
    # HTTP HELPERS
    # ==========================
    async def _post(self, endpoint: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/{endpoint}",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Z-API POST error [{endpoint}]: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _get(self, endpoint: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.base_url}/{endpoint}"
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Z-API GET error [{endpoint}]: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ==========================
    # SENDERS
    # ==========================
    async def send_text(
        self,
        phone: str,
        message: str,
        delay: int = 0,
    ) -> dict:
        payload = {
            "phone": self._format_phone(phone),
            "message": message,
        }

        if delay > 0:
            payload["delayMessage"] = delay

        return await self._post("send-text", payload)

    async def send_image(
        self,
        phone: str,
        image_url: str,
        caption: str = "",
    ) -> dict:
        return await self._post(
            "send-image",
            {
                "phone": self._format_phone(phone),
                "image": image_url,
                "caption": caption,
            },
        )

    async def send_document(
        self,
        phone: str,
        document_url: str,
        filename: str,
    ) -> dict:
        return await self._post(
            "send-document",
            {
                "phone": self._format_phone(phone),
                "document": document_url,
                "fileName": filename,
            },
        )

    # ==========================
    # STATUS
    # ==========================
    async def check_connection(self) -> dict:
        data = await self._get("status")
        return {
            "connected": data.get("connected", False),
            "data": data,
            "instance_id": self.instance_id,
        }

    # ==========================
    # UTILS
    # ==========================
    @staticmethod
    def _format_phone(phone: str) -> str:
        return "".join(filter(str.isdigit, phone))
