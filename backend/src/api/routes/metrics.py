"""
ROTAS: MÉTRICAS V2.0
====================

Endpoints para métricas do dashboard.
Dados consolidados para análise do gestor.

CORREÇÕES V2.0:
✅ Autenticação via token (não mais tenant_slug)
✅ Cálculo correto de tempo economizado
✅ Horário comercial realista (8h-22h)
✅ Engagement rate correto (2+ mensagens)
✅ Crescimento pode ser negativo
✅ Campo assigned_seller_id (não assigned_to)
✅ Endpoint correto (/dashboard/metrics)
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, case, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Tenant, LeadEvent, Message, User
from src.domain.entities.enums import LeadStatus
from src.api.dependencies import get_current_user
from src.api.schemas import DashboardMetrics, LeadsByPeriod
import re
from collections import Counter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])  # ✅ CORRIGIDO!


# ============================================
# HELPERS - FUNÇÕES AUXILIARES
# ============================================

def is_after_hours(dt: datetime) -> bool:
    """
    Verifica se está fora do horário comercial.
    
    ✅ CORRIGIDO: Agora usa 8h-22h (mais realista)
    """
    hour = dt.hour
    weekday = dt.weekday()
    return hour < 8 or hour >= 22 or weekday >= 5  # ✅ 22h ao invés de 18h


def calculate_time_saved(total_leads: int) -> dict:
    """
    ✅ CORRIGIDO: Calcula tempo/dinheiro economizado pela IA.
    
    Premissa:
    - Atendente humano: 10 minutos por lead
    - IA Velaris: 2 minutos por lead
    - Economia: 8 minutos por lead
    - Custo atendente: R$ 20/hora
    """
    minutes_saved_per_lead = 10 - 2  # 8 minutos economizados
    total_minutes_saved = total_leads * minutes_saved_per_lead
    hours_saved = total_minutes_saved / 60
    cost_saved = hours_saved * 20  # ✅ R$ 20/hora (mais realista)
    
    return {
        "hours_saved": round(hours_saved, 1),
        "cost_saved_brl": round(cost_saved, 2),
        "leads_handled": total_leads,
    }


def get_date_ranges():
    """Retorna ranges de datas para filtros."""
    now = datetime.now(timezone.utc)
    
    # Início do dia (00:00)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Início da semana (segunda-feira)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    # Início do mês
    month_start = today_start.replace(day=1)
    
    # Semana anterior (para calcular growth)
    last_week_start = week_start - timedelta(days=7)
    
    # Mês anterior (para calcular growth)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    return {
        "now": now,
        "today_start": today_start,
        "week_start": week_start,
        "month_start": month_start,
        "last_week_start": last_week_start,
        "last_month_start": last_month_start,
    }

def extract_topics(messages: list[str]) -> list[dict]:
    """Extrai tópicos frequentes das mensagens (simples heatmap)."""
    # Lista de stopwords simples
    stopwords = {'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma', 'os', 'as', 'no', 'na', 'por', 'mais', 'como', 'me', 'meu', 'minha', 'tem', 'quero', 'sou', 'vcs', 'vocês', 'boa', 'tarde', 'dia', 'noite', 'ola', 'olá', 'oi'}
    
    words = []
    for msg in messages:
        # Limpar e tokenizar
        clean_msg = re.sub(r'[^\w\s]', '', msg.lower())
        for word in clean_msg.split():
            if len(word) > 3 and word not in stopwords:
                words.append(word)
    
    most_common = Counter(words).most_common(10)
    return [{"topic": word, "count": count} for word, count in most_common]


# ============================================
# ENDPOINT PRINCIPAL
# ============================================

@router.get("/metrics")  # ✅ /api/dashboard/metrics
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),  # ✅ AUTENTICAÇÃO!
    db: AsyncSession = Depends(get_db),
):
    """
    📊 Retorna métricas consolidadas do dashboard.
    
    ✅ MELHORADO COM:
    - Autenticação via token
    - Cálculos corretos
    - Todos os campos que o frontend espera
    """
    
    try:
        from src.domain.entities import Seller
        from src.domain.entities.enums import UserRole

        tenant_id = current_user.tenant_id  # ✅ Pega do token!

        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # ✅ Busca tenant para validar
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # 🆕 FILTRO POR SELLER - Se usuário for corretor, mostrar apenas seus leads
        seller_filter = None
        if current_user.role == UserRole.SELLER:
            # Busca seller vinculado ao usuário
            seller_result = await db.execute(
                select(Seller).where(
                    Seller.user_id == current_user.id,
                    Seller.tenant_id == tenant_id
                )
            )
            seller = seller_result.scalar_one_or_none()
            if seller:
                seller_filter = seller.id  # Filtra por seller_id

        # Períodos de tempo
        dates = get_date_ranges()

        # =============================================
        # TOTAIS BÁSICOS (COM FILTRO DE SELLER)
        # =============================================

        # Query base com filtro opcional de seller
        base_query_filters = [Lead.tenant_id == tenant_id]
        if seller_filter:
            base_query_filters.append(Lead.assigned_seller_id == seller_filter)

        total_result = await db.execute(
            select(func.count(Lead.id)).where(and_(*base_query_filters))
        )
        total_leads = total_result.scalar() or 0
        
        today_result = await db.execute(
            select(func.count(Lead.id))
            .where(and_(*base_query_filters))
            .where(Lead.created_at >= dates["today_start"])
        )
        leads_today = today_result.scalar() or 0

        week_result = await db.execute(
            select(func.count(Lead.id))
            .where(and_(*base_query_filters))
            .where(Lead.created_at >= dates["week_start"])
        )
        leads_this_week = week_result.scalar() or 0

        month_result = await db.execute(
            select(func.count(Lead.id))
            .where(and_(*base_query_filters))
            .where(Lead.created_at >= dates["month_start"])
        )
        leads_this_month = month_result.scalar() or 0
        
        # =============================================
        # ECONOMIA DE TEMPO/DINHEIRO (✅ CORRIGIDO!)
        # =============================================
        time_saved = calculate_time_saved(leads_this_month)
        
        # =============================================
        # LEADS FORA DO HORÁRIO (✅ OTIMIZADO!)
        # =============================================
        all_leads_month = await db.execute(
            select(Lead.created_at)
            .where(and_(*base_query_filters))
            .where(Lead.created_at >= dates["month_start"])
        )
        
        after_hours_count = 0
        for row in all_leads_month:
            if row.created_at and is_after_hours(row.created_at):
                after_hours_count += 1
        
        # =============================================
        # CRESCIMENTO VS SEMANA/MÊS ANTERIOR (✅ CORRIGIDO!)
        # =============================================
        last_week_result = await db.execute(
            select(func.count(Lead.id))
            .where(and_(*base_query_filters))
            .where(Lead.created_at >= dates["last_week_start"])
            .where(Lead.created_at < dates["week_start"])
        )
        leads_last_week = last_week_result.scalar() or 0
        
        # ✅ PODE SER NEGATIVO AGORA!
        if leads_last_week > 0:
            growth_percentage = ((leads_this_week - leads_last_week) / leads_last_week) * 100
        else:
            growth_percentage = 100 if leads_this_week > 0 else 0
        
        # =============================================
        # POR QUALIFICAÇÃO
        # =============================================
        qual_result = await db.execute(
            select(Lead.qualification, func.count(Lead.id))
            .where(and_(*base_query_filters))
            .where(Lead.qualification.isnot(None))
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
            .where(and_(*base_query_filters))
            .group_by(Lead.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # =============================================
        # LEADS QUENTES AGUARDANDO (✅ CORRIGIDO + FILTRO SELLER!)
        # =============================================
        hot_waiting_filters = list(base_query_filters)  # Copia os filtros base
        hot_waiting_filters.extend([
            or_(
                Lead.qualification == "quente",
                Lead.qualification == "hot"
            ),
            Lead.status != LeadStatus.HANDED_OFF.value,
            Lead.assigned_seller_id.is_(None) if not seller_filter else True == True  # Se é seller, ignora esse filtro
        ])
        hot_waiting_result = await db.execute(
            select(func.count(Lead.id)).where(and_(*hot_waiting_filters))
        )
        hot_leads_waiting = hot_waiting_result.scalar() or 0
        
        # =============================================
        # VELOCIDADE DE RESPOSTA
        # =============================================
        avg_response_result = await db.execute(
            select(func.avg(
                func.extract('epoch', Message.created_at) - 
                func.extract('epoch', Lead.created_at)
            ))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant_id)
            .where(Message.role == "assistant")
            .where(Lead.created_at >= dates["month_start"])
        )
        avg_seconds = avg_response_result.scalar()
        avg_response_time_minutes = round((avg_seconds / 60), 1) if avg_seconds else 2.0
        
        # =============================================
        # TAXA DE ENGAJAMENTO (✅ CORRIGIDO!)
        # =============================================
        # Leads com 2+ mensagens (conversa real)
        engaged_result = await db.execute(
            select(Lead.id)
            .join(Message, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant_id)
            .where(Message.role == "user")
            .where(Lead.created_at >= dates["month_start"])
            .group_by(Lead.id)
            .having(func.count(Message.id) >= 2)  # ✅ CORRIGIDO!
        )
        engaged_leads = len(engaged_result.all())
        engagement_rate = (engaged_leads / leads_this_month * 100) if leads_this_month > 0 else 0
        
        # =============================================
        # POR CANAL E SOURCE
        # =============================================
        channel_result = await db.execute(
            select(Lead.channel_id, func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.channel_id)
        )
        by_channel = {str(row[0] or "direct"): row[1] for row in channel_result.all()}
        
        source_result = await db.execute(
            select(Lead.source, func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.source)
        )
        by_source = {row[0] or "organico": row[1] for row in source_result.all()}
        
        # =============================================
        # TAXA DE CONVERSÃO
        # =============================================
        converted_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.status == LeadStatus.HANDED_OFF.value)
        )
        converted_leads = converted_result.scalar() or 0
        
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        # =============================================
        # TEMPO MÉDIO DE QUALIFICAÇÃO
        # =============================================
        avg_time_result = await db.execute(
            select(func.avg(
                func.extract('epoch', Lead.updated_at) - 
                func.extract('epoch', Lead.created_at)
            ))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.qualification.isnot(None))
        )
        avg_qual_seconds = avg_time_result.scalar()
        avg_qualification_time_hours = round((avg_qual_seconds / 3600), 2) if avg_qual_seconds else 1.0

        # =============================================
        # FUNIL DE CONVERSÃO (NOVO)
        # =============================================
        # Estágios do Funil:
        # 1. Total (leads_this_month)
        # 2. Engajados (engaged_leads)
        # 3. Qualificados (leads_hot_month)
        # 4. Convertidos/Handoff (converted_month)

        leads_hot_month_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.created_at >= dates["month_start"])
            .where(or_(Lead.qualification == "quente", Lead.qualification == "hot"))
        )
        leads_hot_month = leads_hot_month_result.scalar() or 0

        converted_month_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.created_at >= dates["month_start"])
            .where(Lead.status == LeadStatus.HANDED_OFF.value)
        )
        converted_month = converted_month_result.scalar() or 0

        funnel_data = {
            "total": leads_this_month,
            "engaged": engaged_leads,
            "qualified": leads_hot_month,
            "converted": converted_month
        }

        # =============================================
        # EXTRAÇÃO DE TÓPICOS (HEATMAP)
        # =============================================
        recent_msgs_result = await db.execute(
            select(Message.content)
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant_id)
            .where(Message.role == "user")
            .where(Lead.created_at >= dates["month_start"])
            .limit(200)
        )
        recent_msgs = [row[0] for row in recent_msgs_result.all()]
        top_topics = extract_topics(recent_msgs)
        
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
            
            # Métricas de Valor
            "avg_response_time_minutes": avg_response_time_minutes,
            "engagement_rate": round(engagement_rate, 1),
            "time_saved": time_saved,
            "after_hours_leads": after_hours_count,
            "growth_percentage": round(growth_percentage, 1),
            "hot_leads_waiting": hot_leads_waiting,
            "funnel": funnel_data,
            "top_topics": top_topics,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Erro ao buscar métricas: {e}", exc_info=True)
        
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
# LEADS POR DIA (Mantido - Útil para gráficos)
# ============================================

@router.get("/leads-by-day", response_model=list[LeadsByPeriod])
async def get_leads_by_day(
    current_user: User = Depends(get_current_user),  # ✅ CORRIGIDO!
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna leads agrupados por dia.
    Útil para gráficos de evolução.
    """
    tenant_id = current_user.tenant_id
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(
            func.date(Lead.created_at).label("day"),
            func.count(Lead.id).label("count"),
            func.sum(case((Lead.qualification == "quente", 1), else_=0)).label("hot"),
            func.sum(case((Lead.qualification == "morno", 1), else_=0)).label("warm"),
            func.sum(case((Lead.qualification == "frio", 1), else_=0)).label("cold"),
        )
        .where(Lead.tenant_id == tenant_id)
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
# TOP CAMPANHAS (Mantido - Útil para análise)
# ============================================

@router.get("/top-campaigns")
async def get_top_campaigns(
    current_user: User = Depends(get_current_user),  # ✅ CORRIGIDO!
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna campanhas com mais leads.
    """
    tenant_id = current_user.tenant_id
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant")
    
    result = await db.execute(
        select(Lead.campaign, func.count(Lead.id).label("count"))
        .where(Lead.tenant_id == tenant_id)
        .where(Lead.campaign.isnot(None))
        .group_by(Lead.campaign)
        .order_by(func.count(Lead.id).desc())
        .limit(limit)
    )
    
    return [
        {"campaign": row.campaign, "count": row.count}
        for row in result.all()
    ]