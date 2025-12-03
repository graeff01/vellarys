"""
ROTAS: MÉTRICAS
================

Endpoints para métricas do dashboard.
Dados consolidados para análise do gestor.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Tenant, LeadEvent
from src.api.schemas import DashboardMetrics, LeadsByPeriod

router = APIRouter(prefix="/metrics", tags=["Métricas"])


@router.get("", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas consolidadas do dashboard.
    
    Inclui:
    - Total de leads por período
    - Distribuição por qualificação
    - Distribuição por status
    - Distribuição por canal
    - Taxa de conversão
    - Tempo médio de qualificação
    """
    
    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # Total geral
    total_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
    )
    total_leads = total_result.scalar() or 0
    
    # Leads hoje
    today_result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.created_at >= today_start)
    )
    leads_today = today_result.scalar() or 0
    
    # Leads esta semana
    week_result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.created_at >= week_start)
    )
    leads_this_week = week_result.scalar() or 0
    
    # Leads este mês
    month_result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.created_at >= month_start)
    )
    leads_this_month = month_result.scalar() or 0
    
    # Por qualificação
    qual_result = await db.execute(
        select(Lead.qualification, func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .group_by(Lead.qualification)
    )
    by_qualification = {row[0]: row[1] for row in qual_result.all()}
    
    # Por status
    status_result = await db.execute(
        select(Lead.status, func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .group_by(Lead.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}
    
    # Por canal
    channel_result = await db.execute(
        select(Lead.channel_id, func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .group_by(Lead.channel_id)
    )
    by_channel = {str(row[0] or "direct"): row[1] for row in channel_result.all()}
    
    # Por source
    source_result = await db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.tenant_id == tenant.id)
        .group_by(Lead.source)
    )
    by_source = {row[0]: row[1] for row in source_result.all()}
    
    # Taxa de conversão (qualified / total)
    qualified_count = by_status.get("qualified", 0) + by_status.get("handed_off", 0) + by_status.get("closed", 0)
    conversion_rate = (qualified_count / total_leads * 100) if total_leads > 0 else 0
    
    # Tempo médio de qualificação
    avg_time_result = await db.execute(
        select(func.avg(
            func.extract('epoch', LeadEvent.created_at) - 
            func.extract('epoch', Lead.created_at)
        ))
        .join(Lead, LeadEvent.lead_id == Lead.id)
        .where(Lead.tenant_id == tenant.id)
        .where(LeadEvent.event_type == "status_change")
        .where(LeadEvent.new_value == "qualified")
    )
    avg_seconds = avg_time_result.scalar()
    avg_qualification_time_hours = (avg_seconds / 3600) if avg_seconds else 0
    
    return DashboardMetrics(
        total_leads=total_leads,
        leads_today=leads_today,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        by_qualification=by_qualification,
        by_status=by_status,
        by_channel=by_channel,
        by_source=by_source,
        conversion_rate=round(conversion_rate, 2),
        avg_qualification_time_hours=round(avg_qualification_time_hours, 2),
    )


@router.get("/leads-by-day", response_model=list[LeadsByPeriod])
async def get_leads_by_day(
    tenant_slug: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna leads agrupados por dia.
    Útil para gráficos de evolução.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Agrupa por dia
    result = await db.execute(
        select(
            func.date(Lead.created_at).label("day"),
            func.count(Lead.id).label("count"),
            func.sum(case((Lead.qualification == "hot", 1), else_=0)).label("hot"),
            func.sum(case((Lead.qualification == "warm", 1), else_=0)).label("warm"),
            func.sum(case((Lead.qualification == "cold", 1), else_=0)).label("cold"),
        )
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.created_at >= start_date)
        .group_by(func.date(Lead.created_at))
        .order_by(func.date(Lead.created_at))
    )
    
    return [
        LeadsByPeriod(
            period=str(row.day),
            count=row.count,
            hot=row.hot or 0,
            warm=row.warm or 0,
            cold=row.cold or 0,
        )
        for row in result.all()
    ]


@router.get("/top-campaigns")
async def get_top_campaigns(
    tenant_slug: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna campanhas com mais leads.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    result = await db.execute(
        select(Lead.campaign, func.count(Lead.id).label("count"))
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.campaign.isnot(None))
        .group_by(Lead.campaign)
        .order_by(func.count(Lead.id).desc())
        .limit(limit)
    )
    
    return [
        {"campaign": row.campaign, "count": row.count}
        for row in result.all()
    ]
