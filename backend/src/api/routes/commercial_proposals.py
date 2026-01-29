"""
API Routes: Commercial Proposals (Propostas Comerciais)
=========================================================

Gerenciamento de propostas comerciais para mercado imobiliário.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.domain.entities.commercial_proposal import (
    CommercialProposal,
    ProposalStatus,
    ProposalEvent
)
from src.domain.entities.models import Tenant, User, Lead
from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user, get_current_tenant


router = APIRouter(prefix="/proposals", tags=["proposals"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PropertyInfo(BaseModel):
    """Informações do imóvel."""
    type: str = Field(..., description="apartamento, casa, sobrado, terreno, sala_comercial")
    address: str
    size: Optional[str] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking: Optional[int] = None
    features: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)


class ProposalCreate(BaseModel):
    """Criar proposta."""
    lead_id: int
    seller_id: Optional[int] = None
    property_info: PropertyInfo
    asked_value: float = Field(..., gt=0, description="Valor pedido pelo proprietário")
    offered_value: float = Field(..., gt=0, description="Valor oferecido pelo lead")
    deadline_hours: Optional[int] = Field(None, ge=1, le=720, description="Prazo em horas (max 30 dias)")
    notes: Optional[str] = None


class ProposalUpdate(BaseModel):
    """Atualizar proposta."""
    property_info: Optional[PropertyInfo] = None
    asked_value: Optional[float] = Field(None, gt=0)
    offered_value: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None


class ProposalEventInput(BaseModel):
    """Adicionar evento à timeline."""
    event: str
    value: Optional[float] = None
    note: Optional[str] = None


class ProposalResponse(BaseModel):
    """Resposta de proposta."""
    id: int
    lead_id: int
    lead_name: str
    seller_id: Optional[int]
    seller_name: Optional[str]
    property_info: dict
    asked_value: float
    offered_value: float
    final_value: Optional[float]
    status: str
    deadline: Optional[datetime]
    timeline: List[dict]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]

    # Computed fields
    diff_value: float  # Diferença entre pedido e oferta
    diff_percentage: float  # Percentual de diferença

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[ProposalResponse])
async def list_proposals(
    status: Optional[str] = None,
    lead_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    property_type: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    expired: bool = Query(False, description="Incluir expiradas"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista propostas comerciais com filtros.

    Filtros:
    - status: Status da proposta
    - lead_id: Propostas de um lead específico
    - seller_id: Propostas de um vendedor específico
    - property_type: Tipo de imóvel
    - min_value/max_value: Faixa de valores
    - expired: Se True, inclui propostas expiradas
    """
    query = select(CommercialProposal).where(CommercialProposal.tenant_id == tenant.id)

    # Filtros
    if status:
        query = query.where(CommercialProposal.status == status)

    if lead_id:
        query = query.where(CommercialProposal.lead_id == lead_id)

    if seller_id:
        query = query.where(CommercialProposal.seller_id == seller_id)

    if property_type:
        query = query.where(CommercialProposal.property_info['type'].astext == property_type)

    if min_value:
        query = query.where(CommercialProposal.offered_value >= min_value)

    if max_value:
        query = query.where(CommercialProposal.offered_value <= max_value)

    if not expired:
        # Exclui expiradas
        query = query.where(CommercialProposal.status != ProposalStatus.EXPIRED)

    # Ordenar por mais recentes
    query = query.order_by(CommercialProposal.created_at.desc())

    result = await db.execute(query)
    proposals = result.scalars().all()

    # Enriquecer com dados de lead/seller
    response = []
    for proposal in proposals:
        lead = await db.get(Lead, proposal.lead_id)
        seller_name = None
        if proposal.seller_id:
            from src.domain.entities.seller import Seller
            seller = await db.get(Seller, proposal.seller_id)
            if seller:
                seller_name = seller.name

        response.append(ProposalResponse(
            id=proposal.id,
            lead_id=proposal.lead_id,
            lead_name=lead.name if lead else "Lead removido",
            seller_id=proposal.seller_id,
            seller_name=seller_name,
            property_info=proposal.property_info,
            asked_value=float(proposal.asked_value),
            offered_value=float(proposal.offered_value),
            final_value=float(proposal.final_value) if proposal.final_value else None,
            status=proposal.status,
            deadline=proposal.deadline,
            timeline=proposal.timeline or [],
            notes=proposal.notes,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            closed_at=proposal.closed_at,
            diff_value=float(proposal.asked_value - proposal.offered_value),
            diff_percentage=round(
                ((proposal.asked_value - proposal.offered_value) / proposal.asked_value) * 100, 2
            )
        ))

    return response


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Busca proposta por ID."""
    proposal = await db.get(CommercialProposal, proposal_id)

    if not proposal or proposal.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposta não encontrada"
        )

    # Enriquecer
    lead = await db.get(Lead, proposal.lead_id)
    seller_name = None
    if proposal.seller_id:
        from src.domain.entities.seller import Seller
        seller = await db.get(Seller, proposal.seller_id)
        if seller:
            seller_name = seller.name

    return ProposalResponse(
        id=proposal.id,
        lead_id=proposal.lead_id,
        lead_name=lead.name if lead else "Lead removido",
        seller_id=proposal.seller_id,
        seller_name=seller_name,
        property_info=proposal.property_info,
        asked_value=float(proposal.asked_value),
        offered_value=float(proposal.offered_value),
        final_value=float(proposal.final_value) if proposal.final_value else None,
        status=proposal.status,
        deadline=proposal.deadline,
        timeline=proposal.timeline or [],
        notes=proposal.notes,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        closed_at=proposal.closed_at,
        diff_value=float(proposal.asked_value - proposal.offered_value),
        diff_percentage=round(
            ((proposal.asked_value - proposal.offered_value) / proposal.asked_value) * 100, 2
        )
    )


@router.post("", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    payload: ProposalCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria nova proposta comercial.

    Timeline inicial: lead_offered
    """
    # Validar lead
    lead = await db.get(Lead, payload.lead_id)
    if not lead or lead.tenant_id != tenant.id:
        raise HTTPException(404, "Lead não encontrado")

    # Calcular deadline
    deadline = None
    if payload.deadline_hours:
        deadline = datetime.now() + timedelta(hours=payload.deadline_hours)

    # Criar proposta
    proposal = CommercialProposal(
        tenant_id=tenant.id,
        lead_id=payload.lead_id,
        seller_id=payload.seller_id,
        created_by=user.id,
        property_info=payload.property_info.model_dump(),
        asked_value=payload.asked_value,
        offered_value=payload.offered_value,
        status=ProposalStatus.PENDING,
        deadline=deadline,
        notes=payload.notes,
        timeline=[{
            "date": datetime.now().isoformat(),
            "event": ProposalEvent.LEAD_OFFERED,
            "value": payload.offered_value,
            "note": f"Lead ofereceu R$ {payload.offered_value:,.2f}"
        }]
    )

    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    # Retornar com dados enriquecidos
    return await get_proposal(proposal.id, user, tenant, db)


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: int,
    payload: ProposalUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza proposta."""
    proposal = await db.get(CommercialProposal, proposal_id)

    if not proposal or proposal.tenant_id != tenant.id:
        raise HTTPException(404, "Proposta não encontrada")

    # Atualizar campos
    update_data = payload.model_dump(exclude_unset=True)

    # Converter PropertyInfo se presente
    if 'property_info' in update_data and update_data['property_info']:
        update_data['property_info'] = update_data['property_info'].model_dump()

    for field, value in update_data.items():
        setattr(proposal, field, value)

    await db.commit()
    await db.refresh(proposal)

    return await get_proposal(proposal.id, user, tenant, db)


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(
    proposal_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Deleta proposta."""
    proposal = await db.get(CommercialProposal, proposal_id)

    if not proposal or proposal.tenant_id != tenant.id:
        raise HTTPException(404, "Proposta não encontrada")

    await db.delete(proposal)
    await db.commit()

    return None


