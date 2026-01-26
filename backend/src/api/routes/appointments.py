"""
API Routes: Appointments (Agendamentos)
========================================

Endpoints para gerenciar agendamentos de compromissos entre vendedores e leads.

Funcionalidades:
- CRUD completo de appointments
- Filtros por vendedor, lead, status, datas
- Ações especiais: confirmar, completar, cancelar
- View de calendário (agrupado por dia/mês)
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from src.domain.entities import (
    Appointment,
    AppointmentType,
    AppointmentStatus,
    AppointmentOutcome,
    Lead,
    Seller,
    Tenant,
    User,
)
from src.api.dependencies import get_db, get_current_user, get_current_tenant

router = APIRouter(prefix="/appointments", tags=["appointments"])


# ==========================================
# SCHEMAS PYDANTIC
# ==========================================


class AppointmentCreate(BaseModel):
    """Schema para criar agendamento."""

    lead_id: int
    seller_id: int
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    appointment_type: str = Field(default=AppointmentType.VISIT)
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)  # 15min a 8h
    timezone: str = Field(default="America/Sao_Paulo")
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


class AppointmentUpdate(BaseModel):
    """Schema para atualizar agendamento."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    appointment_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    status: Optional[str] = None


class AppointmentCompletePayload(BaseModel):
    """Schema para marcar agendamento como completo."""

    outcome: str = Field(..., description="sale, follow_up, not_interested, rescheduled")
    outcome_notes: Optional[str] = None


class AppointmentCancelPayload(BaseModel):
    """Schema para cancelar agendamento."""

    reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    """Schema de resposta de agendamento."""

    id: int
    tenant_id: int
    lead_id: int
    lead_name: str
    lead_phone: Optional[str] = None
    seller_id: int
    seller_name: str
    created_by: int

    title: str
    description: Optional[str]
    appointment_type: str
    scheduled_at: datetime
    duration_minutes: int
    timezone: str

    location: Optional[str]
    location_lat: Optional[float]
    location_lng: Optional[float]

    status: str
    confirmed_by_lead: bool
    confirmed_at: Optional[datetime]

    outcome: Optional[str]
    outcome_notes: Optional[str]
    completed_at: Optional[datetime]

    reminder_sent: bool
    reminded_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# CRUD ENDPOINTS
