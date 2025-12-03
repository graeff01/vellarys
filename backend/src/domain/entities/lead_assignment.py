"""
MODELO: ATRIBUIÇÃO DE LEAD (LEAD ASSIGNMENT)
=============================================

Histórico de atribuições de leads para vendedores.
Importante para:
- Auditoria (quem recebeu o quê)
- Métricas (tempo de resposta, reatribuições)
- Rastreabilidade (por que foi atribuído assim)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LeadAssignment(Base):
    """
    Registro de atribuição de lead para vendedor.
    
    Cada vez que um lead é atribuído (ou reatribuído),
    um novo registro é criado aqui.
    """
    
    __tablename__ = "lead_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # ==========================================
    # REFERÊNCIAS
    # ==========================================
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), index=True)
    
    # ==========================================
    # DETALHES DA ATRIBUIÇÃO
    # ==========================================
    # Método usado: round_robin, by_city, by_interest, manual
    assignment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Se foi reatribuído, de qual vendedor veio (sem FK para evitar conflito)
    reassigned_from_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Motivo da atribuição/reatribuição
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==========================================
    # TIMESTAMPS
    # ==========================================
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        nullable=False
    )
    
    # Quando o vendedor foi notificado
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Quando o vendedor visualizou/respondeu (futuro)
    seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # ==========================================
    # STATUS DA ATRIBUIÇÃO
    # ==========================================
    # pending, notified, seen, responded, expired, reassigned
    status: Mapped[str] = mapped_column(String(20), default="pending")
    
    # ==========================================
    # RELACIONAMENTOS
    # ==========================================
    lead: Mapped["Lead"] = relationship(back_populates="assignments")
    seller: Mapped["Seller"] = relationship(
        back_populates="assignments",
        foreign_keys=[seller_id]
    )