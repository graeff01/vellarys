"""
SCHEMAS DE VALIDAÇÃO (VERSÃO CORRIGIDA)
========================================

Define a estrutura de dados de entrada e saída da API.
Pydantic valida automaticamente os dados.

CORREÇÕES:
- MessageResponse com campos Optional
- Adicionado from_attributes para compatibilidade ORM
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# WEBHOOK - Receber mensagens
# ============================================

class WebhookMessage(BaseModel):
    """Mensagem recebida via webhook."""
    model_config = ConfigDict(extra="allow")
    
    tenant_slug: str = Field(..., description="Identificador do tenant")
    channel_type: str = Field(..., description="Tipo do canal: whatsapp, web")
    external_id: str = Field(..., description="ID do contato na plataforma (ex: número WhatsApp)")
    content: str = Field(..., description="Conteúdo da mensagem")
    
    # Opcionais - podem vir do canal
    sender_name: Optional[str] = Field(None, description="Nome do remetente se disponível")
    sender_phone: Optional[str] = Field(None, description="Telefone se disponível")
    
    # Rastreamento
    campaign: Optional[str] = Field(None, description="Campanha de origem")
    source: Optional[str] = Field(None, description="Fonte: organic, paid, referral")


class WebhookResponse(BaseModel):
    """Resposta do webhook."""
    
    success: bool
    reply: Optional[str] = Field(None, description="Resposta da IA para enviar ao lead")
    lead_id: Optional[int] = None
    is_new_lead: bool = False
    qualification: Optional[str] = None
    empreendimento_id: Optional[int] = None
    empreendimento_nome: Optional[str] = None

# ============================================
# SELLER (Vendedor) - Resumo para exibir no Lead
# ============================================

class SellerSummary(BaseModel):
    """Resumo do vendedor para exibir em listas."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    whatsapp: Optional[str] = None


# ============================================
# LEAD
# ============================================

class LeadBase(BaseModel):
    """Campos base do lead."""
    
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    custom_data: dict = Field(default_factory=dict)
    source: str = "organic"
    campaign: Optional[str] = None


class LeadCreate(LeadBase):
    """Dados para criar lead manualmente."""
    
    channel_id: Optional[int] = None


class LeadUpdate(BaseModel):
    """Dados para atualizar lead."""
    
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    custom_data: Optional[dict] = None
    qualification: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None


class LeadResponse(LeadBase):
    """Lead completo na resposta."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    channel_id: Optional[int] = None
    external_id: Optional[str] = None
    qualification: Optional[str] = None  # ✅ CORRIGIDO: Pode ser None
    status: Optional[str] = None  # ✅ CORRIGIDO: Pode ser None
    summary: Optional[str] = None
    assigned_to: Optional[int] = None
    handed_off_at: Optional[datetime] = None
    created_at: Optional[datetime] = None  # ✅ CORRIGIDO: Pode ser None
    updated_at: Optional[datetime] = None  # ✅ CORRIGIDO: Pode ser None
    
    # Vendedor atribuído
    assigned_seller_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    assignment_method: Optional[str] = None
    assigned_seller: Optional[SellerSummary] = None


class LeadListResponse(BaseModel):
    """Lista de leads com paginação."""
    
    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============================================
# MENSAGEM (CORRIGIDO!)
# ============================================

class MessageResponse(BaseModel):
    """Mensagem na resposta."""
    model_config = ConfigDict(from_attributes=True)  # ✅ Permite criar de ORM
    
    id: int
    lead_id: int
    role: str
    content: str
    tokens_used: Optional[int] = 0  # ✅ CORRIGIDO: Pode ser None, default 0
    created_at: Optional[datetime] = None  # ✅ CORRIGIDO: Pode ser None


class MessageCreate(BaseModel):
    """Dados para criar mensagem."""
    
    lead_id: int
    role: str  # "user" ou "assistant"
    content: str
    tokens_used: Optional[int] = 0


# ============================================
# TENANT
# ============================================

class TenantSettings(BaseModel):
    """Configurações do tenant (empresa cliente)."""
    model_config = ConfigDict(extra="allow")  # Permite campos extras

    # Identidade da empresa
    niche: str = "services"
    company_name: Optional[str] = None
    tone: str = "cordial"
    custom_questions: list[str] = Field(default_factory=list)
    custom_rules: list[str] = Field(default_factory=list)
    custom_prompt: Optional[str] = None

    # === Integração com WhatsApp/Gupshup ===
    whatsapp_number: Optional[str] = Field(
        default=None,
        description="Número do WhatsApp Business usado por este tenant."
    )
    gupshup_app_name: Optional[str] = Field(
        default=None,
        description="Nome do APP dentro do Gupshup."
    )
    gupshup_api_key: Optional[str] = Field(
        default=None,
        description="API Key exclusiva do Gupshup."
    )
    gupshup_webhook_secret: Optional[str] = Field(
        default=None,
        description="Segredo usado para validar assinatura HMAC."
    )
    webhook_api_key: Optional[str] = Field(
        default=None,
        description="API Key para autenticar webhooks recebidos"
    )


class TenantCreate(BaseModel):
    """Dados necessários para criar um novo tenant."""

    name: str
    slug: str
    plan: str = "starter"
    settings: Optional[TenantSettings] = None


class TenantResponse(BaseModel):
    """Resposta completa do tenant."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    plan: str
    settings: Optional[dict] = None
    active: bool = True
    created_at: Optional[datetime] = None


