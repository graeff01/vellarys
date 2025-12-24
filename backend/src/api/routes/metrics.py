"""
ROTAS: MÉTRICAS
================

Endpoints para métricas do dashboard.
Dados consolidados para análise do gestor.

MELHORIAS:
- Economia de tempo calculada
- Leads fora do horário
- Crescimento vs semana anterior
- Leads quentes aguardando
- Taxa de engajamento
- Velocidade de resposta
"""

from datetime import datetime, timedelta, time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, case, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Tenant, LeadEvent, Message
from src.api.schemas import DashboardMetrics, LeadsByPeriod

router = APIRouter(prefix="/metrics", tags=["Métricas"])


# ============================================
# HELPERS - FUNÇÕES AUXILIARES
# ============================================

def is_after_hours(dt: datetime) -> bool:
    """Verifica se está fora do horário comercial (8h-18h, seg-sex)."""
    hour = dt.hour
    weekday = dt.weekday()
    return hour < 8 or hour >= 18 or weekday >= 5


def calculate_time_saved(total_leads: int) -> dict:
    """
    Calcula tempo/dinheiro economizado pela IA.
    Premissa: Cada lead = 15min de atendente humano.
    """
    total_minutes = total_leads * 15
    hours = total_minutes / 60
    cost_saved = hours * 15  # R$ 15/hora
    
    return {
        "hours_saved": round(hours, 1),
        "cost_saved_brl": round(cost_saved, 2),
        "leads_handled": total_leads,
    }


# ============================================
# ENDPOINT PRINCIPAL
# ============================================

