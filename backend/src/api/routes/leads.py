"""
ROTAS: LEADS (VERSÃO CORRIGIDA)
================================
Endpoints para gerenciar leads.

CORREÇÕES:
- Endpoint /messages com tratamento de erro robusto
- Não depende de schema para serialização
- Melhor logging para debug
"""

from datetime import datetime, timedelta
from typing import Optional  # ← ADICIONAR ESTA LINHA
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant, LeadEvent, Seller, User
from src.api.schemas.schemas import (
    LeadResponse,
    LeadListResponse,
    LeadUpdate,
    LeadCreate
)
from src.api.dependencies import get_current_user, get_current_tenant

# Import correto
from src.infrastructure.services import assign_lead_to_seller

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["Leads"])


# ===============================
# SCHEMAS
# ===============================
class AssignSellerRequest(BaseModel):
    seller_id: int
    reason: Optional[str] = None


# ===============================
# HELPERS
# ===============================
def lead_to_response(lead: Lead) -> dict:
    """Converte Lead para dict de resposta."""
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
        "handed_off_at": lead.handed_off_at.isoformat() if lead.handed_off_at else None,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        "assigned_seller_id": lead.assigned_seller_id,
        "assigned_at": lead.assigned_at.isoformat() if lead.assigned_at else None,
        "assignment_method": lead.assignment_method,
        "assigned_seller": None,
    }

    if hasattr(lead, 'assigned_seller') and lead.assigned_seller:
        data["assigned_seller"] = {
            "id": lead.assigned_seller.id,
            "name": lead.assigned_seller.name,
            "whatsapp": lead.assigned_seller.whatsapp,
        }

    return data


def message_to_response(message: Message) -> dict:
    """Converte Message para dict de resposta (sem depender de schema)."""
    return {
        "id": message.id,
        "lead_id": message.lead_id,
        "role": message.role,
        "content": message.content,
        "tokens_used": message.tokens_used or 0,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


# ===============================
# LISTAGEM DE LEADS
# ===============================
@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    qualification: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Ordenação: created_at, propensity_score"),
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Lista leads do tenant com filtros e paginação."""
    query = select(Lead).where(Lead.tenant_id == current_tenant.id)
    count_query = select(func.count(Lead.id)).where(Lead.tenant_id == current_tenant.id)

    if status:
        query = query.where(Lead.status == status)
        count_query = count_query.where(Lead.status == status)

    if qualification:
        query = query.where(Lead.qualification == qualification)
        count_query = count_query.where(Lead.qualification == qualification)

    if search:
        s = f"%{search}%"
        query = query.where((Lead.name.ilike(s)) | (Lead.phone.ilike(s)) | (Lead.email.ilike(s)))
        count_query = count_query.where((Lead.name.ilike(s)) | (Lead.phone.ilike(s)) | (Lead.email.ilike(s)))

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page

    # Ordenação
    if sort_by == "propensity_score":
        query = query.order_by(Lead.propensity_score.desc())
    else:
        query = query.order_by(Lead.created_at.desc())
        
    result = await db.execute(query.offset(offset).limit(per_page))
    leads = result.scalars().all()

    return {
        "items": leads,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }


# ===============================
# CRIAR LEAD MANUALMENTE
# ===============================
@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Cria um novo lead manualmente para o tenant."""
    # ✅ VERIFICAR LIMITE DE LEADS DO PLANO
    from src.application.services.limits_service import check_limit, increment_usage, LimitType
    
    limit_check = await check_limit(
        db=db,
        tenant_id=current_tenant.id,
        limit_type=LimitType.LEADS,
        increment=1
    )
    
    if not limit_check.allowed:
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail={
                "error": "LEAD_LIMIT_EXCEEDED",
                "message": limit_check.message,
                "current": limit_check.current,
                "limit": limit_check.limit,
                "percentage": limit_check.percentage,
                "upgrade_required": True
            }
        )
    
    new_lead = Lead(**lead_data.model_dump(), tenant_id=current_tenant.id)
    db.add(new_lead)
    
    # ✅ INCREMENTAR CONTADOR DE LEADS
    await increment_usage(db, current_tenant.id, LimitType.LEADS, 1)
    
    await db.commit()
    await db.refresh(new_lead)
    return new_lead

