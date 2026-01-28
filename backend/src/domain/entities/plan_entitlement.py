"""
Plan Entitlement Entity

Define o que um plano OFERECE (pode usar).
Parte da nova arquitetura de entitlements.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .plan import Plan


class EntitlementType:
    """Tipos de entitlement."""
    FEATURE = "feature"  # Funcionalidade qualitativa (bool)
    LIMIT = "limit"      # Limite quantitativo (int)
    ADDON = "addon"      # Add-on opcional


class EntitlementCategory:
    """Categorias de entitlements."""
    CORE = "core"              # Funcionalidades básicas
    ADVANCED = "advanced"      # Funcionalidades avançadas
    ENTERPRISE = "enterprise"  # Funcionalidades enterprise
    SECURITY = "security"      # Segurança e compliance
    LIMIT = "limit"            # Limites quantitativos


class PlanEntitlement(Base, TimestampMixin):
    """
    Define o que um plano oferece.

    Substitui o antigo Plan.features (JSONB) por estrutura normalizada.
    Permite versionamento, queries complexas e auditoria.

    Examples:
        # Feature qualitativa
        PlanEntitlement(
            plan_id=1,
            entitlement_type="feature",
            entitlement_key="calendar_enabled",
            entitlement_value={"included": True, "max_users": None},
            name="Calendário de Agendamentos",
            category="core"
        )

        # Limite quantitativo
        PlanEntitlement(
            plan_id=1,
            entitlement_type="limit",
            entitlement_key="leads_per_month",
            entitlement_value={"max": 1000, "unit": "per_month"},
            name="Leads por Mês",
            category="limit"
        )
    """

    __tablename__ = "plan_entitlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Tipo de entitlement
    entitlement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="feature | limit | addon"
    )

    # Key única (ex: "calendar_enabled", "leads_per_month")
    entitlement_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Identificador único do entitlement"
    )

    # Valor (JSONB flexível)
    entitlement_value: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        comment="Valor do entitlement (estrutura flexível)"
    )

    # Metadata
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nome legível do entitlement"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada"
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Categoria do entitlement"
    )

    # Relacionamento
    plan: Mapped["Plan"] = relationship(back_populates="entitlements")

    __table_args__ = (
        UniqueConstraint('plan_id', 'entitlement_key', name='uq_plan_entitlement'),
        {'comment': 'Entitlements de planos (nova arquitetura)'}
    )

    def __repr__(self) -> str:
        return f"<PlanEntitlement(plan_id={self.plan_id}, key={self.entitlement_key}, type={self.entitlement_type})>"

    @property
    def is_feature(self) -> bool:
        """Verifica se é uma feature."""
        return self.entitlement_type == EntitlementType.FEATURE

    @property
    def is_limit(self) -> bool:
        """Verifica se é um limite."""
        return self.entitlement_type == EntitlementType.LIMIT

    @property
    def is_included(self) -> bool:
        """Verifica se está incluído (para features)."""
        if self.is_feature:
            return self.entitlement_value.get("included", False)
        return False

    @property
    def max_value(self) -> Optional[int]:
        """Retorna valor máximo (para limites)."""
        if self.is_limit:
            return self.entitlement_value.get("max")
        return None

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "type": self.entitlement_type,
            "key": self.entitlement_key,
            "value": self.entitlement_value,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
