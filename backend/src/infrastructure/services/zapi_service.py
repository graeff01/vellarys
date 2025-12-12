"""
SERVIÇO Z-API — WhatsApp (MULTI-TENANT)
======================================

Cliente oficial Z-API desacoplado de settings globais.
Cada instância representa UM channel / tenant.

Usado por:
- WhatsAppService
- Webhooks Z-API
"""

import httpx
import logging

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
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Z-API HTTP error [{self.instance_id}] {e.response.status_code} — {e.response.text}"
            )
            return {
                "success": False,
                "error": e.response.text,
                "status_code": e.response.status_code,
            }

        except Exception as e:
            logger.exception(
                f"Z-API POST error [{self.instance_id}] endpoint={endpoint}"
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def _get(self, endpoint: str) -> dict:
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.exception(
                f"Z-API GET error [{self.instance_id}] endpoint={endpoint}"
            )
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
            "success": True,
            "connected": data.get("connected", False),
            "instance_id": self.instance_id,
            "raw": data,
        }

    # ==========================
    # UTILS
    # ==========================
    @staticmethod
    def _format_phone(phone: str) -> str:
        return "".join(filter(str.isdigit, phone))