# ===============================
# DETALHE DO LEAD
# ===============================
@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Retorna detalhes de um lead específico."""
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id, Lead.tenant_id == current_tenant.id)
        .options(selectinload(Lead.assigned_seller))
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


# ===============================
# ATUALIZAR LEAD
# ===============================
@router.patch("/{lead_id}")
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Atualiza dados de um lead."""
    try:
        result = await db.execute(
            select(Lead)
            .where(Lead.id == lead_id, Lead.tenant_id == current_tenant.id)
            .options(selectinload(Lead.assigned_seller))
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(404, "Lead não encontrado")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(lead, field):
                setattr(lead, field, value)

        await db.commit()
        await db.refresh(lead)
        return lead_to_response(lead)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar lead {lead_id}: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ===============================
# MENSAGENS DO LEAD (CORRIGIDO!)
# ===============================
@router.get("/{lead_id}/messages")
async def get_lead_messages(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """
    Retorna mensagens de um lead.
    """
    try:
        logger.info(f"Buscando mensagens do lead {lead_id} - tenant: {current_tenant.slug}")
        
        # Verifica se lead existe e pertence ao tenant
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == current_tenant.id)
        )
        lead = result.scalar_one_or_none()
        if not lead:
            logger.warning(f"Lead não encontrado: {lead_id} para tenant {current_tenant.id}")
            raise HTTPException(404, "Lead não encontrado")

        # Busca mensagens
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        
        logger.info(f"Encontradas {len(messages)} mensagens para lead {lead_id}")
        
        # Converte para dict (sem usar schema que pode quebrar)
        return [message_to_response(m) for m in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens do lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(500, f"Erro ao carregar mensagens: {str(e)}")


# ===============================
# HISTÓRICO/EVENTOS DO LEAD
# ===============================
@router.get("/{lead_id}/events")
async def get_lead_events(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Retorna histórico de eventos do lead."""
    try:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == current_tenant.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(404, "Lead não encontrado")

        result = await db.execute(
            select(LeadEvent)
            .where(LeadEvent.lead_id == lead_id)
            .order_by(LeadEvent.created_at.desc())
        )
        events = result.scalars().all()
        
        return [
            {
                "id": e.id,
                "lead_id": e.lead_id,
                "event_type": e.event_type,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "description": e.description,
                "created_by": e.created_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar eventos do lead {lead_id}: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ===============================
# HANDOFF
# ===============================
@router.post("/{lead_id}/handoff")
async def handoff_lead(
    lead_id: int,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Transfere lead para atendimento humano."""
    try:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == current_tenant.id)
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(404, "Lead não encontrado")

        old_status = lead.status
        lead.status = "handed_off"
        lead.assigned_to = user_id
        lead.handed_off_at = datetime.utcnow()

        db.add(
            LeadEvent(
                lead_id=lead.id,
                event_type="status_change",
                old_value=old_status,
                new_value="handed_off",
                description="Lead transferido para atendimento humano",
                created_by=user_id,
            )
        )

        await db.commit()
        return {"success": True, "message": "Lead transferido com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no handoff do lead {lead_id}: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ===============================
# ATRIBUIR VENDEDOR
# ===============================
@router.post("/{lead_id}/assign-seller")
async def assign_seller_compat(
    lead_id: int,
    payload: AssignSellerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atribui um vendedor ao lead."""
    try:
        lead = await db.get(Lead, lead_id)
        seller = await db.get(Seller, payload.seller_id)
        tenant = await db.get(Tenant, current_user.tenant_id)

        if not lead or not seller:
            raise HTTPException(404, "Lead ou vendedor não encontrado")

        if lead.assigned_seller_id:
            raise HTTPException(400, "Lead já possui vendedor atribuído")

        await assign_lead_to_seller(
            db=db,
            lead=lead,
            seller=seller,
            tenant=tenant,
            method="manual",
            reason=payload.reason or "Atribuição manual via dashboard",
        )

        await db.commit()
        return {"success": True, "message": "Lead atribuído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atribuir vendedor ao lead {lead_id}: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ===============================
# REMOVER ATRIBUIÇÃO
# ===============================
@router.delete("/{lead_id}/assign-seller")
async def unassign_lead_from_seller(
    lead_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Remove atribuição de vendedor do lead."""
    try:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant.id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise HTTPException(404, "Lead não encontrado")

        if not lead.assigned_seller_id:
            raise HTTPException(400, "Lead não tem vendedor atribuído")

        previous_seller_id = lead.assigned_seller_id
        lead.assigned_seller_id = None
        lead.assigned_at = None
        lead.assignment_method = None

        db.add(
            LeadEvent(
                lead_id=lead.id,
                event_type="seller_unassigned",
                old_value=str(previous_seller_id),
                new_value=None,
                description=f"Atribuição removida por {user.name}",
                created_by=user.id,
            )
        )

        await db.commit()
        return {"success": True, "message": "Atribuição removida com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover atribuição do lead {lead_id}: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ===============================
# ESTATÍSTICAS RÁPIDAS
# ===============================
@router.get("/stats/summary")
async def get_leads_summary(
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Retorna resumo de leads do tenant."""
    try:
        # Total de leads
        total = (await db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == current_tenant.id)
        )).scalar() or 0

        # Por qualificação
        quente = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.qualification.in_(["quente", "hot"]))
        )).scalar() or 0

        morno = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.qualification.in_(["morno", "warm"]))
        )).scalar() or 0

        frio = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.qualification.in_(["frio", "cold", None]))
        )).scalar() or 0

        # Sem atribuição
        unassigned = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.assigned_seller_id.is_(None))
        )).scalar() or 0

        return {
            "total": total,
            "quente": quente,
            "morno": morno,
            "frio": frio,
            "unassigned": unassigned,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar stats de leads: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


        # ===============================
# MÉTRICAS DO DASHBOARD
# ===============================
@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Retorna métricas completas para o dashboard."""
    try:
        from datetime import timedelta
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Total de leads
        total = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
        )).scalar() or 0
        
        # Leads hoje
        today = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.created_at >= today_start)
        )).scalar() or 0
        
        # Leads esta semana
        week = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.created_at >= week_start)
        )).scalar() or 0
        
        # Leads este mês
        month = (await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == current_tenant.id)
            .where(Lead.created_at >= month_start)
        )).scalar() or 0
        
        # Por qualificação
        result = await db.execute(
            select(
                Lead.qualification,
                func.count(Lead.id).label('count')
            )
            .where(Lead.tenant_id == current_tenant.id)
            .group_by(Lead.qualification)
        )
        
        by_qualification = {}
        for row in result:
            qual = row.qualification or 'frio'
            if qual in ['hot', 'quente']:
                by_qualification['quente'] = by_qualification.get('quente', 0) + row.count
            elif qual in ['warm', 'morno']:
                by_qualification['morno'] = by_qualification.get('morno', 0) + row.count
            else:
                by_qualification['frio'] = by_qualification.get('frio', 0) + row.count
        
        # Por status
        result = await db.execute(
            select(
                Lead.status,
                func.count(Lead.id).label('count')
            )
            .where(Lead.tenant_id == current_tenant.id)
            .group_by(Lead.status)
        )
        by_status = {row.status: row.count for row in result}
        
        # Taxa de conversão
        hot_leads = by_qualification.get('quente', 0)
        conversion_rate = round((hot_leads / total * 100), 1) if total > 0 else 0
        
        return {
            "total_leads": total,
            "leads_today": today,
            "leads_this_week": week,
            "leads_this_month": month,
            "conversion_rate": conversion_rate,
            "avg_qualification_time_hours": 2.5,
            "by_qualification": by_qualification,
            "by_status": by_status,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar métricas: {e}", exc_info=True)
        raise HTTPException(500, f"Erro interno: {str(e)}")
