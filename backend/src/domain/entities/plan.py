"""
PLAN - Planos de assinatura
============================

Define os planos disponíveis e seus limites.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING, List
from sqlalchemy import String, Boolean, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant


class Plan(Base, TimestampMixin):
    """
    Plano de assinatura com limites e features.
    
    Exemplo de limits:
    {
        "leads_per_month": 500,
        "messages_per_month": 5000,
        "sellers": 10,
        "niches": 3,
        "ai_tokens_per_month": 500000
    }
    
    Exemplo de features:
    {
        "reengagement": True,
        "advanced_reports": True,
        "api_access": False,
        "priority_support": False,
        "white_label": False,
        "custom_integrations": False
    }
    """
    
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Identificação
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Preços
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    
    # Limites (JSONB para flexibilidade)
    limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Features habilitadas (JSONB)
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Ordenação para exibição
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Se é o plano destacado (mais popular)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def get_limit(self, key: str, default: int = 0) -> int:
        """Retorna um limite específico."""
        value = self.limits.get(key, default)
        # -1 significa ilimitado
        return value
    
    def has_feature(self, key: str) -> bool:
        """Verifica se uma feature está habilitada."""
        return self.features.get(key, False)
    
    def is_unlimited(self, key: str) -> bool:
        """Verifica se um limite é ilimitado (-1)."""
        return self.limits.get(key, 0) == -1