# =============================================================================
# AÇÕES ESPECIAIS
# =============================================================================

@router.post("/{proposal_id}/timeline", response_model=ProposalResponse)
async def add_timeline_event(
    proposal_id: int,
    event_data: ProposalEventInput,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Adiciona evento à timeline da proposta.

    Eventos comuns:
    - owner_rejected: Proprietário rejeitou
    - owner_accepted: Proprietário aceitou
    - lead_raised: Lead aumentou oferta
    - deadline_extended: Prazo estendido
    """
    proposal = await db.get(CommercialProposal, proposal_id)

    if not proposal or proposal.tenant_id != tenant.id:
        raise HTTPException(404, "Proposta não encontrada")

    # Adicionar evento
    proposal.add_timeline_event(
        event=event_data.event,
        value=event_data.value,
        note=event_data.note
    )

    # Atualizar status baseado no evento
    if event_data.event == ProposalEvent.OWNER_REJECTED:
        proposal.status = ProposalStatus.OWNER_REJECTED
    elif event_data.event == ProposalEvent.OWNER_ACCEPTED:
        proposal.status = ProposalStatus.OWNER_ACCEPTED
    elif event_data.event == ProposalEvent.CLOSED:
        proposal.status = ProposalStatus.CLOSED
        proposal.closed_at = datetime.now()
        proposal.final_value = event_data.value or proposal.offered_value

    await db.commit()
    await db.refresh(proposal)

    return await get_proposal(proposal.id, user, tenant, db)


@router.post("/{proposal_id}/close", response_model=ProposalResponse)
async def close_proposal(
    proposal_id: int,
    final_value: float,
    note: Optional[str] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Fecha proposta como aceita.

    Registra valor final e adiciona evento à timeline.
    """
    proposal = await db.get(CommercialProposal, proposal_id)

    if not proposal or proposal.tenant_id != tenant.id:
        raise HTTPException(404, "Proposta não encontrada")

    # Atualizar status
    proposal.status = ProposalStatus.CLOSED
    proposal.final_value = final_value
    proposal.closed_at = datetime.now()

    # Adicionar evento
    proposal.add_timeline_event(
        event=ProposalEvent.CLOSED,
        value=final_value,
        note=note or f"Proposta fechada em R$ {final_value:,.2f}"
    )

    await db.commit()
    await db.refresh(proposal)

    return await get_proposal(proposal.id, user, tenant, db)


@router.get("/stats/summary", response_model=dict)
async def get_proposals_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna estatísticas das propostas.

    Métricas:
    - Total de propostas
    - Propostas por status
    - Taxa de conversão
    - Valor médio
    """
    query = select(CommercialProposal).where(CommercialProposal.tenant_id == tenant.id)
    result = await db.execute(query)
    proposals = result.scalars().all()

    # Calcular métricas
    total = len(proposals)
    closed = len([p for p in proposals if p.status == ProposalStatus.CLOSED])
    pending = len([p for p in proposals if p.status == ProposalStatus.PENDING])
    rejected = len([p for p in proposals if p.status == ProposalStatus.OWNER_REJECTED])

    avg_offered = sum(float(p.offered_value) for p in proposals) / total if total > 0 else 0
    avg_asked = sum(float(p.asked_value) for p in proposals) / total if total > 0 else 0
    avg_final = sum(float(p.final_value) for p in proposals if p.final_value) / closed if closed > 0 else 0

    conversion_rate = (closed / total * 100) if total > 0 else 0

    return {
        "total_proposals": total,
        "closed": closed,
        "pending": pending,
        "rejected": rejected,
        "conversion_rate": round(conversion_rate, 2),
        "avg_offered_value": round(avg_offered, 2),
        "avg_asked_value": round(avg_asked, 2),
        "avg_final_value": round(avg_final, 2),
    }
