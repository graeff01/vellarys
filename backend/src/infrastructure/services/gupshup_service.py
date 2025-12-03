"""
SERVIÇO GUPSHUP
================

Integração com Gupshup WhatsApp Business API.
Documentação: https://docs.gupshup.io/docs/whatsapp-api-documentation

Este serviço é uma "ponte" entre o Velaris e o WhatsApp via Gupshup.
Quando migrar para API direta do Meta, basta criar um novo serviço
seguindo a mesma interface.

FUNCIONALIDADES:
- Enviar mensagens de texto
- Enviar templates (mensagens pré-aprovadas)
- Enviar mídia (imagem, documento, áudio, vídeo)
- Validar assinatura do webhook
- Parsear payloads recebidos
"""

import hmac
import hashlib
import logging
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


# ==========================================
# ENUMS E TIPOS
# ==========================================

class GupshupMessageType(str, Enum):
    """Tipos de mensagem suportados pelo Gupshup."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"
    TEMPLATE = "template"


class GupshupEventType(str, Enum):
    """Tipos de evento recebidos do Gupshup."""
    MESSAGE = "message"
    MESSAGE_EVENT = "message-event"
    BILLING_EVENT = "billing-event"
    TEMPLATE_EVENT = "template-event"
    USER_EVENT = "user-event"


class GupshupMessageStatus(str, Enum):
    """Status de mensagem enviada."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    ENQUEUED = "enqueued"


# ==========================================
# DATA CLASSES
# ==========================================

@dataclass
class GupshupConfig:
    """Configuração do Gupshup."""
    api_key: str
    app_name: str
    source_phone: str  # Número do WhatsApp Business (com código país)
    webhook_secret: Optional[str] = None  # Para validar assinaturas
    base_url: str = "https://api.gupshup.io/wa/api/v1"
    
    @property
    def is_configured(self) -> bool:
        """Verifica se está configurado."""
        return bool(self.api_key and self.app_name and self.source_phone)


@dataclass
class ParsedIncomingMessage:
    """Mensagem recebida parseada para formato Velaris."""
    external_id: str  # ID único da conversa/contato
    sender_phone: str  # Número de quem enviou
    sender_name: Optional[str]  # Nome do contato (se disponível)
    content: str  # Conteúdo da mensagem
    message_type: str  # text, image, etc
    message_id: str  # ID da mensagem no Gupshup
    timestamp: datetime
    raw_payload: dict  # Payload original para debug
    
    # Mídia (se houver)
    media_url: Optional[str] = None
    media_caption: Optional[str] = None
    media_filename: Optional[str] = None


