"""
MODELOS DO BANCO DE DADOS (VERSÃO CORRIGIDA)
=============================================

Todas as tabelas do sistema Velaris.

CORREÇÃO: Campo settings agora usa MutableDict para
          SQLAlchemy detectar mudanças internas no JSON.
"""
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, DateTime, Table, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict  # ← ADICIONADO!

from .base import Base, TimestampMixin
from .enums import LeadStatus, LeadQualification, LeadSource, UserRole

if TYPE_CHECKING:
    from .tenant_subscription import TenantSubscription
    from .tenant_usage import TenantUsage


# ============================================
# TABELA DE ASSOCIAÇÃO (Lead <-> Tag)
# ============================================

lead_tags = Table(
    "lead_tags",
    Base.metadata,
    Column("lead_id", Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# ============================================
# TENANT - Empresa cliente da Velaris
# ============================================

class Tenant(Base, TimestampMixin):
    """Empresa que contrata a Velaris."""
    
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="starter")  # slug do plano
    
    # ═══════════════════════════════════════════════════════════════════════
    # CORREÇÃO CRÍTICA: Usar MutableDict para detectar mudanças no JSON
    # ═══════════════════════════════════════════════════════════════════════
    settings: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # ← CORREÇÃO!
        default=dict,
        nullable=True
    )
    
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relacionamentos principais
    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    channels: Mapped[list["Channel"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    sellers: Mapped[list["Seller"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    
    # Relacionamentos de assinatura e uso
    subscription: Mapped[Optional["TenantSubscription"]] = relationship(
        back_populates="tenant", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["TenantUsage"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan"
    )


# ============================================
# USER - Usuários do dashboard
# ============================================

class User(Base, TimestampMixin):
    """Usuário que acessa o dashboard."""
    
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.ADMIN.value)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


# ============================================
# CHANNEL - Canais de atendimento
# ============================================

class Channel(Base, TimestampMixin):
    """Canal de comunicação (WhatsApp, site, etc)."""
    
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # ← Também corrigido
        default=dict
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="channels")
    leads: Mapped[list["Lead"]] = relationship(back_populates="channel")


# ============================================
# TAG - Etiquetas customizáveis
# ============================================

class Tag(Base, TimestampMixin):
    """Etiqueta para categorizar leads."""
    
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")

    tenant: Mapped["Tenant"] = relationship(back_populates="tags")
    leads: Mapped[list["Lead"]] = relationship(secondary=lead_tags, back_populates="tags")


# ============================================
# LEAD - Potencial cliente
# ============================================

class Lead(Base, TimestampMixin):
    """Lead que entrou em contato."""
    
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # ==========================================
    # DADOS DO LEAD
    # ==========================================
    name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    custom_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),  # ← Também corrigido
        default=dict
    )
    
    # ==========================================
    # QUALIFICAÇÃO E STATUS
    # ==========================================
    qualification: Mapped[str] = mapped_column(String(20), default=LeadQualification.COLD.value, index=True)
    status: Mapped[str] = mapped_column(String(20), default=LeadStatus.NEW.value, index=True)
    
    # ==========================================
    # ORIGEM
    # ==========================================
    source: Mapped[str] = mapped_column(String(20), default=LeadSource.ORGANIC.value)
    campaign: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # ==========================================
    # RESUMO E HANDOFF
    # ==========================================
    summary: Mapped[Optional[str]] = mapped_column(Text)
    handed_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    

    # ==========================================
    # REENGAJAMENTO
    # ==========================================
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reengagement_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_reengagement_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reengagement_status: Mapped[Optional[str]] = mapped_column(String(20), default="none")

    # ==========================================
    # ATRIBUIÇÃO PARA VENDEDOR
    # ==========================================
    assigned_seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assignment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ==========================================
    # ATRIBUIÇÃO LEGADA (gestor/usuário)
    # ==========================================
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # ==========================================
    # RELACIONAMENTOS
    # ==========================================
    tenant: Mapped["Tenant"] = relationship(back_populates="leads")
    channel: Mapped[Optional["Channel"]] = relationship(back_populates="leads")
    messages: Mapped[list["Message"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    events: Mapped[list["LeadEvent"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(secondary=lead_tags, back_populates="leads")
    assigned_seller: Mapped[Optional["Seller"]] = relationship(foreign_keys=[assigned_seller_id])
    assignments: Mapped[list["LeadAssignment"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


# ============================================
# NOTIFICATION - Notificações
# ============================================

class Notification(Base):
    """Alertas para o gestor (lead hot, etc)."""
    
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    tenant: Mapped["Tenant"] = relationship(back_populates="notifications")


# ============================================
# MESSAGE - Mensagens da conversa
# ============================================

class Message(Base, TimestampMixin):
    """Mensagem individual da conversa."""
    
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    lead: Mapped["Lead"] = relationship(back_populates="messages")


# ============================================
# LEAD_EVENT - Histórico de mudanças
# ============================================

class LeadEvent(Base, TimestampMixin):
    """Evento/mudança no lead (para métricas)."""
    
    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    old_value: Mapped[Optional[str]] = mapped_column(String(100))
    new_value: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    lead: Mapped["Lead"] = relationship(back_populates="events")


# ============================================
# IMPORTS PARA EVITAR CIRCULAR
# ============================================
from .seller import Seller
from .lead_assignment import LeadAssignment