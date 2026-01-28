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
    from .plan_entitlement import PlanEntitlement


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

    # =========================================================================
    # NOVA ARQUITETURA: Relacionamento com entitlements (não quebra código antigo)
    # =========================================================================
    entitlements: Mapped[List["PlanEntitlement"]] = relationship(
        "PlanEntitlement",
        back_populates="plan",
        cascade="all, delete-orphan",
        doc="Entitlements do plano (nova arquitetura)"
    )

    def get_entitlements_by_type(self, etype: str) -> Dict[str, Any]:
        """
        Retorna entitlements de um tipo específico (nova arquitetura).

        Args:
            etype: "feature" | "limit" | "addon"

        Returns:
            dict: {key: value}
        """
        if not self.entitlements:
            return {}

        return {
            e.entitlement_key: e.entitlement_value
            for e in self.entitlements
            if e.entitlement_type == etype
        }

    @property
    def features_v2(self) -> Dict[str, bool]:
        """
        Features como dict {key: bool} (nova arquitetura).

        Se entitlements não existirem, fallback para self.features (JSONB antigo).
        """
        if self.entitlements:
            return {
                k: v.get("included", False)
                for k, v in self.get_entitlements_by_type("feature").items()
            }
        # Fallback para JSONB antigo
        return self.features or {}

    @property
    def limits_v2(self) -> Dict[str, int]:
        """
        Limits como dict {key: int} (nova arquitetura).

        Se entitlements não existirem, fallback para self.limits (JSONB antigo).
        """
        if self.entitlements:
            return {
                k: v.get("max", 0)
                for k, v in self.get_entitlements_by_type("limit").items()
            }
        # Fallback para JSONB antigo
        return self.limits or {}