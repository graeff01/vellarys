"""
SERVICO Z-API - Integracao WhatsApp
===================================
Alternativa nao-oficial ao 360dialog/Gupshup
Mensagens ilimitadas por mensalidade fixa

Documentacao: https://developer.z-api.io/
"""

import httpx
import logging
from typing import Optional
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ZAPIService:
    """Cliente para Z-API WhatsApp."""
    
    def __init__(self, instance_id: str = None, token: str = None, client_token: str = None):
        self.instance_id = instance_id or getattr(settings, 'zapi_instance_id', None)
        self.token = token or getattr(settings, 'zapi_token', None)
        self.client_token = client_token or getattr(settings, 'zapi_client_token', None)
        
        if self.instance_id and self.token:
            self.base_url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.token}"
        else:
            self.base_url = None
            logger.warning("Z-API: Credenciais nao configuradas")
    
    def _get_headers(self) -> dict:
        """Retorna headers para as requisicoes, incluindo Client-Token se configurado."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.client_token:
            headers["Client-Token"] = self.client_token
        return headers
    
    def is_configured(self) -> bool:
        """Verifica se o servico esta configurado."""
        return self.base_url is not None
    
    async def send_text(self, phone: str, message: str, delay_message: int = 0) -> dict:
        """
        Envia mensagem de texto.
        
        Args:
            phone: Numero com DDI (ex: 5551999999999)
            message: Texto da mensagem
            delay_message: Delay em segundos antes de enviar (0-15)
        
        Returns:
            {"success": True/False, "data": {...}, "error": "..."}
        """
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-text"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message
        }
        
        if delay_message > 0:
            payload["delayMessage"] = min(delay_message, 15)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Z-API: Mensagem enviada para {phone[:8]}***")
                return {"success": True, "data": result}
            except httpx.HTTPStatusError as e:
                logger.error(f"Z-API HTTP erro: {e.response.status_code} - {e.response.text}")
                return {"success": False, "error": f"HTTP {e.response.status_code}"}
            except Exception as e:
                logger.error(f"Z-API erro: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_image(
        self, 
        phone: str, 
        image_url: str, 
        caption: str = ""
    ) -> dict:
        """Envia imagem com legenda opcional."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-image"
        
        payload = {
            "phone": self._format_phone(phone),
            "image": image_url,
            "caption": caption
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro imagem: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_document(
        self, 
        phone: str, 
        document_url: str, 
        filename: str
    ) -> dict:
        """Envia documento/arquivo."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-document/url"
        
        payload = {
            "phone": self._format_phone(phone),
            "document": document_url,
            "fileName": filename
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro documento: {e}")
                return {"success": False, "error": str(e)}

    async def send_location(
        self, 
        phone: str, 
        latitude: float, 
        longitude: float,
        title: str = "",
        address: str = ""
    ) -> dict:
        """Envia localizacao (GPS)."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-location"
        
        payload = {
            "phone": self._format_phone(phone),
            "latitude": str(latitude),
            "longitude": str(longitude),
            "title": title,
            "address": address
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro localizacao: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_audio(self, phone: str, audio_url: str) -> dict:
        """Envia audio via URL."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}

        url = f"{self.base_url}/send-audio"

        payload = {
            "phone": self._format_phone(phone),
            "audio": audio_url
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro audio: {e}")
                return {"success": False, "error": str(e)}

    async def send_audio_base64(
        self,
        phone: str,
        audio_base64: str,
        mime_type: str = "audio/ogg"
    ) -> dict:
        """
        Envia audio via base64.

        Args:
            phone: Numero do destinatario (ex: 5551999999999)
            audio_base64: Audio codificado em base64
            mime_type: Tipo do audio (audio/ogg, audio/mp3, audio/mpeg)

        Returns:
            {"success": True/False, "data": {...}, "error": "..."}
        """
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}

        url = f"{self.base_url}/send-audio"

        # Formato base64 com data URI
        audio_data = f"data:{mime_type};base64,{audio_base64}"

        payload = {
            "phone": self._format_phone(phone),
            "audio": audio_data
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60  # Timeout maior para audio
                )
                response.raise_for_status()
                logger.info(f"Z-API: Audio enviado para {phone[:8]}***")
                return {"success": True, "data": response.json()}
            except httpx.HTTPStatusError as e:
                logger.error(f"Z-API audio base64 HTTP erro: {e.response.status_code} - {e.response.text}")
                return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
            except Exception as e:
                logger.error(f"Z-API erro audio base64: {e}")
                return {"success": False, "error": str(e)}

    async def send_ptt(
        self,
        phone: str,
        audio_base64: str,
        mime_type: str = "audio/ogg"
    ) -> dict:
        """
        Envia audio como PTT (Push-to-Talk / mensagem de voz).
        Aparece como "bolinha" de audio no WhatsApp.

        Args:
            phone: Numero do destinatario
            audio_base64: Audio codificado em base64
            mime_type: Tipo do audio

        Returns:
            {"success": True/False, "data": {...}, "error": "..."}
        """
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}

        # Endpoint específico para PTT (áudio de voz)
        url = f"{self.base_url}/send-audio"

        # Formato base64 com data URI
        audio_data = f"data:{mime_type};base64,{audio_base64}"

        payload = {
            "phone": self._format_phone(phone),
            "audio": audio_data,
            "messageId": None  # Opcional: para rastrear a mensagem
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60
                )
                response.raise_for_status()
                logger.info(f"Z-API: PTT enviado para {phone[:8]}***")
                return {"success": True, "data": response.json()}
            except httpx.HTTPStatusError as e:
                logger.error(f"Z-API PTT HTTP erro: {e.response.status_code}")
                return {"success": False, "error": f"HTTP {e.response.status_code}"}
            except Exception as e:
                logger.error(f"Z-API erro PTT: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_link(
        self, 
        phone: str, 
        message: str, 
        link_url: str,
        title: str = "",
        description: str = "",
        image_url: str = ""
    ) -> dict:
        """Envia mensagem com preview de link."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-link"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message,
            "linkUrl": link_url,
            "title": title,
            "linkDescription": description,
            "image": image_url
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro link: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_button_list(
        self, 
        phone: str, 
        message: str, 
        buttons: list,
        title: str = "",
        footer: str = ""
    ) -> dict:
        """
        Envia mensagem com botoes.
        
        Args:
            phone: Numero do destinatario
            message: Mensagem principal
            buttons: Lista de labels dos botoes (max 3)
            title: Titulo opcional
            footer: Rodape opcional
        """
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-button-list"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message,
            "buttonList": {
                "buttons": [{"label": btn[:20]} for btn in buttons[:3]]
            }
        }
        
        if title:
            payload["title"] = title[:60]
        if footer:
            payload["footer"] = footer[:60]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro botoes: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_list_menu(
        self,
        phone: str,
        message: str,
        button_label: str,
        sections: list
    ) -> dict:
        """
        Envia lista de opcoes (menu).
        
        Args:
            phone: Numero do destinatario
            message: Mensagem principal
            button_label: Texto do botao que abre a lista
            sections: Lista de secoes com opcoes
                      [{"title": "Secao 1", "rows": [{"title": "Opcao 1", "description": "Desc"}]}]
        """
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/send-option-list"
        
        payload = {
            "phone": self._format_phone(phone),
            "message": message,
            "optionList": {
                "title": "Menu",
                "buttonLabel": button_label,
                "options": sections
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API erro lista: {e}")
                return {"success": False, "error": str(e)}
    
    async def check_connection(self) -> dict:
        """Verifica se instancia esta conectada."""
        if not self.is_configured():
            return {"connected": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/status"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(),
                    timeout=10
                )
                data = response.json()
                connected = data.get("connected", False)
                return {"connected": connected, "data": data}
            except Exception as e:
                logger.error(f"Z-API status erro: {e}")
                return {"connected": False, "error": str(e)}
    
    async def get_qrcode(self) -> dict:
        """Obtem QR Code para conexao."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/qr-code/image"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(),
                    timeout=30
                )
                data = response.json()
                return {"success": True, "data": data}
            except Exception as e:
                logger.error(f"Z-API QR Code erro: {e}")
                return {"success": False, "error": str(e)}
    
    async def disconnect(self) -> dict:
        """Desconecta a instancia."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/disconnect"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(),
                    timeout=10
                )
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API disconnect erro: {e}")
                return {"success": False, "error": str(e)}
    
    async def restart(self) -> dict:
        """Reinicia a instancia."""
        if not self.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        url = f"{self.base_url}/restart"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(),
                    timeout=30
                )
                return {"success": True, "data": response.json()}
            except Exception as e:
                logger.error(f"Z-API restart erro: {e}")
                return {"success": False, "error": str(e)}
    
    def _format_phone(self, phone: str) -> str:
        """Remove caracteres nao numericos do telefone."""
        clean = ''.join(filter(str.isdigit, str(phone)))
        
        # Garante que tem DDI do Brasil
        if len(clean) == 11:  # DDD + 9 digitos
            clean = "55" + clean
        elif len(clean) == 10:  # DDD + 8 digitos (fixo)
            clean = "55" + clean
        
        return clean


# ============================================
# FUNCAO HELPER GLOBAL
# ============================================

_zapi_client: Optional[ZAPIService] = None

def get_zapi_client(
    instance_id: str = None, 
    token: str = None,
    client_token: str = None,
    force_new: bool = False
) -> ZAPIService:
    """
    Obtem cliente Z-API (singleton ou novo).
    
    Args:
        instance_id: ID da instancia (opcional, usa settings)
        token: Token da instancia (opcional, usa settings)
        client_token: Client-Token de seguranca (opcional, usa settings)
        force_new: Forca criacao de nova instancia
    
    Returns:
        ZAPIService configurado
    """
    global _zapi_client
    
    if instance_id or token or client_token or force_new:
        return ZAPIService(instance_id=instance_id, token=token, client_token=client_token)
    
    if _zapi_client is None:
        _zapi_client = ZAPIService()
    
    return _zapi_client


# ============================================
# FUNCOES AUXILIARES
# ============================================

async def send_whatsapp_message(
    phone: str, 
    message: str,
    instance_id: str = None,
    token: str = None,
    client_token: str = None
) -> dict:
    """
    Funcao simplificada para enviar mensagem WhatsApp.
    
    Args:
        phone: Numero do destinatario
        message: Texto da mensagem
        instance_id: ID da instancia Z-API (opcional)
        token: Token da instancia (opcional)
        client_token: Client-Token de seguranca (opcional)
    
    Returns:
        {"success": True/False, "error": "..."}
    """
    client = get_zapi_client(instance_id=instance_id, token=token, client_token=client_token)
    return await client.send_text(phone, message)


async def check_zapi_connection(
    instance_id: str = None,
    token: str = None,
    client_token: str = None
) -> bool:
    """
    Verifica se Z-API esta conectado.
    
    Returns:
        True se conectado, False caso contrario
    """
    client = get_zapi_client(instance_id=instance_id, token=token, client_token=client_token)
    result = await client.check_connection()
    return result.get("connected", False)