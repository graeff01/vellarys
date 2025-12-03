"""
SERVIÇO DE WHATSAPP
====================

Preparado para integração com WhatsApp Business API.
Por enquanto apenas simula o envio.

INTEGRAÇÃO FUTURA:
- WhatsApp Business API (oficial)
- Evolution API
- Z-API
- Outros providers
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Serviço de integração com WhatsApp.
    Abstrai o provider específico.
    """
    
    def __init__(self, config: dict = None):
        """
        Inicializa o serviço.
        
        config pode conter:
        - provider: "official" | "evolution" | "z-api"
        - api_key: chave da API
        - phone_number_id: ID do número (API oficial)
        - instance_id: ID da instância (Evolution/Z-API)
        """
        self.config = config or {}
        self.provider = self.config.get("provider", "mock")
        self.is_configured = self._check_configuration()
    
    def _check_configuration(self) -> bool:
        """Verifica se o serviço está configurado."""
        if self.provider == "mock":
            return True
        
        if self.provider == "official":
            return bool(
                self.config.get("api_key") and 
                self.config.get("phone_number_id")
            )
        
        if self.provider in ["evolution", "z-api"]:
            return bool(
                self.config.get("api_key") and
                self.config.get("instance_id")
            )
        
        return False
    
    async def send_message(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None,
    ) -> dict:
        """
        Envia mensagem para um número de WhatsApp.
        
        Args:
            to: Número de destino (ex: 5511999999999)
            message: Texto da mensagem
            media_url: URL de mídia opcional
        
        Returns:
            {"success": True/False, "message_id": "...", "error": "..."}
        """
        # Remove caracteres não numéricos
        to_clean = "".join(filter(str.isdigit, to))
        
        if self.provider == "mock":
            return await self._send_mock(to_clean, message)
        
        elif self.provider == "official":
            return await self._send_official(to_clean, message, media_url)
        
        elif self.provider == "evolution":
            return await self._send_evolution(to_clean, message, media_url)
        
        else:
            return {"success": False, "error": f"Provider não suportado: {self.provider}"}
    
    async def _send_mock(self, to: str, message: str) -> dict:
        """Simula envio (para desenvolvimento)."""
        logger.info(f"""
        ========== WHATSAPP (MOCK) ==========
        Para: {to}
        Mensagem: {message[:100]}...
        =====================================
        """)
        
        return {
            "success": True,
            "message_id": f"mock_{to}_{id(message)}",
            "provider": "mock",
            "note": "Mensagem simulada - integrar com WhatsApp API para envio real"
        }
    
    async def _send_official(
        self, 
        to: str, 
        message: str, 
        media_url: Optional[str] = None
    ) -> dict:
        """
        Envia via WhatsApp Business API (oficial).
        
        Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api
        """
        # TODO: Implementar quando tiver a API oficial
        # 
        # import httpx
        # 
        # url = f"https://graph.facebook.com/v17.0/{self.config['phone_number_id']}/messages"
        # headers = {
        #     "Authorization": f"Bearer {self.config['api_key']}",
        #     "Content-Type": "application/json",
        # }
        # payload = {
        #     "messaging_product": "whatsapp",
        #     "to": to,
        #     "type": "text",
        #     "text": {"body": message}
        # }
        # 
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(url, json=payload, headers=headers)
        #     ...
        
        logger.warning("WhatsApp Official API não implementada ainda")
        return {"success": False, "error": "API oficial não implementada"}
    
    async def _send_evolution(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None
    ) -> dict:
        """
        Envia via Evolution API.
        
        Documentação: https://doc.evolution-api.com
        """
        # TODO: Implementar quando configurar Evolution API
        #
        # import httpx
        #
        # url = f"{self.config['base_url']}/message/sendText/{self.config['instance_id']}"
        # headers = {"apikey": self.config['api_key']}
        # payload = {
        #     "number": to,
        #     "text": message
        # }
        #
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(url, json=payload, headers=headers)
        #     ...
        
        logger.warning("Evolution API não implementada ainda")
        return {"success": False, "error": "Evolution API não implementada"}


# Instância global (será configurada pelo tenant)
whatsapp_service = WhatsAppService()


async def send_whatsapp_message(to: str, message: str) -> dict:
    """Função helper para enviar mensagem."""
    return await whatsapp_service.send_message(to, message)