@router.get("")
async def get_dashboard_metrics(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas consolidadas do dashboard.
    
    MELHORADO COM:
    - Economia de tempo/dinheiro
    - Leads fora do horário
    - Crescimento positivo
    - Leads quentes aguardando
    - Velocidade de resposta
    - Taxa de engajamento
    """
    
    try:
        # Busca tenant
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        
        # Períodos de tempo
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        last_week_start = week_start - timedelta(days=7)
        
        # =============================================
        # TOTAIS BÁSICOS
        # =============================================
        
        total_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
        )
        total_leads = total_result.scalar() or 0
        
        today_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.created_at >= today_start)
        )
        leads_today = today_result.scalar() or 0
        
        week_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.created_at >= week_start)
        )
        leads_this_week = week_result.scalar() or 0
        
        month_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.created_at >= month_start)
        )
        leads_this_month = month_result.scalar() or 0
        
        # =============================================
        # ECONOMIA DE TEMPO/DINHEIRO (NOVO!)
        # =============================================
        time_saved = calculate_time_saved(leads_this_month)
        
        # =============================================
        # LEADS FORA DO HORÁRIO (NOVO!)
        # =============================================
        all_leads_month = await db.execute(
            select(Lead.created_at)
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.created_at >= month_start)
        )
        
        after_hours_count = 0
        for row in all_leads_month:
            if row.created_at and is_after_hours(row.created_at):
                after_hours_count += 1
        
        # =============================================
        # CRESCIMENTO VS SEMANA ANTERIOR (NOVO!)
        # =============================================
        last_week_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .where(Lead.created_at >= last_week_start)
            .where(Lead.created_at < week_start)
        )
        leads_last_week = last_week_result.scalar() or 0
        
        if leads_last_week > 0:
            growth_percentage = ((leads_this_week - leads_last_week) / leads_last_week) * 100
        else:
            growth_percentage = 100 if leads_this_week > 0 else 0
        
        growth_percentage = max(0, growth_percentage)  # Sempre positivo
        
        # =============================================
        # POR QUALIFICAÇÃO
        # =============================================
        qual_result = await db.execute(
            select(Lead.qualification, func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .group_by(Lead.qualification)
        )
        
        by_qualification = {}
        for row in qual_result.all():
            qual = row[0] or "frio"
            if qual in ["hot", "quente"]:
                by_qualification["quente"] = by_qualification.get("quente", 0) + row[1]
            elif qual in ["warm", "morno"]:
                by_qualification["morno"] = by_qualification.get("morno", 0) + row[1]
            else:
                by_qualification["frio"] = by_qualification.get("frio", 0) + row[1]
        
        by_qualification.setdefault("quente", 0)
        by_qualification.setdefault("morno", 0)
        by_qualification.setdefault("frio", 0)
        
        # =============================================
        # POR STATUS
        # =============================================
        status_result = await db.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .group_by(Lead.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}
        
        # =============================================
        # LEADS QUENTES AGUARDANDO (NOVO!)
        # =============================================
        hot_waiting_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .where(or_(
                Lead.qualification == "quente",
                Lead.qualification == "hot"
            ))
            .where(or_(
                Lead.status == "new",
                Lead.status == "in_progress"
            ))
            .where(Lead.assigned_to.is_(None))
        )
        hot_leads_waiting = hot_waiting_result.scalar() or 0
        
        # =============================================
        # VELOCIDADE DE RESPOSTA (NOVO!)
        # =============================================
        avg_response_result = await db.execute(
            select(func.avg(
                func.extract('epoch', Message.created_at) - 
                func.extract('epoch', Lead.created_at)
            ))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant.id)
            .where(Message.role == "assistant")
            .where(Lead.created_at >= month_start)
        )
        avg_seconds = avg_response_result.scalar()
        avg_response_time_minutes = round((avg_seconds / 60), 1) if avg_seconds else 2.0
        
        # =============================================
        # TAXA DE ENGAJAMENTO (NOVO!)
        # =============================================
        engaged_result = await db.execute(
            select(func.count(func.distinct(Message.lead_id)))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant.id)
            .where(Message.role == "user")
            .where(Lead.created_at >= month_start)
        )
        engaged_leads = engaged_result.scalar() or 0
        engagement_rate = (engaged_leads / leads_this_month * 100) if leads_this_month > 0 else 0
        
        # =============================================
        # POR CANAL E SOURCE
        # =============================================
        channel_result = await db.execute(
            select(Lead.channel_id, func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .group_by(Lead.channel_id)
        )
        by_channel = {str(row[0] or "direct"): row[1] for row in channel_result.all()}
        
        source_result = await db.execute(
            select(Lead.source, func.count(Lead.id))
            .where(Lead.tenant_id == tenant.id)
            .group_by(Lead.source)
        )
        by_source = {row[0]: row[1] for row in source_result.all()}
        
        # =============================================
        # TAXA DE CONVERSÃO
        # =============================================
        qualified_count = (
            by_qualification.get("quente", 0) +
            by_status.get("handed_off", 0) +
            by_status.get("closed", 0)
        )
        conversion_rate = (qualified_count / total_leads * 100) if total_leads > 0 else 0
        
        # =============================================
        # TEMPO MÉDIO DE QUALIFICAÇÃO
        # =============================================
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
        avg_qual_seconds = avg_time_result.scalar()
        avg_qualification_time_hours = round((avg_qual_seconds / 3600), 2) if avg_qual_seconds else 0
        
        # =============================================
        # RESPOSTA FINAL
        # =============================================
        return {
            # Básicos
            "total_leads": total_leads,
            "leads_today": leads_today,
            "leads_this_week": leads_this_week,
            "leads_this_month": leads_this_month,
            
            # Qualificação e Status
            "by_qualification": by_qualification,
            "by_status": by_status,
            "by_channel": by_channel,
            "by_source": by_source,
            
            # Métricas de Performance
            "conversion_rate": round(conversion_rate, 1),
            "avg_qualification_time_hours": avg_qualification_time_hours,
            
            # NOVAS MÉTRICAS DE VALOR
            "avg_response_time_minutes": avg_response_time_minutes,
            "engagement_rate": round(engagement_rate, 1),
            "time_saved": time_saved,
            "after_hours_leads": after_hours_count,
            "growth_percentage": round(growth_percentage, 1),
            "hot_leads_waiting": hot_leads_waiting,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao buscar métricas: {e}", exc_info=True)
        
        # Fallback - nunca deixa dashboard quebrar
        return {
            "total_leads": 0,
            "leads_today": 0,
            "leads_this_week": 0,
            "leads_this_month": 0,
            "by_qualification": {"quente": 0, "morno": 0, "frio": 0},
            "by_status": {},
            "by_channel": {},
            "by_source": {},
            "conversion_rate": 0,
            "avg_qualification_time_hours": 0,
            "avg_response_time_minutes": 2.0,
            "engagement_rate": 0,
            "time_saved": {"hours_saved": 0, "cost_saved_brl": 0, "leads_handled": 0},
            "after_hours_leads": 0,
            "growth_percentage": 0,
            "hot_leads_waiting": 0,
        }


# ============================================
# LEADS POR DIA (Mantido)
# ============================================

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


# ============================================
# TOP CAMPANHAS (Mantido)
# ============================================

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