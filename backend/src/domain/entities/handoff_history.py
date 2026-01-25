"""
HandoffHistory - Histórico de Transferências
=============================================

Rastreia todas as transferências de atendimento:
- IA → Vendedor (handoff)
- Vendedor → IA (retornar ao bot)
- Vendedor A → Vendedor B (reatribuição)

Usado para auditoria, compliance e análise de performance.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from .base import Base

if TYPE_CHECKING:
    from .models import Lead, User
    from .seller import Seller


class HandoffHistory(Base):
    """Registro de transferência de atendimento."""

    __tablename__ = "handoff_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # De onde veio ("ai", "seller")
    from_attended_by: Mapped[str] = mapped_column(String(20), nullable=False)
    # Para onde foi ("ai", "seller")
    to_attended_by: Mapped[str] = mapped_column(String(20), nullable=False)

    # IDs dos vendedores envolvidos (se aplicável)
    from_seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True
    )
    to_seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Quem iniciou a transferência (gestor, vendedor, sistema automático)
    initiated_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Motivo da transferência (opcional)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relacionamentos
    lead: Mapped["Lead"] = relationship(back_populates="handoff_history")
    from_seller: Mapped[Optional["Seller"]] = relationship(foreign_keys=[from_seller_id])
    to_seller: Mapped[Optional["Seller"]] = relationship(foreign_keys=[to_seller_id])
    initiated_by: Mapped[Optional["User"]] = relationship(foreign_keys=[initiated_by_user_id])

    def __repr__(self) -> str:
        return f"<HandoffHistory(id={self.id}, lead_id={self.lead_id}, {self.from_attended_by}→{self.to_attended_by})>"
