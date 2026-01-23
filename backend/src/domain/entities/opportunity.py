"""
OPPORTUNITY MODEL
=================

Representa uma oportunidade/negócio em andamento vinculado a um lead.
Usado para tracking de imóveis/produtos em negociação.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, DateTime, Index, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin
from .enums import OpportunityStatus

if TYPE_CHECKING:
    from .models import Lead, Tenant
    from .seller import Seller
    from .product import Product


class Opportunity(Base, TimestampMixin):
    """
    Oportunidade de negócio vinculada a um lead.

    Cada lead pode ter múltiplas oportunidades (ex: interessado em vários imóveis).
    """

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)

    # Produto/imóvel associado (opcional)
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Vendedor responsável
    seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Dados da oportunidade
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=0)  # Valor em centavos
    status: Mapped[str] = mapped_column(
        String(20),
        default=OpportunityStatus.NEW.value,
        index=True
    )

    # Datas
    expected_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    won_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Motivo de perda (quando status = lost)
    lost_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Notas e dados extras
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict
    )

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship("Tenant")
    lead: Mapped["Lead"] = relationship("Lead", back_populates="opportunities")
    product: Mapped[Optional["Product"]] = relationship("Product")
    seller: Mapped[Optional["Seller"]] = relationship("Seller")

    # Índices
    __table_args__ = (
        Index("ix_opportunities_tenant_status", "tenant_id", "status"),
        Index("ix_opportunities_tenant_created", "tenant_id", "created_at"),
        Index("ix_opportunities_lead_status", "lead_id", "status"),
    )
