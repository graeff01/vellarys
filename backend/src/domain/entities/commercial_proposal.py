"""
CommercialProposal - Proposta Comercial Imobiliária
====================================================

Gerencia negociações de compra/venda de imóveis:
- Registro de ofertas e contrapropostas
- Timeline completo da negociação
- Status: pendente → análise → negociando → fechada/rejeitada
- Deadline para resposta

Fluxo típico:
1. Lead oferece R$ 450k no imóvel (asked_value: R$ 480k)
2. Proprietário rejeita
3. Lead aumenta para R$ 460k
4. Proprietário aceita → Status: closed, final_value: R$ 460k
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, Lead, User
    from .seller import Seller


class ProposalStatus:
    """Status da proposta."""
    PENDING = "pending"                   # Aguardando análise
    OWNER_ANALYSIS = "owner_analysis"     # Proprietário analisando
    OWNER_REJECTED = "owner_rejected"     # Proprietário rejeitou
    OWNER_ACCEPTED = "owner_accepted"     # Proprietário aceitou (ainda negociando)
    NEGOTIATING = "negotiating"           # Em negociação ativa
    CLOSED = "closed"                     # Fechado! Venda concretizada
    EXPIRED = "expired"                   # Expirado (passou o deadline)


class ProposalEvent:
    """Eventos da timeline."""
    LEAD_OFFERED = "lead_offered"         # Lead fez oferta
    OWNER_REJECTED = "owner_rejected"     # Proprietário rejeitou
    OWNER_ACCEPTED = "owner_accepted"     # Proprietário aceitou
    LEAD_RAISED = "lead_raised"           # Lead aumentou oferta
    LEAD_LOWERED = "lead_lowered"         # Lead baixou oferta
    DEADLINE_SET = "deadline_set"         # Prazo definido
    DEADLINE_EXTENDED = "deadline_extended"  # Prazo estendido
    CLOSED = "closed"                     # Proposta fechada


class CommercialProposal(Base, TimestampMixin):
    """Proposta comercial imobiliária."""

    __tablename__ = "commercial_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sellers.id", ondelete="SET NULL"), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Property Info (JSONB)
    property_info: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False
    )
    # {
    #   "type": "apartamento",
    #   "address": "Rua X, 123 - Zona Sul",
    #   "size": "80m²",
    #   "rooms": 3,
    #   "bathrooms": 2,
    #   "parking": 1,
    #   "features": ["piscina", "churrasqueira"],
    #   "images": ["url1", "url2"]
    # }

    # Values
    asked_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    offered_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    final_value: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=ProposalStatus.PENDING, index=True)

    # Deadline
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timeline (JSONB array)
    timeline: Mapped[List[Dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=True
    )
    # [
    #   {"date": "2026-01-15T10:30:00", "event": "lead_offered", "value": 450000, "note": "..."},
    #   {"date": "2026-01-15T14:20:00", "event": "owner_rejected", "note": "..."}
    # ]

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Closed timestamp
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    lead: Mapped["Lead"] = relationship(back_populates="commercial_proposals")
    seller: Mapped[Optional["Seller"]] = relationship()
    creator: Mapped[Optional["User"]] = relationship()

    # Índices compostos
    __table_args__ = (
        Index("ix_proposals_tenant_status", "tenant_id", "status"),
    )

    def add_timeline_event(
        self,
        event: str,
        value: Optional[float] = None,
        note: Optional[str] = None
    ) -> None:
        """Adiciona evento à timeline."""
        if self.timeline is None:
            self.timeline = []

        self.timeline.append({
            "date": datetime.now().isoformat(),
            "event": event,
            "value": value,
            "note": note
        })

    def __repr__(self) -> str:
        return f"<CommercialProposal(id={self.id}, lead_id={self.lead_id}, offered={self.offered_value}, status='{self.status}')>"
