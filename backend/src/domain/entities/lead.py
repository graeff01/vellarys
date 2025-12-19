# backend/src/domain/entities/lead.py

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Text, JSON, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Lead(Base):
    __tablename__ = "leads"

    # ===============================
    # IDENTIDADE
    # ===============================
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("channels.id"), nullable=True)

    external_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # ===============================
    # DADOS DO LEAD
    # ===============================
    name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))

    source: Mapped[Optional[str]] = mapped_column(String(100))
    campaign: Mapped[Optional[str]] = mapped_column(String(100))

    custom_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # ===============================
    # QUALIFICAÇÃO / IA
    # ===============================
    qualification: Mapped[Optional[str]] = mapped_column(String(20))
    qualification_score: Mapped[Optional[int]] = mapped_column(Integer)
    qualification_confidence: Mapped[Optional[float]] = mapped_column(Float)
    last_qualification_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    summary: Mapped[Optional[str]] = mapped_column(Text)

    # ===============================
    # STATUS / HANDOFF
    # ===============================
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[Optional[int]] = mapped_column(Integer)
    handed_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ===============================
    # ATRIBUIÇÃO
    # ===============================
    assigned_seller_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sellers.id"))
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assignment_method: Mapped[Optional[str]] = mapped_column(String(50))

    # ===============================
    # TIMESTAMPS
    # ===============================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ===============================
    # RELACIONAMENTOS
    # ===============================
    assignments: Mapped[List["LeadAssignment"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan"
    )

    assigned_seller = relationship("Seller", lazy="joined")
