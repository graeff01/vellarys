"""
SCHEMAS GUPSHUP
================

Schemas de validação para payloads do Gupshup.
Baseado na documentação: https://docs.gupshup.io/docs/whatsapp-api-documentation
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


# ==========================================
# PAYLOAD DE ENTRADA (Webhook)
# ==========================================

class GupshupSender(BaseModel):
    """Informações do remetente."""
    phone: str = Field(..., description="Número do remetente")
    name: Optional[str] = Field(None, description="Nome do remetente")
    country_code: Optional[str] = None
    dial_code: Optional[str] = None


class GupshupMessagePayload(BaseModel):
    """Payload interno da mensagem."""
    text: Optional[str] = None
    url: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    name: Optional[str] = None
    address: Optional[str] = None
    title: Optional[str] = None  # Para button_reply e list_reply
    id: Optional[str] = None  # ID do botão/item selecionado


class GupshupMessageContext(BaseModel):
    """Contexto da mensagem (se for resposta a outra)."""
    gsId: Optional[str] = None
    id: Optional[str] = None


class GupshupIncomingMessage(BaseModel):
    """Mensagem recebida no webhook."""
    id: str = Field(..., description="ID da mensagem")
    source: str = Field(..., description="Número do remetente")
    type: str = Field(..., description="Tipo: text, image, etc")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sender: Optional[GupshupSender] = None
    context: Optional[GupshupMessageContext] = None


class GupshupWebhookPayload(BaseModel):
    """
    Payload completo recebido do Gupshup.
    
    Tipos de evento:
    - message: Nova mensagem recebida
    - message-event: Status de mensagem enviada (sent, delivered, read, failed)
    - user-event: Eventos do usuário (opt-in, opt-out)
    - template-event: Eventos de template
    - billing-event: Eventos de cobrança
    """
    app: str = Field(..., description="Nome do app no Gupshup")
    timestamp: str = Field(..., description="Timestamp em milissegundos")
    version: int = Field(default=2, description="Versão da API")
    type: str = Field(..., description="Tipo do evento")
    payload: Dict[str, Any] = Field(..., description="Dados do evento")
    
    class Config:
        extra = "allow"  # Permite campos extras


class GupshupMessageEventPayload(BaseModel):
    """Payload de evento de status de mensagem."""
    id: Optional[str] = None
    gsId: Optional[str] = None
    type: str  # sent, delivered, read, failed, enqueued
    destination: str
    payload: Optional[Dict[str, Any]] = None


# ==========================================
# PAYLOAD DE SAÍDA (Envio)
# ==========================================

class GupshupSendTextRequest(BaseModel):
    """Request para enviar mensagem de texto."""
    to: str = Field(..., description="Número destino")
    message: str = Field(..., description="Texto da mensagem")


class GupshupSendTemplateRequest(BaseModel):
    """Request para enviar template."""
    to: str = Field(..., description="Número destino")
    template_id: str = Field(..., description="ID do template")
    params: Optional[List[str]] = Field(default_factory=list, description="Parâmetros do template")


class GupshupSendMediaRequest(BaseModel):
    """Request para enviar mídia."""
    to: str = Field(..., description="Número destino")
    media_url: str = Field(..., description="URL da mídia")
    media_type: str = Field(..., description="Tipo: image, document, audio, video")
    caption: Optional[str] = Field(None, description="Legenda")
    filename: Optional[str] = Field(None, description="Nome do arquivo (para documentos)")


# ==========================================
# RESPOSTAS
# ==========================================

class GupshupSendResponse(BaseModel):
    """Resposta do envio de mensagem."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class GupshupWebhookResponse(BaseModel):
    """Resposta para o webhook (ACK)."""
    success: bool = True
    message: str = "OK"


# ==========================================
# CONVERSÃO PARA FORMATO VELARIS
# ==========================================

class VelarisWebhookPayload(BaseModel):
    """
    Payload convertido para o formato interno do Velaris.
    Usado para integrar com process_message().
    """
    tenant_slug: str
    channel_type: str = "whatsapp"
    external_id: str  # Número do remetente
    content: str
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    source: str = "whatsapp"
    campaign: Optional[str] = None
    
    # Metadados extras
    message_id: Optional[str] = None
    message_type: Optional[str] = None
    media_url: Optional[str] = None
    timestamp: Optional[datetime] = None