class TenantUpdate(BaseModel):
    """Dados para atualizar tenant."""
    
    name: Optional[str] = None
    plan: Optional[str] = None
    settings: Optional[dict] = None
    active: Optional[bool] = None


# ============================================
# MÉTRICAS (Dashboard)
# ============================================

class DashboardMetrics(BaseModel):
    """Métricas do dashboard."""
    
    total_leads: int = 0
    leads_today: int = 0
    leads_this_week: int = 0
    leads_this_month: int = 0
    
    by_qualification: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_channel: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    
    conversion_rate: float = 0.0
    avg_qualification_time_hours: float = 0.0


class LeadsByPeriod(BaseModel):
    """Leads agrupados por período."""
    
    period: str
    count: int = 0
    hot: int = 0
    warm: int = 0
    cold: int = 0


# ============================================
# NICHO
# ============================================

class NicheInfo(BaseModel):
    """Informações de um nicho."""
    
    id: str
    name: str
    description: str


# ============================================
# AUTH
# ============================================

class LoginRequest(BaseModel):
    """Requisição de login."""
    
    email: str
    password: str


class TokenResponse(BaseModel):
    """Resposta com token JWT."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 horas
    user: dict


# ============================================
# CHANNEL (Canal de comunicação)
# ============================================

class ChannelCreate(BaseModel):
    """Dados para criar canal."""
    
    type: str  # whatsapp, web, etc
    config: dict = Field(default_factory=dict)


class ChannelResponse(BaseModel):
    """Resposta do canal."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    type: str
    active: bool = True
    config: dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None


# ============================================
# SELLER (Vendedor completo)
# ============================================

class SellerCreate(BaseModel):
    """Dados para criar vendedor."""
    
    name: str
    email: Optional[str] = None
    whatsapp: str
    cities: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    daily_limit: int = 10
    priority: int = 1
    active: bool = True


class SellerResponse(BaseModel):
    """Resposta do vendedor."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    name: str
    email: Optional[str] = None
    whatsapp: str
    cities: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    daily_limit: int = 10
    leads_today: int = 0
    priority: int = 1
    available: bool = True
    active: bool = True
    created_at: Optional[datetime] = None


class SellerUpdate(BaseModel):
    """Dados para atualizar vendedor."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    cities: Optional[list[str]] = None
    specialties: Optional[list[str]] = None
    daily_limit: Optional[int] = None
    priority: Optional[int] = None
    available: Optional[bool] = None
    active: Optional[bool] = None


# ============================================
# NOTIFICATION
# ============================================

class NotificationResponse(BaseModel):
    """Resposta de notificação."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    type: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    read: bool = False
    created_at: Optional[datetime] = None


# ============================================
# LEAD EVENT (Histórico)
# ============================================

class LeadEventResponse(BaseModel):
    """Resposta de evento do lead."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    lead_id: int
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None