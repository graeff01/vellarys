"""
SCHEMAS DE VALIDAÇÃO
=====================

Define a estrutura de dados de entrada e saída da API.
Pydantic valida automaticamente os dados.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict   # <-- IMPORT CORRETO



# ============================================
# WEBHOOK - Receber mensagens
# ============================================

class WebhookMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    """Mensagem recebida via webhook."""
    
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

    class Config:
        extra = "ignore"   # <--- ESSA LINHA RESOLVE O ERRO 400


class WebhookResponse(BaseModel):
    """Resposta do webhook."""
    
    success: bool
    reply: str = Field(..., description="Resposta da IA para enviar ao lead")
    lead_id: int
    is_new_lead: bool
    qualification: Optional[str] = None


# ============================================
# SELLER (Vendedor) - Resumo para exibir no Lead
# ============================================

class SellerSummary(BaseModel):
    """Resumo do vendedor para exibir em listas."""
    
    id: int
    name: str
    whatsapp: str
    
    class Config:
        from_attributes = True


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
    
    id: int
    tenant_id: int
    channel_id: Optional[int]
    external_id: Optional[str]
    qualification: str
    status: str
    summary: Optional[str]
    assigned_to: Optional[int]
    handed_off_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Vendedor atribuído
    assigned_seller_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    assignment_method: Optional[str] = None
    assigned_seller: Optional[SellerSummary] = None
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Lista de leads com paginação."""
    
    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ============================================
# MENSAGEM
# ============================================

class MessageResponse(BaseModel):
    """Mensagem na resposta."""
    
    id: int
    lead_id: int
    role: str
    content: str
    tokens_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# TENANT
# ============================================
class TenantSettings(BaseModel):
    """Configurações do tenant (empresa cliente)."""

    # Identidade da empresa
    niche: str = "services"
    company_name: str
    tone: str = "cordial"
    custom_questions: list[str] = Field(default_factory=list)
    custom_rules: list[str] = Field(default_factory=list)
    custom_prompt: Optional[str] = None

    # === Integração com WhatsApp/Gupshup ===
    whatsapp_number: Optional[str] = Field(
        default=None,
        description="Número do WhatsApp Business usado por este tenant (somente dígitos)."
    )

    gupshup_app_name: Optional[str] = Field(
        default=None,
        description="Nome do APP dentro do Gupshup que pertence a este tenant."
    )

    gupshup_api_key: Optional[str] = Field(
        default=None,
        description="API Key exclusiva do Gupshup para este tenant."
    )

    gupshup_webhook_secret: Optional[str] = Field(
        default=None,
        description="Segredo usado para validar assinatura HMAC do webhook."
    )



# ============================================
# MÉTRICAS (Dashboard)
# ============================================

class DashboardMetrics(BaseModel):
    """Métricas do dashboard."""
    
    total_leads: int
    leads_today: int
    leads_this_week: int
    leads_this_month: int
    
    by_qualification: dict[str, int]  # {"hot": 10, "warm": 25, "cold": 50}
    by_status: dict[str, int]         # {"new": 5, "qualified": 20, ...}
    by_channel: dict[str, int]        # {"whatsapp": 60, "web": 25}
    by_source: dict[str, int]         # {"organic": 40, "paid": 45}
    
    conversion_rate: float            # % de leads que viraram qualified
    avg_qualification_time_hours: float  # Tempo médio até qualificar


class LeadsByPeriod(BaseModel):
    """Leads agrupados por período."""
    
    period: str  # "2024-01-15" ou "2024-01" ou "2024-W03"
    count: int
    hot: int
    warm: int
    cold: int


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
    expires_in: int
    user: dict

    # ============================================
# TENANT - Criação, resposta e atualização
# ============================================

class TenantCreate(BaseModel):
    """Dados necessários para criar um novo tenant (cliente)."""

    name: str
    slug: str
    plan: str = "starter"
    settings: TenantSettings


class TenantResponse(BaseModel):
    """Resposta completa do tenant."""

    id: int
    name: str
    slug: str
    plan: str
    settings: dict
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True