# ==========================================


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    payload: AppointmentCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria novo agendamento.

    Valida:
    - Lead existe e pertence ao tenant
    - Seller existe e pertence ao tenant
    - Data/hora é futura
    """
    # Validar lead
    lead_result = await db.execute(
        select(Lead).where(Lead.id == payload.lead_id, Lead.tenant_id == tenant.id)
    )
    lead = lead_result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Validar seller
    seller_result = await db.execute(
        select(Seller).where(Seller.id == payload.seller_id, Seller.tenant_id == tenant.id)
    )
    seller = seller_result.scalar_one_or_none()

    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")

    # Validar data futura
    if payload.scheduled_at < datetime.now():
        raise HTTPException(
            status_code=400, detail="Data do agendamento deve ser futura"
        )

    # Criar appointment
    appointment = Appointment(
        tenant_id=tenant.id,
        lead_id=payload.lead_id,
        seller_id=payload.seller_id,
        created_by=user.id,
        title=payload.title,
        description=payload.description,
        appointment_type=payload.appointment_type,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        timezone=payload.timezone,
        location=payload.location,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
    )

    db.add(appointment)
    await db.commit()
    await db.refresh(appointment, ["lead", "seller"])

    # TODO: Agendar job para enviar reminder 1h antes (usar APScheduler ou Celery)

    return _format_appointment_response(appointment)


@router.get("", response_model=List[AppointmentResponse])
async def list_appointments(
    seller_id: Optional[int] = Query(None, description="Filtrar por vendedor"),
    lead_id: Optional[int] = Query(None, description="Filtrar por lead"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    date_from: Optional[datetime] = Query(None, description="Data inicial"),
    date_to: Optional[datetime] = Query(None, description="Data final"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista agendamentos com filtros.

    Filtros disponíveis:
    - seller_id: Agendamentos de um vendedor específico
    - lead_id: Agendamentos de um lead específico
    - status: scheduled, confirmed, completed, cancelled, no_show
    - date_from/date_to: Intervalo de datas
    """
    query = (
        select(Appointment)
        .where(Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )

    # Aplicar filtros
    if seller_id:
        query = query.where(Appointment.seller_id == seller_id)

    if lead_id:
        query = query.where(Appointment.lead_id == lead_id)

    if status:
        query = query.where(Appointment.status == status)

    if date_from:
        query = query.where(Appointment.scheduled_at >= date_from)

    if date_to:
        query = query.where(Appointment.scheduled_at <= date_to)

    # Ordenar e paginar
    query = query.order_by(Appointment.scheduled_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    appointments = result.scalars().all()

    return [_format_appointment_response(appt) for appt in appointments]


@router.get("/calendar")
async def calendar_view(
    seller_id: Optional[int] = Query(None, description="Filtrar por vendedor"),
    month: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    year: int = Query(..., ge=2020, le=2100, description="Ano"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna agendamentos formatados para calendário (agrupados por dia).

    Retorna estrutura:
    {
        "2026-01-26": [appointment1, appointment2],
        "2026-01-27": [appointment3]
    }
    """
    # Calcular primeiro e último dia do mês
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    date_from = datetime(year, month, 1, 0, 0, 0)
    date_to = datetime(year, month, last_day, 23, 59, 59)

    # Query
    query = (
        select(Appointment)
        .where(
            Appointment.tenant_id == tenant.id,
            Appointment.scheduled_at >= date_from,
            Appointment.scheduled_at <= date_to,
        )
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )

    if seller_id:
        query = query.where(Appointment.seller_id == seller_id)

    query = query.order_by(Appointment.scheduled_at.asc())

    result = await db.execute(query)
    appointments = result.scalars().all()

    # Agrupar por dia
    calendar_data = {}
    for appt in appointments:
        day_key = appt.scheduled_at.strftime("%Y-%m-%d")
        if day_key not in calendar_data:
            calendar_data[day_key] = []

        calendar_data[day_key].append(_format_appointment_response(appt))

    return calendar_data


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de um agendamento."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return _format_appointment_response(appointment)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza dados do agendamento.

    Permite atualizar:
    - Título, descrição, tipo
    - Data/hora, duração
    - Localização
    - Status
    """
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Atualizar campos
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    await db.commit()
    await db.refresh(appointment)

    return _format_appointment_response(appointment)


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Deleta agendamento."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id, Appointment.tenant_id == tenant.id
        )
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    await db.delete(appointment)
    await db.commit()

    return {"success": True, "message": "Agendamento deletado com sucesso"}


# ==========================================
# AÇÕES ESPECIAIS
# ==========================================


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirma agendamento (geralmente acionado pelo lead via WhatsApp ou email).

    Marca:
    - status = confirmed
    - confirmed_by_lead = True
    - confirmed_at = agora
    """
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=400, detail="Não é possível confirmar agendamento cancelado"
        )

    appointment.status = AppointmentStatus.CONFIRMED
    appointment.confirmed_by_lead = True
    appointment.confirmed_at = datetime.now()

    await db.commit()
    await db.refresh(appointment)

    return _format_appointment_response(appointment)


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: int,
    payload: AppointmentCompletePayload,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Marca agendamento como completo com resultado.

    Outcomes possíveis:
    - sale: Venda realizada
    - follow_up: Precisa acompanhamento
    - not_interested: Lead não interessado
    - rescheduled: Foi reagendado
    """
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=400, detail="Não é possível completar agendamento cancelado"
        )

    # Validar outcome
    valid_outcomes = [
        AppointmentOutcome.SALE,
        AppointmentOutcome.FOLLOW_UP_NEEDED,
        AppointmentOutcome.NOT_INTERESTED,
        AppointmentOutcome.RESCHEDULED,
    ]
    if payload.outcome not in valid_outcomes:
        raise HTTPException(
            status_code=400,
            detail=f"Outcome inválido. Use: {', '.join(valid_outcomes)}",
        )

    appointment.status = AppointmentStatus.COMPLETED
    appointment.outcome = payload.outcome
    appointment.outcome_notes = payload.outcome_notes
    appointment.completed_at = datetime.now()

    await db.commit()
    await db.refresh(appointment)

    return _format_appointment_response(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancelPayload,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancela agendamento.

    Permite cancelamento por:
    - Vendedor (via UI)
    - Lead (via WhatsApp/email)
    - Sistema (se lead não confirmar X horas antes)
    """
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail="Não é possível cancelar agendamento já completo"
        )

    appointment.status = AppointmentStatus.CANCELLED
    if payload.reason:
        appointment.outcome_notes = f"Cancelamento: {payload.reason}"

    await db.commit()
    await db.refresh(appointment)

    return _format_appointment_response(appointment)


@router.post("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_no_show(
    appointment_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Marca agendamento como 'no show' (lead não compareceu)."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .options(selectinload(Appointment.lead), selectinload(Appointment.seller))
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    appointment.status = AppointmentStatus.NO_SHOW
    appointment.completed_at = datetime.now()

    await db.commit()
    await db.refresh(appointment)

    return _format_appointment_response(appointment)


# ==========================================
# UTILS
# ==========================================


def _format_appointment_response(appointment: Appointment) -> dict:
    """Formata appointment para response incluindo dados de lead e seller."""
    return {
        "id": appointment.id,
        "tenant_id": appointment.tenant_id,
        "lead_id": appointment.lead_id,
        "lead_name": appointment.lead.name if appointment.lead else "N/A",
        "lead_phone": appointment.lead.phone if appointment.lead else None,
        "seller_id": appointment.seller_id,
        "seller_name": appointment.seller.name if appointment.seller else "N/A",
        "created_by": appointment.created_by,
        "title": appointment.title,
        "description": appointment.description,
        "appointment_type": appointment.appointment_type,
        "scheduled_at": appointment.scheduled_at,
        "duration_minutes": appointment.duration_minutes,
        "timezone": appointment.timezone,
        "location": appointment.location,
        "location_lat": appointment.location_lat,
        "location_lng": appointment.location_lng,
        "status": appointment.status,
        "confirmed_by_lead": appointment.confirmed_by_lead,
        "confirmed_at": appointment.confirmed_at,
        "outcome": appointment.outcome,
        "outcome_notes": appointment.outcome_notes,
        "completed_at": appointment.completed_at,
        "reminder_sent": appointment.reminder_sent,
        "reminded_at": appointment.reminded_at,
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at,
    }
