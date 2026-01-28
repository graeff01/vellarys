"""
Feature Flag Entity

Feature flags operacionais (Gestor ativa/desativa).
Parte da nova arquitetura de entitlements.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, User


class FeatureFlag(Base, TimestampMixin):
    """
    Feature flags operacionais (Gestor ativa/desativa).

    Permite que Gestor/Admin controle quais features estão ATIVAS
    operacionalmente, dentro do que o plano permite.

    Diferença de Entitlement:
    - Entitlement: O que o plano OFERECE (pode usar)
    - Feature Flag: O que está ATIVO no momento (toggle operacional)

    Examples:
        # Gestor desativa calendário
        FeatureFlag(
            tenant_id=5,
            flag_key="calendar_enabled",
            is_enabled=False,
            last_changed_by_id=10
        )

        # Gestor ativa métricas
        FeatureFlag(
            tenant_id=5,
            flag_key="metrics_enabled",
            is_enabled=True,
            last_changed_by_id=10
        )
    """

    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Flag
    flag_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Key da feature (ex: calendar_enabled, metrics_enabled)"
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Se o flag está ativo"
    )

    # Auditoria
    last_changed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="Último usuário que alterou"
    )

    last_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Última alteração"
    )

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    last_changed_by: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint('tenant_id', 'flag_key', name='uq_tenant_feature_flag'),
        {'comment': 'Feature flags operacionais (Gestor)'}
    )

    def __repr__(self) -> str:
        status = "enabled" if self.is_enabled else "disabled"
        return f"<FeatureFlag(tenant_id={self.tenant_id}, key={self.flag_key}, {status})>"

    def enable(self, changed_by_id: int):
        """Ativa o flag."""
        self.is_enabled = True
        self.last_changed_by_id = changed_by_id
        self.last_changed_at = datetime.now(datetime.timezone.utc)

    def disable(self, changed_by_id: int):
        """Desativa o flag."""
        self.is_enabled = False
        self.last_changed_by_id = changed_by_id
        self.last_changed_at = datetime.now(datetime.timezone.utc)

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "key": self.flag_key,
            "is_enabled": self.is_enabled,
            "last_changed_by_id": self.last_changed_by_id,
            "last_changed_at": self.last_changed_at.isoformat() if self.last_changed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
