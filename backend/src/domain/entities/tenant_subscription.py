"""
TENANT SUBSCRIPTION - Assinatura do tenant
===========================================

Controla o período de assinatura, trial e status de pagamento.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TenantSubscription(Base, TimestampMixin):
    """
    Assinatura do tenant.
    
    Controla:
    - Período de trial
    - Tipo de cobrança (mensal/anual)
    - Status da assinatura
    - Bloqueio por limite
    """
    
    __tablename__ = "tenant_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), 
        unique=True, 
        index=True
    )
    
    # Plano atual
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    
    # Tipo de cobrança: monthly, yearly
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    
    # Status: trial, active, past_due, canceled, suspended
    status: Mapped[str] = mapped_column(String(20), default="trial", index=True)
    
    # Trial
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Datas da assinatura
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Bloqueio por limite
    is_limit_exceeded: Mapped[bool] = mapped_column(Boolean, default=False)
    limit_exceeded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    limit_exceeded_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Tolerância usada (% além do limite)
    tolerance_used: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    
    # Limites customizados (sobrescreve o plano se definido)
    custom_limits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship()
    
    def is_trial(self) -> bool:
        """Verifica se está em trial."""
        return self.status == "trial"
    
    def is_trial_expired(self) -> bool:
        """Verifica se o trial expirou."""
        if not self.trial_ends_at:
            return False
        return datetime.now(self.trial_ends_at.tzinfo) > self.trial_ends_at
    
    def is_active(self) -> bool:
        """Verifica se a assinatura está ativa."""
        return self.status in ("trial", "active")
    
    def is_blocked(self) -> bool:
        """Verifica se está bloqueado por limite."""
        return self.is_limit_exceeded
    
    def days_remaining_trial(self) -> int:
        """Retorna dias restantes do trial."""
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.now(self.trial_ends_at.tzinfo)
        return max(0, delta.days)
    
    def get_limit(self, key: str) -> int:
        """
        Retorna o limite para um recurso.
        Prioriza limite customizado sobre o do plano.
        """
        if self.custom_limits and key in self.custom_limits:
            return self.custom_limits[key]
        return self.plan.get_limit(key) if self.plan else 0
    
    def has_feature(self, key: str) -> bool:
        """Verifica se uma feature está disponível."""
        return self.plan.has_feature(key) if self.plan else False


# Importações para evitar circular
from .models import Tenant
from .plan import Plan