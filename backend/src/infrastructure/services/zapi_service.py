"""
SERVIÇO Z-API - Integração WhatsApp
===================================
Alternativa não-oficial ao 360dialog/Gupshup
Mais barato, mensagens ilimitadas
"""

import httpx
import logging
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ZAPIService:
    """Cliente para Z-API WhatsApp."""
    
    def __init__(self, instance_id: str, token: str):
        self.instance_id = instance_id
        self.token = token
        self.base_url = f"https://api.z-api.io/instances/{instance_id}/token/{token}"
    
    async def send_text(self, phone: str, message: str) -> dict:
        """
        Envia mensagem de texto.
        
        Args:
            phone: Número com DDI (ex: 5551999999999)
            message: Texto da mensagem
        """
        url = f"{self.base_url}/send-text"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info(f"✅ Z-API: Mensagem enviada para {phone}")
                return {"success": True, "data": result}
            except Exception as e:
                logger.error(f"❌ Z-API erro: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_image(self, phone: str, image_url: str, caption: str = "") -> dict:
        """Envia imagem com legenda opcional."""
        url = f"{self.base_url}/send-image"
        
        payload = {
            "phone": self._format_phone(phone),
            "image": image_url,
            "caption": caption
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"❌ Z-API erro imagem: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_document(self, phone: str, document_url: str, filename: str) -> dict:
        """Envia documento/arquivo."""
        url = f"{self.base_url}/send-document/{document_url}"
        
        payload = {
            "phone": self._format_phone(phone),
            "document": document_url,
            "fileName": filename
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"❌ Z-API erro documento: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_button_list(self, phone: str, message: str, buttons: list) -> dict:
        """Envia mensagem com botões."""
        url = f"{self.base_url}/send-button-list"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message,
            "buttonList": {
                "buttons": [{"label": btn} for btn in buttons]
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"❌ Z-API erro botões: {e}")
                return {"success": False, "error": str(e)}
    
    async def check_connection(self) -> dict:
        """Verifica se instância está conectada."""
        url = f"{self.base_url}/status"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10)
                data = response.json()
                connected = data.get("connected", False)
                return {"connected": connected, "data": data}
            except Exception as e:
                logger.error(f"❌ Z-API status erro: {e}")
                return {"connected": False, "error": str(e)}
    
    def _format_phone(self, phone: str) -> str:
        """Remove caracteres não numéricos do telefone."""
        return ''.join(filter(str.isdigit, phone))


# Função helper para criar instância
def get_zapi_client(instance_id: str = None, token: str = None) -> ZAPIService:
    """Cria cliente Z-API com credenciais do settings ou passadas."""
    return ZAPIService(
        instance_id=instance_id or settings.zapi_instance_id,
        token=token or settings.zapi_token
    )