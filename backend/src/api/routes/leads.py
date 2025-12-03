"""
ROTAS: LEADS
=============

Endpoints para gerenciar leads.
Usado pelo dashboard para listar, ver detalhes, atualizar.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant, LeadEvent, Seller, User
from src.api.schemas import (
    LeadResponse,
    LeadListResponse,
    LeadUpdate,
    MessageResponse,
    SellerSummary,
)
from src.api.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/leads", tags=["Leads"])


# ==========================================
# SCHEMAS
# ==========================================

class AssignSellerRequest(BaseModel):
    seller_id: int
    reason: Optional[str] = None


# ==========================================
# HELPERS
# ==========================================

def lead_to_response(lead: Lead) -> dict:
    """Converte Lead para dict de resposta com vendedor."""
    data = {
        "id": lead.id,
        "tenant_id": lead.tenant_id,
        "channel_id": lead.channel_id,
        "external_id": lead.external_id,
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "city": lead.city,
        "custom_data": lead.custom_data or {},
        "source": lead.source,
        "campaign": lead.campaign,
        "qualification": lead.qualification,
        "status": lead.status,
        "summary": lead.summary,
        "assigned_to": lead.assigned_to,
        "handed_off_at": lead.handed_off_at,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
        "assigned_seller_id": lead.assigned_seller_id,
        "assigned_at": lead.assigned_at,
        "assignment_method": lead.assignment_method,
        "assigned_seller": None,
    }
    
    # Adiciona vendedor se existir
    if lead.assigned_seller:
        data["assigned_seller"] = {
            "id": lead.assigned_seller.id,
            "name": lead.assigned_seller.name,
            "whatsapp": lead.assigned_seller.whatsapp,
        }
    
    return data


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("")
async def list_leads(
    tenant_slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    qualification: Optional[str] = None,
    channel_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    assigned_seller_id: Optional[int] = None,
    unassigned: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Lista leads do tenant com filtros e paginação.
    """
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Monta query base com eager loading do vendedor
    query = (
        select(Lead)
        .where(Lead.tenant_id == tenant.id)
        .options(selectinload(Lead.assigned_seller))
    )
    count_query = select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
    
    # Aplica filtros
    if status:
        query = query.where(Lead.status == status)
        count_query = count_query.where(Lead.status == status)
    
    if qualification:
        query = query.where(Lead.qualification == qualification)
        count_query = count_query.where(Lead.qualification == qualification)
    
    if channel_id:
        query = query.where(Lead.channel_id == channel_id)
        count_query = count_query.where(Lead.channel_id == channel_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Lead.name.ilike(search_filter)) |
            (Lead.phone.ilike(search_filter)) |
            (Lead.email.ilike(search_filter))
        )
        count_query = count_query.where(
            (Lead.name.ilike(search_filter)) |
            (Lead.phone.ilike(search_filter)) |
            (Lead.email.ilike(search_filter))
        )
    
    if date_from:
        query = query.where(Lead.created_at >= date_from)
        count_query = count_query.where(Lead.created_at >= date_from)
    
    if date_to:
        query = query.where(Lead.created_at <= date_to)
        count_query = count_query.where(Lead.created_at <= date_to)
    
    if assigned_seller_id:
        query = query.where(Lead.assigned_seller_id == assigned_seller_id)
        count_query = count_query.where(Lead.assigned_seller_id == assigned_seller_id)
    
    if unassigned:
        query = query.where(Lead.assigned_seller_id == None)
        count_query = count_query.where(Lead.assigned_seller_id == None)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginação
    offset = (page - 1) * per_page
    query = query.order_by(Lead.created_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return {
        "items": [lead_to_response(lead) for lead in leads],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }


@router.get("/{lead_id}")
async def get_lead(
    lead_id: int,
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca lead por ID."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
        .options(selectinload(Lead.assigned_seller))
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    return lead_to_response(lead)


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: int,
    tenant_slug: str,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza dados do lead."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
        .options(selectinload(Lead.assigned_seller))
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Atualiza campos
    update_data = payload.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(lead, field):
            setattr(lead, field, value)
    
    await db.commit()
    await db.refresh(lead)
    
    return lead_to_response(lead)


@router.get("/{lead_id}/messages", response_model=list[MessageResponse])
async def get_lead_messages(
    lead_id: int,
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca histórico de mensagens do lead."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Verifica se lead pertence ao tenant
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Busca mensagens
    result = await db.execute(
        select(Message)
        .where(Message.lead_id == lead_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    
    return [MessageResponse.model_validate(msg) for msg in messages]


@router.post("/{lead_id}/handoff")
async def handoff_lead(
    lead_id: int,
    tenant_slug: str,
    user_id: int = Query(..., description="ID do usuário que vai assumir"),
    db: AsyncSession = Depends(get_db),
):
    """
    Passa o lead para atendimento humano.
    Marca como handed_off e atribui a um usuário.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Atualiza lead
    old_status = lead.status
    lead.status = "handed_off"
    lead.assigned_to = user_id
    lead.handed_off_at = datetime.utcnow()
    
    # Registra evento
    event = LeadEvent(
        lead_id=lead.id,
        event_type="status_change",
        old_value=old_status,
        new_value="handed_off",
        description=f"Lead transferido para atendimento humano",
        created_by=user_id,
    )
    db.add(event)
    
    await db.commit()
    
    return {"success": True, "message": "Lead transferido com sucesso"}


@router.post("/{lead_id}/assign-seller")
async def assign_lead_to_seller_endpoint(
    lead_id: int,
    payload: AssignSellerRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atribui um lead manualmente a um vendedor.
    """
    from src.infrastructure.services import manual_assign_lead
    
    # Busca o lead
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Busca o vendedor
    result = await db.execute(
        select(Seller)
        .where(Seller.id == payload.seller_id)
        .where(Seller.tenant_id == tenant.id)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    if not seller.active:
        raise HTTPException(status_code=400, detail="Vendedor está inativo")
    
    # Guarda vendedor anterior (se houver)
    previous_seller_id = lead.assigned_seller_id
    
    # Executa a atribuição
    result = await manual_assign_lead(
        db=db,
        lead=lead,
        seller=seller,
        tenant=tenant,
        assigned_by=user.name,
    )
    
    # Registra evento
    event = LeadEvent(
        lead_id=lead.id,
        event_type="seller_assigned",
        old_value=str(previous_seller_id) if previous_seller_id else None,
        new_value=str(seller.id),
        description=f"Lead atribuído para {seller.name} por {user.name}",
        created_by=user.id,
    )
    db.add(event)
    await db.commit()
    
    return {
        "success": True,
        "message": f"Lead atribuído para {seller.name}",
        "seller": {
            "id": seller.id,
            "name": seller.name,
            "whatsapp": seller.whatsapp,
        },
        "notifications_sent": result.get("notifications_sent", []),
    }


@router.delete("/{lead_id}/assign-seller")
async def unassign_lead_from_seller(
    lead_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove atribuição de vendedor de um lead.
    """
    # Busca o lead
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    if not lead.assigned_seller_id:
        raise HTTPException(status_code=400, detail="Lead não tem vendedor atribuído")
    
    # Guarda vendedor anterior
    previous_seller_id = lead.assigned_seller_id
    
    # Remove atribuição
    lead.assigned_seller_id = None
    lead.assigned_at = None
    lead.assignment_method = None
    
    # Registra evento
    event = LeadEvent(
        lead_id=lead.id,
        event_type="seller_unassigned",
        old_value=str(previous_seller_id),
        new_value=None,
        description=f"Atribuição removida por {user.name}",
        created_by=user.id,
    )
    db.add(event)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Atribuição removida com sucesso",
    }