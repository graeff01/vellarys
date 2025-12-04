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
import json
from typing import Optional, Dict, Any
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
        to_clean = "".join(filter(str.isdigit, to))

        message_payload = {
            "type": "text",
            "text": message,
        }

        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "message": json.dumps(message_payload),
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

        template_data: Dict[str, Any] = {
            "id": template_id,
            "params": params or [],
        }

        payload = {
            "channel": "whatsapp",
            "source": self.config.source_phone,
            "destination": to_clean,
            "template": json.dumps(template_data),
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
            "message": json.dumps(message_data),
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
            "message": json.dumps(message_data),
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
            "message": json.dumps(message_data),
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
            "message": json.dumps(message_data),
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
            "message": json.dumps(message_data),
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
                logger.info(
                    f"Mensagem enviada para {payload.get('destination')}: "
                    f"{response_data.get('messageId')}"
                )
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
        """
        if not self.config.webhook_secret:
            logger.warning(
                "Webhook secret não configurado - aceitando todas as requisições"
            )
            return True

        expected_signature = hmac.new(
            self.config.webhook_secret.encode(),
            payload_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def parse_incoming_message(
        self,
        payload: dict,
    ) -> Optional[ParsedIncomingMessage]:
        """
        Converte payload do Gupshup para formato Velaris.
        """
        try:
            event_type = payload.get("type")

            if event_type != "message":
                logger.debug(f"Evento ignorado: {event_type}")
                return None

            message_payload = payload.get("payload", {})

            sender_phone = message_payload.get("source", "")
            sender_name = message_payload.get("sender", {}).get("name")
            message_id = message_payload.get("id", "")

            timestamp_str = payload.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromtimestamp(int(timestamp_str) / 1000)
                except Exception:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            message_type = message_payload.get("type", "text")
            content = ""
            media_url = None
            media_caption = None
            media_filename = None

            payload_inner = message_payload.get("payload", {}) or {}

            if message_type == "text":
                content = payload_inner.get("text", "")

            elif message_type == "image":
                media_url = payload_inner.get("url")
                media_caption = payload_inner.get("caption", "")
                content = media_caption or "[Imagem recebida]"

            elif message_type == "document":
                media_url = payload_inner.get("url")
                media_filename = payload_inner.get("filename")
                media_caption = payload_inner.get("caption", "")
                content = media_caption or f"[Documento: {media_filename}]"

            elif message_type == "audio":
                media_url = payload_inner.get("url")
                content = "[Áudio recebido]"

            elif message_type == "video":
                media_url = payload_inner.get("url")
                media_caption = payload_inner.get("caption", "")
                content = media_caption or "[Vídeo recebido]"

            elif message_type == "location":
                lat = payload_inner.get("latitude")
                lon = payload_inner.get("longitude")
                content = f"[Localização: {lat}, {lon}]"

            elif message_type == "contact":
                contact_name = payload_inner.get("name", "")
                content = f"[Contato: {contact_name}]"

            elif message_type in {"button_reply", "list_reply"}:
                content = payload_inner.get("title", "")

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
        """
        try:
            if payload.get("type") != "message-event":
                return None

            message_payload = payload.get("payload", {})

            return {
                "message_id": message_payload.get("gsId"),
                "destination": message_payload.get("destination"),
                "status": message_payload.get("type"),
                "timestamp": payload.get("timestamp"),
                "error": (
                    message_payload.get("payload", {}).get("reason")
                    if message_payload.get("type") == "failed"
                    else None
                ),
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
        """
        digits = "".join(filter(str.isdigit, phone))

        if digits.startswith(country_code):
            return digits

        if digits.startswith("0"):
            digits = digits[1:]

        return f"{country_code}{digits}"


# ==========================================
# INSTÂNCIA GLOBAL E HELPERS
# (mantidos para compatibilidade / dev)
# ==========================================

_gupshup_service: Optional[GupshupService] = None


def get_gupshup_service() -> GupshupService:
    """Retorna instância global do serviço (modo legacy/mock)."""
    global _gupshup_service
    if _gupshup_service is None:
        _gupshup_service = GupshupService(
            GupshupConfig(
                api_key="",
                app_name="",
                source_phone="",
            )
        )
    return _gupshup_service


def configure_gupshup_service(config: GupshupConfig) -> GupshupService:
    """Configura e retorna instância global."""
    global _gupshup_service
    _gupshup_service = GupshupService(config)
    logger.info(f"GupshupService configurado - App: {config.app_name}")
    return _gupshup_service


async def send_gupshup_message(to: str, message: str) -> SendMessageResult:
    """Helper para enviar mensagem de texto usando instância global."""
    service = get_gupshup_service()
    return await service.send_text(to, message)


# ==========================================
# HELPER MULTI-TENANT
# ==========================================

def build_gupshup_service_from_settings(settings: Dict[str, Any]) -> GupshupService:
    """
    Cria uma instância de GupshupService a partir de settings do tenant.

    Espera chaves:
      - gupshup_api_key
      - gupshup_app_name
      - whatsapp_number
      - gupshup_webhook_secret
    """
    config = GupshupConfig(
        api_key=settings.get("gupshup_api_key", "") or "",
        app_name=settings.get("gupshup_app_name", "") or "",
        source_phone=settings.get("whatsapp_number", "") or "",
        webhook_secret=settings.get("gupshup_webhook_secret"),
    )
    return GupshupService(config)
