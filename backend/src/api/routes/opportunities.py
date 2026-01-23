"""
ROTAS: OPPORTUNITIES
====================

Endpoints para gerenciar oportunidades/negócios vinculados a leads.

Endpoints:
- GET /opportunities - Lista oportunidades do tenant
- GET /opportunities/{id} - Busca oportunidade por ID
- GET /leads/{lead_id}/opportunities - Lista oportunidades de um lead
- POST /leads/{lead_id}/opportunities - Cria oportunidade para um lead
- PATCH /opportunities/{id} - Atualiza oportunidade
- DELETE /opportunities/{id} - Remove oportunidade
- POST /opportunities/{id}/win - Marca como ganha
- POST /opportunities/{id}/lose - Marca como perdida
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import get_db
from src.domain.entities import User, Lead, Opportunity, Seller, Product
from src.domain.entities.enums import OpportunityStatus, LeadStatus
from src.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


# =============================================
# SCHEMAS
# =============================================

class OpportunityCreate(BaseModel):
    """Input para criar oportunidade."""
    title: str = Field(..., max_length=200)
    product_id: Optional[int] = None
    seller_id: Optional[int] = None
    value: int = Field(default=0, description="Valor em centavos")
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None
    custom_data: Optional[dict] = None


class OpportunityUpdate(BaseModel):
    """Input para atualizar oportunidade."""
    title: Optional[str] = Field(None, max_length=200)
    product_id: Optional[int] = None
    seller_id: Optional[int] = None
    value: Optional[int] = None
    status: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None
    custom_data: Optional[dict] = None


class OpportunityResponse(BaseModel):
    """Resposta de oportunidade."""
    id: int
    lead_id: int
    tenant_id: int
    title: str
    value: int
    status: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    seller_id: Optional[int] = None
    seller_name: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    won_at: Optional[datetime] = None
    lost_at: Optional[datetime] = None
    lost_reason: Optional[str] = None
    notes: Optional[str] = None
    custom_data: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    """Resposta de lista de oportunidades."""
    items: List[OpportunityResponse]
    total: int
    page: int
    per_page: int


class WinInput(BaseModel):
    """Input para marcar oportunidade como ganha."""
    notes: Optional[str] = None


class LoseInput(BaseModel):
    """Input para marcar oportunidade como perdida."""
    reason: str = Field(..., max_length=200)
    notes: Optional[str] = None


# =============================================
# HELPERS
# =============================================

def opportunity_to_response(opp: Opportunity) -> OpportunityResponse:
    """Converte Opportunity para resposta."""
    return OpportunityResponse(
        id=opp.id,
        lead_id=opp.lead_id,
        tenant_id=opp.tenant_id,
        title=opp.title,
        value=opp.value,
        status=opp.status,
        product_id=opp.product_id,
        product_name=opp.product.name if opp.product else None,
        seller_id=opp.seller_id,
        seller_name=opp.seller.name if opp.seller else None,
        expected_close_date=opp.expected_close_date,
        won_at=opp.won_at,
        lost_at=opp.lost_at,
        lost_reason=opp.lost_reason,
        notes=opp.notes,
        custom_data=opp.custom_data,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


# =============================================
# ENDPOINTS
# =============================================

@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    seller_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas as oportunidades do tenant.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        query = select(Opportunity).where(Opportunity.tenant_id == tenant_id)
        count_query = select(func.count(Opportunity.id)).where(Opportunity.tenant_id == tenant_id)

        if status:
            query = query.where(Opportunity.status == status)
            count_query = count_query.where(Opportunity.status == status)

        if seller_id:
            query = query.where(Opportunity.seller_id == seller_id)
            count_query = count_query.where(Opportunity.seller_id == seller_id)

        total = (await db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page

        result = await db.execute(
            query
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
            .order_by(Opportunity.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        opportunities = result.scalars().all()

        return OpportunityListResponse(
            items=[opportunity_to_response(o) for o in opportunities],
            total=total,
            page=page,
            per_page=per_page,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro listando oportunidades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao listar oportunidades")


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca oportunidade por ID.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
        )
        opp = result.scalar_one_or_none()

        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        return opportunity_to_response(opp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro buscando oportunidade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar oportunidade")


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: int,
    data: OpportunityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza oportunidade.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
        )
        opp = result.scalar_one_or_none()

        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        # Atualiza campos
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(opp, field, value)

        await db.commit()
        await db.refresh(opp)

        logger.info(f"Oportunidade atualizada: {opportunity_id}")
        return opportunity_to_response(opp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro atualizando oportunidade: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao atualizar oportunidade")


@router.delete("/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove oportunidade.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
        )
        opp = result.scalar_one_or_none()

        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        await db.delete(opp)
        await db.commit()

        logger.info(f"Oportunidade removida: {opportunity_id}")
        return {"success": True, "message": "Oportunidade removida"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro removendo oportunidade: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao remover oportunidade")


@router.post("/{opportunity_id}/win", response_model=OpportunityResponse)
async def win_opportunity(
    opportunity_id: int,
    data: WinInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marca oportunidade como ganha.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
        )
        opp = result.scalar_one_or_none()

        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        opp.status = OpportunityStatus.WON.value
        opp.won_at = datetime.now(timezone.utc)
        if data.notes:
            opp.notes = (opp.notes or "") + f"\n\n[GANHO] {data.notes}"

        await db.commit()
        await db.refresh(opp)

        logger.info(f"Oportunidade ganha: {opportunity_id}")
        return opportunity_to_response(opp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro marcando oportunidade como ganha: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao marcar oportunidade como ganha")


@router.post("/{opportunity_id}/lose", response_model=OpportunityResponse)
async def lose_opportunity(
    opportunity_id: int,
    data: LoseInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marca oportunidade como perdida.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
        )
        opp = result.scalar_one_or_none()

        if not opp:
            raise HTTPException(status_code=404, detail="Oportunidade não encontrada")

        opp.status = OpportunityStatus.LOST.value
        opp.lost_at = datetime.now(timezone.utc)
        opp.lost_reason = data.reason
        if data.notes:
            opp.notes = (opp.notes or "") + f"\n\n[PERDIDO] {data.notes}"

        await db.commit()
        await db.refresh(opp)

        logger.info(f"Oportunidade perdida: {opportunity_id}")
        return opportunity_to_response(opp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro marcando oportunidade como perdida: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao marcar oportunidade como perdida")


# =============================================
# ENDPOINTS POR LEAD
# =============================================

leads_router = APIRouter(prefix="/leads", tags=["Opportunities"])


@leads_router.get("/{lead_id}/opportunities", response_model=List[OpportunityResponse])
async def list_lead_opportunities(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista oportunidades de um lead específico.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Verifica se lead existe
        lead_result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        )
        lead = lead_result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.lead_id == lead_id, Opportunity.tenant_id == tenant_id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
            .order_by(Opportunity.created_at.desc())
        )
        opportunities = result.scalars().all()

        return [opportunity_to_response(o) for o in opportunities]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro listando oportunidades do lead: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao listar oportunidades")


@leads_router.post("/{lead_id}/opportunities", response_model=OpportunityResponse, status_code=201)
async def create_lead_opportunity(
    lead_id: int,
    data: OpportunityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria nova oportunidade para um lead.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Verifica se lead existe
        lead_result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        )
        lead = lead_result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Verifica produto se fornecido
        if data.product_id:
            product_result = await db.execute(
                select(Product).where(Product.id == data.product_id, Product.tenant_id == tenant_id)
            )
            if not product_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Produto não encontrado")

        # Verifica vendedor se fornecido
        if data.seller_id:
            seller_result = await db.execute(
                select(Seller).where(Seller.id == data.seller_id, Seller.tenant_id == tenant_id)
            )
            if not seller_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Vendedor não encontrado")

        # Cria oportunidade
        opp = Opportunity(
            tenant_id=tenant_id,
            lead_id=lead_id,
            title=data.title,
            product_id=data.product_id,
            seller_id=data.seller_id or lead.assigned_seller_id,  # Herda vendedor do lead se não especificado
            value=data.value,
            expected_close_date=data.expected_close_date,
            notes=data.notes,
            custom_data=data.custom_data or {},
        )

        db.add(opp)
        await db.commit()
        await db.refresh(opp)

        # Carrega relacionamentos
        result = await db.execute(
            select(Opportunity)
            .where(Opportunity.id == opp.id)
            .options(selectinload(Opportunity.product), selectinload(Opportunity.seller))
        )
        opp = result.scalar_one()

        logger.info(f"Oportunidade criada: {opp.id} para lead {lead_id}")
        return opportunity_to_response(opp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro criando oportunidade: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao criar oportunidade")


# =============================================
# MÉTRICAS DE OPORTUNIDADES
# =============================================

class OpportunityMetrics(BaseModel):
    """Métricas de oportunidades."""
    total: int = 0
    by_status: dict = {}
    total_value: int = 0
    won_value: int = 0
    lost_count: int = 0
    conversion_rate: float = 0


@router.get("/metrics/summary", response_model=OpportunityMetrics)
async def get_opportunity_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas resumidas de oportunidades.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Total
        total_result = await db.execute(
            select(func.count(Opportunity.id)).where(Opportunity.tenant_id == tenant_id)
        )
        total = total_result.scalar() or 0

        # Por status
        status_result = await db.execute(
            select(Opportunity.status, func.count(Opportunity.id))
            .where(Opportunity.tenant_id == tenant_id)
            .group_by(Opportunity.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # Valor total
        value_result = await db.execute(
            select(func.sum(Opportunity.value))
            .where(Opportunity.tenant_id == tenant_id)
        )
        total_value = value_result.scalar() or 0

        # Valor ganho
        won_result = await db.execute(
            select(func.sum(Opportunity.value))
            .where(Opportunity.tenant_id == tenant_id, Opportunity.status == OpportunityStatus.WON.value)
        )
        won_value = won_result.scalar() or 0

        # Perdidos
        lost_count = by_status.get(OpportunityStatus.LOST.value, 0)

        # Taxa de conversão
        closed = by_status.get(OpportunityStatus.WON.value, 0) + lost_count
        conversion_rate = (by_status.get(OpportunityStatus.WON.value, 0) / closed * 100) if closed > 0 else 0

        return OpportunityMetrics(
            total=total,
            by_status=by_status,
            total_value=total_value,
            won_value=won_value,
            lost_count=lost_count,
            conversion_rate=round(conversion_rate, 1),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro buscando métricas de oportunidades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar métricas")
