"""
Feature Audit Log Entity

Log de todas as mudanças em features.
Parte da nova arquitetura de entitlements.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, User


class ChangeType:
    """Tipos de mudança."""
    OVERRIDE = "override"        # SuperAdmin override
    FLAG = "flag"                # Gestor toggle
    PLAN_CHANGE = "plan_change"  # Mudança de plano


class FeatureAuditLog(Base, TimestampMixin):
    """
    Log de todas as mudanças em features e limites.

    Permite auditoria completa de quem mudou o quê, quando e por quê.
    Essencial para compliance e troubleshooting.

    Examples:
        # SuperAdmin ativou feature
        FeatureAuditLog(
            tenant_id=5,
            change_type="override",
            entity_type="feature",
            entity_key="copilot_enabled",
            old_value={"enabled": False},
            new_value={"enabled": True},
            changed_by_id=1,
            reason="Cliente piloto",
            ip_address="192.168.1.1"
        )

        # Gestor desativou calendário
        FeatureAuditLog(
            tenant_id=5,
            change_type="flag",
            entity_type="feature",
            entity_key="calendar_enabled",
            old_value={"enabled": True},
            new_value={"enabled": False},
            changed_by_id=10,
            reason="Equipe não usa mais"
        )

        # Mudança de plano
        FeatureAuditLog(
            tenant_id=5,
            change_type="plan_change",
            entity_type="plan",
            entity_key="plan_upgrade",
            old_value={"plan": "starter"},
            new_value={"plan": "premium"},
            changed_by_id=1,
            reason="Upgrade solicitado pelo cliente"
        )
    """

    __tablename__ = "feature_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # O que mudou
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="override | flag | plan_change"
    )

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="feature | limit | plan"
    )

    entity_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Key da entidade (ex: calendar_enabled)"
    )

    # Valores
    old_value: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        comment="Valor anterior"
    )

    new_value: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        comment="Novo valor"
    )

    # Contexto
    changed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="Quem fez a mudança"
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Motivo da mudança"
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP do usuário"
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="User agent do navegador"
    )

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    changed_by: Mapped["User"] = relationship()

    __table_args__ = (
        {'comment': 'Audit trail de mudanças em features'}
    )

    def __repr__(self) -> str:
        return f"<FeatureAuditLog(tenant_id={self.tenant_id}, type={self.change_type}, key={self.entity_key})>"

    @property
    def is_override_change(self) -> bool:
        """Verifica se foi mudança de override (SuperAdmin)."""
        return self.change_type == ChangeType.OVERRIDE

    @property
    def is_flag_change(self) -> bool:
        """Verifica se foi mudança de flag (Gestor)."""
        return self.change_type == ChangeType.FLAG

    @property
    def is_plan_change(self) -> bool:
        """Verifica se foi mudança de plano."""
        return self.change_type == ChangeType.PLAN_CHANGE

    def get_change_summary(self) -> str:
        """Retorna resumo legível da mudança."""
        old = self.old_value or {}
        new = self.new_value or {}

        if self.entity_type == "feature":
            old_status = "habilitado" if old.get("enabled") else "desabilitado"
            new_status = "habilitado" if new.get("enabled") else "desabilitado"
            return f"{self.entity_key}: {old_status} → {new_status}"

        elif self.entity_type == "limit":
            old_max = old.get("max", 0)
            new_max = new.get("max", 0)
            return f"{self.entity_key}: {old_max} → {new_max}"

        else:
            return f"{self.entity_key} alterado"

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "change_type": self.change_type,
            "entity_type": self.entity_type,
            "entity_key": self.entity_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by_id": self.changed_by_id,
            "reason": self.reason,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "summary": self.get_change_summary(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
