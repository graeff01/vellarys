"""
LeadNote - Anotações Internas dos Leads
========================================

Permite vendedores/gestores adicionarem notas privadas sobre leads.
Não são visíveis para o cliente, apenas internamente no CRM.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Lead, User


class LeadNote(Base, TimestampMixin):
    """Anotação interna sobre um lead."""

    __tablename__ = "lead_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relacionamentos
    lead: Mapped["Lead"] = relationship(back_populates="notes")
    author: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<LeadNote(id={self.id}, lead_id={self.lead_id}, author_id={self.author_id})>"
