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
from src.infrastructure.services.zapi_service import ZAPIService, get_zapi_client

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

        instance_id = self.channel.config.get("zapi_instance_id") or self.channel.config.get("instance_id")
        token = self.channel.config.get("zapi_token") or self.channel.config.get("token")
        client_token = self.channel.config.get("zapi_client_token") or self.channel.config.get("client_token")

        if not instance_id or not token:
            logger.error("Z-API não configurado corretamente no channel")
            return {
                "success": False,
                "error": "Z-API não configurado no channel"
            }

        zapi = ZAPIService(
            instance_id=instance_id,
            token=token,
            client_token=client_token,
        )

        result = await zapi.send_text(
            phone=to,
            message=message,
        )

        return {
            "success": result.get("success", False),
            "provider": "zapi",
            "to": to,
            "data": result.get("data"),
            "error": result.get("error"),
        }


# =============================================================================
# FUNÇÃO HELPER GLOBAL (usada pelo handoff_service)
# =============================================================================

async def send_whatsapp_message(
    to: str,
    message: str,
    instance_id: str = None,
    token: str = None,
    client_token: str = None,
) -> dict:
    """
    Função helper para enviar mensagem WhatsApp via Z-API.
    
    Usa credenciais das variáveis de ambiente se não forem passadas.
    
    Args:
        to: Número do destinatário (com DDI, ex: 5551999999999)
        message: Texto da mensagem
        instance_id: ID da instância Z-API (opcional)
        token: Token da instância Z-API (opcional)
        client_token: Client-Token de segurança (opcional)
    
    Returns:
        {"success": True/False, "error": "...", "data": {...}}
    """
    try:
        # Sanitiza número
        to_clean = "".join(filter(str.isdigit, str(to)))
        
        # Garante DDI do Brasil
        if len(to_clean) == 11:
            to_clean = "55" + to_clean
        elif len(to_clean) == 10:
            to_clean = "55" + to_clean
        
        # Obtém cliente Z-API
        zapi = get_zapi_client(
            instance_id=instance_id,
            token=token,
            client_token=client_token,
        )
        
        if not zapi.is_configured():
            logger.error("Z-API não configurado - verifique ZAPI_INSTANCE_ID e ZAPI_TOKEN")
            return {
                "success": False,
                "error": "Z-API não configurado. Verifique as variáveis de ambiente.",
            }
        
        # Envia mensagem
        result = await zapi.send_text(
            phone=to_clean,
            message=message,
            delay_message=2,  # Pequeno delay para parecer mais natural
        )
        
        if result.get("success"):
            logger.info(f"✅ WhatsApp enviado para {to_clean[:8]}***")
            return {
                "success": True,
                "data": result.get("data"),
            }
        else:
            error = result.get("error", "Erro desconhecido")
            logger.error(f"❌ Erro ao enviar WhatsApp: {error}")
            return {
                "success": False,
                "error": error,
            }
    
    except Exception as e:
        logger.error(f"❌ Exceção ao enviar WhatsApp: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def check_whatsapp_connection(
    instance_id: str = None,
    token: str = None,
    client_token: str = None,
) -> dict:
    """
    Verifica se a conexão WhatsApp (Z-API) está ativa.
    
    Returns:
        {"connected": True/False, "error": "..."}
    """
    try:
        zapi = get_zapi_client(
            instance_id=instance_id,
            token=token,
            client_token=client_token,
        )
        
        if not zapi.is_configured():
            return {
                "connected": False,
                "error": "Z-API não configurado",
            }
        
        result = await zapi.check_connection()
        
        return {
            "connected": result.get("connected", False),
            "data": result.get("data"),
            "error": result.get("error"),
        }
    
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }


async def get_profile_picture(
    phone: str,
    instance_id: str = None,
    token: str = None,
    client_token: str = None,
) -> dict:
    """
    Busca foto de perfil do WhatsApp de um contato.

    Args:
        phone: Número do destinatário (com DDI, ex: 5551999999999)
        instance_id: ID da instância Z-API (opcional)
        token: Token da instância Z-API (opcional)
        client_token: Client-Token de segurança (opcional)

    Returns:
        {"success": True/False, "url": "https://...", "error": "..."}
    """
    try:
        # Sanitiza número
        to_clean = "".join(filter(str.isdigit, str(phone)))

        # Garante DDI do Brasil
        if len(to_clean) == 11:
            to_clean = "55" + to_clean
        elif len(to_clean) == 10:
            to_clean = "55" + to_clean

        # Obtém cliente Z-API
        zapi = get_zapi_client(
            instance_id=instance_id,
            token=token,
            client_token=client_token,
        )

        if not zapi.is_configured():
            logger.error("Z-API não configurado - verifique ZAPI_INSTANCE_ID e ZAPI_TOKEN")
            return {
                "success": False,
                "error": "Z-API não configurado",
            }

        # Busca foto de perfil
        result = await zapi.get_profile_picture(phone=to_clean)

        if result.get("success"):
            logger.info(f"✅ Foto de perfil obtida para {to_clean[:8]}***")
            return {
                "success": True,
                "url": result.get("url"),
            }
        else:
            logger.warning(f"⚠️ Sem foto de perfil para {to_clean[:8]}***")
            return {
                "success": False,
                "error": result.get("error", "Sem foto de perfil"),
            }

    except Exception as e:
        logger.error(f"❌ Exceção ao buscar foto de perfil: {e}")
        return {
            "success": False,
            "error": str(e),
        }