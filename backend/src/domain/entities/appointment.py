"""
Model: Appointment (Agendamento)
=================================

Representa um compromisso agendado entre vendedor e lead.

Tipos de agendamento:
- Visita presencial
- Ligação telefônica
- Reunião
- Demonstração
- Videochamada

Estados:
- scheduled: Agendado (criado)
- confirmed: Confirmado pelo lead
- completed: Realizado
- cancelled: Cancelado
- no_show: Lead não compareceu

Resultados (outcomes):
- sale: Venda realizada
- follow_up: Precisa follow-up
- not_interested: Lead não interessado
- rescheduled: Reagendado
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, DateTime, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, Lead, User
    from .seller import Seller


class AppointmentType:
    """Tipos de agendamento disponíveis."""

    VISIT = "visit"          # Visita presencial
    CALL = "call"            # Ligação telefônica
    MEETING = "meeting"      # Reunião
    DEMO = "demo"            # Demonstração de produto
    VIDEOCALL = "videocall"  # Videochamada


class AppointmentStatus:
    """Estados possíveis de um agendamento."""

    SCHEDULED = "scheduled"   # Agendado (inicial)
    CONFIRMED = "confirmed"   # Confirmado pelo lead
    COMPLETED = "completed"   # Realizado
    CANCELLED = "cancelled"   # Cancelado
    NO_SHOW = "no_show"      # Lead não compareceu


class AppointmentOutcome:
    """Resultado do agendamento após conclusão."""

    SALE = "sale"                      # Venda realizada
    FOLLOW_UP_NEEDED = "follow_up"     # Precisa acompanhamento
    NOT_INTERESTED = "not_interested"  # Lead não interessado
    RESCHEDULED = "rescheduled"        # Foi reagendado


class Appointment(Base, TimestampMixin):
    """
    Agendamento de compromisso entre vendedor e lead.

    Permite vendedores marcarem visitas, ligações e outros tipos de
    compromissos com leads, com controle de status, confirmação e resultado.
    """

    __tablename__ = "appointments"

    # ==========================================
    # IDENTIFICAÇÃO
    # ==========================================
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ==========================================
    # DADOS DO AGENDAMENTO
    # ==========================================
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appointment_type: Mapped[str] = mapped_column(
        String(50),
        default=AppointmentType.VISIT,
        nullable=False
    )

    # ==========================================
    # DATA E HORA
    # ==========================================
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="America/Sao_Paulo",
        nullable=False
    )

    # ==========================================
    # LOCALIZAÇÃO (para visitas presenciais)
    # ==========================================
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location_lat: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 8),
        nullable=True
    )
    location_lng: Mapped[Optional[float]] = mapped_column(
        DECIMAL(11, 8),
        nullable=True
    )

    # ==========================================
    # STATUS E CONFIRMAÇÃO
    # ==========================================
    status: Mapped[str] = mapped_column(
        String(20),
        default=AppointmentStatus.SCHEDULED,
        index=True,
        nullable=False
    )
    confirmed_by_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # ==========================================
    # RESULTADO (após conclusão)
    # ==========================================
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # ==========================================
    # NOTIFICAÇÕES
    # ==========================================
    reminded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ==========================================
    # CUSTOM DATA
    # ==========================================
    custom_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    # ==========================================
    # RELACIONAMENTOS
    # ==========================================
    tenant: Mapped["Tenant"] = relationship()
    lead: Mapped["Lead"] = relationship(back_populates="appointments")
    seller: Mapped["Seller"] = relationship(back_populates="appointments")
    creator: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Appointment {self.id}: {self.title} @ {self.scheduled_at} ({self.status})>"
