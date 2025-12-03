"""
TENANT USAGE - Controle de uso mensal
======================================

Registra o consumo de cada tenant por período.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TenantUsage(Base, TimestampMixin):
    """
    Uso mensal do tenant.
    
    Um registro por tenant por mês.
    Período no formato: "2025-01", "2025-02", etc.
    """
    
    __tablename__ = "tenant_usage"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "period", name="uq_tenant_usage_period"),
        Index("ix_tenant_usage_period", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    
    # Período (YYYY-MM)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    
    # Contadores principais
    leads_count: Mapped[int] = mapped_column(Integer, default=0)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    
    # Contadores adicionais (para features específicas)
    reengagement_count: Mapped[int] = mapped_column(Integer, default=0)
    handoffs_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Dados extras (para métricas futuras)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Relacionamento
    tenant: Mapped["Tenant"] = relationship(back_populates="usage_records")
    
    @classmethod
    def get_current_period(cls) -> str:
        """Retorna o período atual (YYYY-MM)."""
        return datetime.now().strftime("%Y-%m")


# Importação para evitar circular
from .models import Tenant