@dataclass 
class SendMessageResult:
    """Resultado do envio de mensagem."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None


# ==========================================
# SERVIÇO PRINCIPAL
# ==========================================

class GupshupService:
    """
    Serviço de integração com Gupshup WhatsApp API.
    
    Uso:
        config = GupshupConfig(
            api_key="sua-api-key",
            app_name="seu-app",
            source_phone="5511999999999"
        )
        service = GupshupService(config)
        
        # Enviar mensagem
        result = await service.send_text("5511888888888", "Olá!")
        
        # Parsear webhook
        message = service.parse_incoming_message(payload)
    """
    
    def __init__(self, config: GupshupConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Verifica se o serviço está configurado."""
        return self.config.is_configured
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP (lazy initialization)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "apikey": self.config.api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )
        return self._client
    
    async def close(self):
        """Fecha o cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    # ==========================================
    # ENVIO DE MENSAGENS
    # ==========================================
    
    async def send_text(
        self,
        to: str,
        message: str,
    ) -> SendMessageResult:
        """
        Envia mensagem de texto simples.
        
        Args:
            to: Número destino (ex: 5511999999999)
            message: Texto da mensagem
            
        Returns:
            SendMessageResult com status do envio
        """
        # Limpa número (só dígitos)
        to_clean = "".join(filter(str.isdigit, to))
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": message,
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def send_template(
        self,
        to: str,
        template_id: str,
        params: Optional[list[str]] = None,
    ) -> SendMessageResult:
        """
        Envia mensagem usando template pré-aprovado.
        
        Templates são necessários para iniciar conversas ou
        enviar mensagens após 24h de inatividade.
        
        Args:
            to: Número destino
            template_id: ID do template no Gupshup
            params: Lista de parâmetros para substituir no template
            
        Returns:
            SendMessageResult com status do envio
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        # Monta estrutura do template
        template_data: Dict[str, Any] = {
            "id": template_id,
            "params": params or [],
        }
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "template": str(template_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload, endpoint="/template/msg")
    
    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> SendMessageResult:
        """
        Envia imagem.
        
        Args:
            to: Número destino
            image_url: URL pública da imagem
            caption: Legenda opcional
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        message_data = {
            "type": "image",
            "originalUrl": image_url,
            "previewUrl": image_url,
        }
        if caption:
            message_data["caption"] = caption
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": str(message_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def send_document(
        self,
        to: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None,
    ) -> SendMessageResult:
        """
        Envia documento (PDF, etc).
        
        Args:
            to: Número destino
            document_url: URL pública do documento
            filename: Nome do arquivo
            caption: Legenda opcional
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        message_data = {
            "type": "file",
            "url": document_url,
            "filename": filename,
        }
        if caption:
            message_data["caption"] = caption
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": str(message_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def send_audio(
        self,
        to: str,
        audio_url: str,
    ) -> SendMessageResult:
        """
        Envia áudio.
        
        Args:
            to: Número destino
            audio_url: URL pública do áudio
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        message_data = {
            "type": "audio",
            "url": audio_url,
        }
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": str(message_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def send_video(
        self,
        to: str,
        video_url: str,
        caption: Optional[str] = None,
    ) -> SendMessageResult:
        """
        Envia vídeo.
        
        Args:
            to: Número destino
            video_url: URL pública do vídeo
            caption: Legenda opcional
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        message_data = {
            "type": "video",
            "url": video_url,
        }
        if caption:
            message_data["caption"] = caption
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": str(message_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> SendMessageResult:
        """
        Envia localização.
        
        Args:
            to: Número destino
            latitude: Latitude
            longitude: Longitude
            name: Nome do local (opcional)
            address: Endereço (opcional)
        """
        to_clean = "".join(filter(str.isdigit, to))
        
        message_data = {
            "type": "location",
            "longitude": longitude,
            "latitude": latitude,
        }
        if name:
            message_data["name"] = name
        if address:
            message_data["address"] = address
        
        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": str(message_data),
            "src.name": self.config.app_name,
        }
        
        return await self._send_request(payload)
    
    async def _send_request(
        self,
        payload: dict,
        endpoint: str = "/msg",
    ) -> SendMessageResult:
        """
        Envia requisição para o Gupshup.
        
        Args:
            payload: Dados da mensagem
            endpoint: Endpoint da API
            
        Returns:
            SendMessageResult
        """
        if not self.is_configured:
            logger.warning("GupshupService não configurado - modo mock")
            return SendMessageResult(
                success=True,
                message_id=f"mock_{payload.get('destination')}_{datetime.now().timestamp()}",
                raw_response={"mock": True, "payload": payload},
            )
        
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            client = await self._get_client()
            response = await client.post(url, data=payload)
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status") == "submitted":
                logger.info(f"Mensagem enviada para {payload.get('destination')}: {response_data.get('messageId')}")
                return SendMessageResult(
                    success=True,
                    message_id=response_data.get("messageId"),
                    raw_response=response_data,
                )
            else:
                error_msg = response_data.get("message", "Erro desconhecido")
                logger.error(f"Erro ao enviar mensagem: {error_msg}")
                return SendMessageResult(
                    success=False,
                    error=error_msg,
                    raw_response=response_data,
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout ao enviar mensagem para Gupshup")
            return SendMessageResult(
                success=False,
                error="Timeout na requisição",
            )
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar mensagem: {str(e)}")
            return SendMessageResult(
                success=False,
                error=str(e),
            )
    
    # ==========================================
    # PROCESSAMENTO DE WEBHOOK
    # ==========================================
    
    def validate_webhook_signature(
        self,
        payload_body: bytes,
        signature: str,
    ) -> bool:
        """
        Valida assinatura do webhook para segurança.
        
        Args:
            payload_body: Corpo da requisição em bytes
            signature: Assinatura recebida no header
            
        Returns:
            True se válido, False se inválido
        """
        if not self.config.webhook_secret:
            # Se não tem secret configurado, aceita tudo (dev mode)
            logger.warning("Webhook secret não configurado - aceitando todas as requisições")
            return True
        
        expected_signature = hmac.new(
            self.config.webhook_secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def parse_incoming_message(
        self,
        payload: dict,
    ) -> Optional[ParsedIncomingMessage]:
        """
        Converte payload do Gupshup para formato Velaris.
        
        Args:
            payload: Payload recebido do webhook
            
        Returns:
            ParsedIncomingMessage ou None se não for mensagem processável
        """
        try:
            # Verifica tipo de evento
            event_type = payload.get("type")
            
            if event_type != "message":
                logger.debug(f"Evento ignorado: {event_type}")
                return None
            
            # Extrai dados da mensagem
            message_payload = payload.get("payload", {})
            
            sender_phone = message_payload.get("source", "")
            sender_name = message_payload.get("sender", {}).get("name")
            message_id = message_payload.get("id", "")
            
            # Timestamp
            timestamp_str = payload.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromtimestamp(int(timestamp_str) / 1000)
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Extrai conteúdo baseado no tipo
            message_type = message_payload.get("type", "text")
            content = ""
            media_url = None
            media_caption = None
            media_filename = None
            
            if message_type == "text":
                content = message_payload.get("payload", {}).get("text", "")
                
            elif message_type == "image":
                media_url = message_payload.get("payload", {}).get("url")
                media_caption = message_payload.get("payload", {}).get("caption", "")
                content = media_caption or "[Imagem recebida]"
                
            elif message_type == "document":
                media_url = message_payload.get("payload", {}).get("url")
                media_filename = message_payload.get("payload", {}).get("filename")
                media_caption = message_payload.get("payload", {}).get("caption", "")
                content = media_caption or f"[Documento: {media_filename}]"
                
            elif message_type == "audio":
                media_url = message_payload.get("payload", {}).get("url")
                content = "[Áudio recebido]"
                
            elif message_type == "video":
                media_url = message_payload.get("payload", {}).get("url")
                media_caption = message_payload.get("payload", {}).get("caption", "")
                content = media_caption or "[Vídeo recebido]"
                
            elif message_type == "location":
                lat = message_payload.get("payload", {}).get("latitude")
                lon = message_payload.get("payload", {}).get("longitude")
                content = f"[Localização: {lat}, {lon}]"
                
            elif message_type == "contact":
                contact_name = message_payload.get("payload", {}).get("name", "")
                content = f"[Contato: {contact_name}]"
                
            elif message_type == "button_reply":
                # Resposta de botão interativo
                content = message_payload.get("payload", {}).get("title", "")
                
            elif message_type == "list_reply":
                # Resposta de lista interativa
                content = message_payload.get("payload", {}).get("title", "")
                
            else:
                content = f"[{message_type}]"
                logger.warning(f"Tipo de mensagem não tratado: {message_type}")
            
            return ParsedIncomingMessage(
                external_id=sender_phone,
                sender_phone=sender_phone,
                sender_name=sender_name,
                content=content,
                message_type=message_type,
                message_id=message_id,
                timestamp=timestamp,
                raw_payload=payload,
                media_url=media_url,
                media_caption=media_caption,
                media_filename=media_filename,
            )
            
        except Exception as e:
            logger.error(f"Erro ao parsear mensagem Gupshup: {str(e)}")
            logger.debug(f"Payload: {payload}")
            return None
    
    def parse_status_update(
        self,
        payload: dict,
    ) -> Optional[dict]:
        """
        Processa atualização de status de mensagem.
        
        Args:
            payload: Payload do evento message-event
            
        Returns:
            Dict com informações do status ou None
        """
        try:
            if payload.get("type") != "message-event":
                return None
            
            message_payload = payload.get("payload", {})
            
            return {
                "message_id": message_payload.get("gsId"),
                "destination": message_payload.get("destination"),
                "status": message_payload.get("type"),  # sent, delivered, read, failed
                "timestamp": payload.get("timestamp"),
                "error": message_payload.get("payload", {}).get("reason") if message_payload.get("type") == "failed" else None,
            }
            
        except Exception as e:
            logger.error(f"Erro ao parsear status update: {str(e)}")
            return None
    
    # ==========================================
    # UTILIDADES
    # ==========================================
    
    async def check_health(self) -> dict:
        """
        Verifica se a conexão com Gupshup está funcionando.
        
        Returns:
            Dict com status da conexão
        """
        if not self.is_configured:
            return {
                "status": "not_configured",
                "message": "Gupshup não configurado",
            }
        
        try:
            client = await self._get_client()
            response = await client.get(
                "https://api.gupshup.io/wa/health",
                timeout=10.0,
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "Conexão OK",
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Status code: {response.status_code}",
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }
    
    def format_phone_number(self, phone: str, country_code: str = "55") -> str:
        """
        Formata número de telefone para padrão internacional.
        
        Args:
            phone: Número (pode ter formatação)
            country_code: Código do país (default: 55 Brasil)
            
        Returns:
            Número formatado (ex: 5511999999999)
        """
        # Remove tudo que não é dígito
        digits = "".join(filter(str.isdigit, phone))
        
        # Se já começa com código do país
        if digits.startswith(country_code):
            return digits
        
        # Se começa com 0, remove
        if digits.startswith("0"):
            digits = digits[1:]
        
        # Adiciona código do país
        return f"{country_code}{digits}"


# ==========================================
# INSTÂNCIA GLOBAL E HELPERS
# ==========================================

# Instância global (configurada no startup)
_gupshup_service: Optional[GupshupService] = None


def get_gupshup_service() -> GupshupService:
    """Retorna instância global do serviço."""
    global _gupshup_service
    if _gupshup_service is None:
        # Cria com config vazia (modo mock)
        _gupshup_service = GupshupService(GupshupConfig(
            api_key="",
            app_name="",
            source_phone="",
        ))
    return _gupshup_service


def configure_gupshup_service(config: GupshupConfig) -> GupshupService:
    """Configura e retorna instância global."""
    global _gupshup_service
    _gupshup_service = GupshupService(config)
    logger.info(f"GupshupService configurado - App: {config.app_name}")
    return _gupshup_service


async def send_gupshup_message(to: str, message: str) -> SendMessageResult:
    """Helper para enviar mensagem de texto."""
    service = get_gupshup_service()
    return await service.send_text(to, message)