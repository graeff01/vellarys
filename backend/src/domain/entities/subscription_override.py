"""
Subscription Override Entity

Overrides por subscription (SuperAdmin customizações).
Parte da nova arquitetura de entitlements.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .tenant_subscription import TenantSubscription
    from .models import User


class SubscriptionOverride(Base, TimestampMixin):
    """
    Overrides por subscription (SuperAdmin customizações).

    Permite que SuperAdmin ative features não incluídas no plano,
    ou desative features incluídas, ou customize limites.

    Examples:
        # Ativar feature não incluída no plano
        SubscriptionOverride(
            subscription_id=5,
            override_key="copilot_enabled",
            override_type="feature",
            override_value={"included": True},
            created_by_id=1,
            reason="Cliente piloto para testar copilot"
        )

        # Aumentar limite
        SubscriptionOverride(
            subscription_id=5,
            override_key="leads_per_month",
            override_type="limit",
            override_value={"max": 5000},
            created_by_id=1,
            reason="Cliente VIP - limite aumentado",
            expires_at=datetime(2026, 12, 31)
        )
    """

    __tablename__ = "subscription_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("tenant_subscriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Override
    override_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Key do entitlement (ex: calendar_enabled, leads_per_month)"
    )

    override_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="feature | limit"
    )

    override_value: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        comment="Valor do override"
    )

    # Auditoria
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="Quem criou o override (geralmente SuperAdmin)"
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Motivo do override"
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Data de expiração (opcional)"
    )

    # Relacionamentos
    subscription: Mapped["TenantSubscription"] = relationship(back_populates="overrides")
    created_by: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint('subscription_id', 'override_key', name='uq_subscription_override'),
        {'comment': 'Overrides de subscriptions (SuperAdmin)'}
    )

    def __repr__(self) -> str:
        return f"<SubscriptionOverride(sub_id={self.subscription_id}, key={self.override_key}, type={self.override_type})>"

    @property
    def is_expired(self) -> bool:
        """Verifica se o override expirou."""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.now(timezone.utc)

    @property
    def is_feature_override(self) -> bool:
        """Verifica se é override de feature."""
        return self.override_type == "feature"

    @property
    def is_limit_override(self) -> bool:
        """Verifica se é override de limite."""
        return self.override_type == "limit"

    @property
    def is_enabled(self) -> bool:
        """Para features, verifica se está habilitado."""
        if self.is_feature_override:
            return self.override_value.get("included", False)
        return False

    @property
    def max_value(self) -> Optional[int]:
        """Para limites, retorna valor máximo."""
        if self.is_limit_override:
            return self.override_value.get("max")
        return None

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "key": self.override_key,
            "type": self.override_type,
            "value": self.override_value,
            "created_by_id": self.created_by_id,
            "reason": self.reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
