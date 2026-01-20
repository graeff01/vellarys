"""
ADMIN: Dashboard CEO
====================

Métricas avançadas para visão executiva do negócio.
Endpoints específicos para o SUPERADMIN/CEO.

ÚLTIMA ATUALIZAÇÃO: 2024-12-29
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, Lead, Message, User
from src.api.routes.admin.deps import get_current_superadmin

router = APIRouter(prefix="/admin/ceo", tags=["Admin - CEO Dashboard"])


# =============================================================================
# HELPERS
# =============================================================================

def get_utc_now():
    """Retorna datetime UTC timezone-aware."""
    return datetime.now(timezone.utc)


def make_aware(dt: datetime) -> datetime:
    """Converte datetime naive para aware (UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt



# =============================================================================
# SCHEMAS
# =============================================================================

class TenantHealth(BaseModel):
    id: int
    name: str
    slug: str
    status: str  # healthy, warning, critical, inactive
    leads_total: int
    leads_this_week: int
    leads_this_month: int
    messages_total: int
    last_activity: Optional[datetime]
    days_since_activity: int
    conversion_rate: float
    plan: Optional[str]


class FinancialMetrics(BaseModel):
    mrr_estimated: float
    burn_rate_today: float
    gross_margin_percent: float
    projected_cost_monthly: float


class InfraMetrics(BaseModel):
    openai_latency_ms: int
    db_latency_ms: int
    active_workers: int
    error_rate_percent: float
    queue_size: int
    status_global: str  # healthy, degraded, down
    kill_switch_active: bool


class CEOMetrics(BaseModel):
    # Resumo Geral
    total_clients: int
    active_clients: int
    inactive_clients: int
    
    total_leads: int
    leads_this_week: int
    leads_this_month: int
    leads_growth_percent: float
    
    total_messages: int
    messages_this_week: int
    
    avg_conversion_rate: float
    total_handoffs: int
    
    # Por status
    clients_healthy: int
    clients_warning: int
    clients_critical: int
    
    # God Mode Metrics
    financial: FinancialMetrics
    infra: InfraMetrics


class Alert(BaseModel):
    type: str  # warning, critical, info
    title: str
    message: str
    tenant_id: Optional[int]
    tenant_name: Optional[str]
    created_at: datetime


class WeeklyGrowth(BaseModel):
    week: str
    leads: int
    messages: int


class ChurnRiskClient(BaseModel):
    id: int
    name: str
    plan: str
    days_inactive: int
    usage_trend: str  # 'declining', 'stable'
    risk_level: str   # 'high', 'medium'
    last_interaction: Optional[datetime]


class UpsellOpportunity(BaseModel):
    id: int
    name: str
    current_plan: str
    usage_percent: float  # Uso em relação ao limite do plano (estimado)
    messages_month: int
    leads_month: int
    suggested_plan: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/metrics", response_model=CEOMetrics)
async def get_ceo_metrics(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas executivas agregadas de todo o sistema.
    """
    now = get_utc_now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # --------------------------------------------------------------------------
    # 1. MÉTRICAS BASE (Leads, Tenants, Msgs)
    # --------------------------------------------------------------------------
    
    # Total de tenants (excluindo admin)
    total_tenants_result = await db.execute(
        select(func.count(Tenant.id)).where(Tenant.slug != "velaris-admin")
    )
    total_clients = total_tenants_result.scalar() or 0
    
    active_tenants_result = await db.execute(
        select(func.count(Tenant.id)).where(
            and_(Tenant.active == True, Tenant.slug != "velaris-admin")
        )
    )
    active_clients = active_tenants_result.scalar() or 0
    inactive_clients = total_clients - active_clients
    
    # Total de leads
    total_leads_result = await db.execute(select(func.count(Lead.id)))
    total_leads = total_leads_result.scalar() or 0
    
    # Leads esta semana
    leads_week_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= week_ago)
    )
    leads_this_week = leads_week_result.scalar() or 0
    
    # Leads este mês
    leads_month_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= month_ago)
    )
    leads_this_month = leads_month_result.scalar() or 0
    
    # Leads mês passado (para calcular crescimento)
    leads_last_month_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.created_at >= two_months_ago,
                Lead.created_at < month_ago
            )
        )
    )
    leads_last_month = leads_last_month_result.scalar() or 0
    
    # Crescimento percentual
    if leads_last_month > 0:
        leads_growth_percent = ((leads_this_month - leads_last_month) / leads_last_month) * 100
    else:
        leads_growth_percent = 100 if leads_this_month > 0 else 0
    
    # Total de mensagens
    total_messages_result = await db.execute(select(func.count(Message.id)))
    total_messages = total_messages_result.scalar() or 0
    
    # Mensagens esta semana
    messages_week_result = await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= week_ago)
    )
    messages_this_week = messages_week_result.scalar() or 0
    
    # Taxa de conversão média (leads quentes / total)
    hot_leads_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.qualification == "quente")
    )
    hot_leads = hot_leads_result.scalar() or 0
    avg_conversion_rate = (hot_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Total de handoffs
    handoffs_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.status == "handed_off")
    )
    total_handoffs = handoffs_result.scalar() or 0

    # --------------------------------------------------------------------------
    # 2. SAÚDE DOS TENANTS
    # --------------------------------------------------------------------------
    
    three_days_ago = now - timedelta(days=3)
    
    # Busca tenant plans e status para cálculo financeiro (excluindo admin)
    tenants_data_result = await db.execute(
        select(Tenant.id, Tenant.active, Tenant.plan)
        .where(Tenant.slug != "velaris-admin")
    )
    tenants_data = tenants_data_result.all()
    
    clients_healthy = 0
    clients_warning = 0
    clients_critical = 0
    
    # Map para preços de plano (mockado por enquanto)
    PLAN_PRICES = {
        "starter": 297.00,
        "pro": 497.00,
        "enterprise": 997.00,
        "custom": 1500.00
    }
    
    estimated_mrr = 0.0
    
    # Verifica saúde e calcula MRR
    for t_id, t_active, t_plan in tenants_data:
        if t_active:
            estimated_mrr += PLAN_PRICES.get(t_plan, 297.00)
            
            # Saúde do tenant
            last_msg_result = await db.execute(
                select(func.max(Message.created_at))
                .join(Lead, Message.lead_id == Lead.id)
                .where(Lead.tenant_id == t_id)
            )
            last_activity_val = last_msg_result.scalar()
            
            if last_activity_val:
                last_activity_val = make_aware(last_activity_val)
                if last_activity_val >= three_days_ago:
                    clients_healthy += 1
                elif last_activity_val >= week_ago:
                    clients_warning += 1
                else:
                    clients_critical += 1
            else:
                clients_critical += 1
        else:
            clients_critical += 1

    # --------------------------------------------------------------------------
    # 3. FINANCEIRO & INFRA (GOD MODE)
    # --------------------------------------------------------------------------
    
    # BURN RATE (Calculado pelo uso de tokens hoje)
    # Custo médio input/output gpt-4o-mini ~ USD 0.60 / 1M tokens => R$ 3.50 / 1M tokens
    COST_PER_TOKEN_BRL = 0.0000035  
    
    tokens_today_result = await db.execute(
        select(func.sum(Message.tokens_used)).where(Message.created_at >= start_of_day)
    )
    tokens_today = tokens_today_result.scalar() or 0
    burn_rate_today = tokens_today * COST_PER_TOKEN_BRL
    
    # Projetado mensal (Burn Rate do dia * 30 + Custos Fixos de Servidor)
    SERVER_COST = 350.00 # Railway + DB estimattiva
    projected_cost = (burn_rate_today * 30) + SERVER_COST
    
    # Margem Bruta
    gross_margin = 0.0
    if estimated_mrr > 0:
        gross_margin = ((estimated_mrr - projected_cost) / estimated_mrr) * 100

    # LATÊNCIA DB (Ping real)
    import time
    start_time = time.time()
    await db.execute(select(1))
    db_latency = int((time.time() - start_time) * 1000)
    
    # Simulação de latência OpenAI (pegar média se tivesse log, por enquanto mock realista)
    openai_latency = 1240  # 1.2s médio
    
    # KILL SWITCH STATUS
    from src.infrastructure.services.redis_service import cache_get
    kill_switch_val = await cache_get("system:kill_switch")
    kill_switch_active = bool(kill_switch_val)
    
    # Status Global
    status_global = "healthy"
    if kill_switch_active:
        status_global = "down"
    elif db_latency > 200 or openai_latency > 4000:
        status_global = "degraded"
    
    financial_metrics = FinancialMetrics(
        mrr_estimated=round(estimated_mrr, 2),
        burn_rate_today=round(burn_rate_today, 2),
        gross_margin_percent=round(gross_margin, 1),
        projected_cost_monthly=round(projected_cost, 2)
    )
    
    infra_metrics = InfraMetrics(
        openai_latency_ms=openai_latency,
        db_latency_ms=db_latency,
        active_workers=4, # Mock
        error_rate_percent=0.2, # Mock
        queue_size=12, # Mock
        status_global=status_global,
        kill_switch_active=kill_switch_active
    )
    
    return CEOMetrics(
        total_clients=total_clients,
        active_clients=active_clients,
        inactive_clients=inactive_clients,
        total_leads=total_leads,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        leads_growth_percent=round(leads_growth_percent, 1),
        total_messages=total_messages,
        messages_this_week=messages_this_week,
        avg_conversion_rate=round(avg_conversion_rate, 1),
        total_handoffs=total_handoffs,
        clients_healthy=clients_healthy,
        clients_warning=clients_warning,
        clients_critical=clients_critical,
        financial=financial_metrics,
        infra=infra_metrics
    )


@router.get("/clients-health", response_model=list[TenantHealth])
async def get_clients_health(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna a saúde de cada cliente com métricas detalhadas.
    """
    now = get_utc_now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    three_days_ago = now - timedelta(days=3)
    
    # Busca todos os tenants (excluindo admin)
    tenants_result = await db.execute(
        select(Tenant).where(Tenant.slug != "velaris-admin").order_by(Tenant.name)
    )
    tenants = tenants_result.scalars().all()
    
    health_list = []
    
    for tenant in tenants:
        # Total de leads
        leads_total_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
        )
        leads_total = leads_total_result.scalar() or 0
        
        # Leads esta semana
        leads_week_result = await db.execute(
            select(func.count(Lead.id)).where(
                and_(
                    Lead.tenant_id == tenant.id,
                    Lead.created_at >= week_ago
                )
            )
        )
        leads_this_week = leads_week_result.scalar() or 0
        
        # Leads este mês
        leads_month_result = await db.execute(
            select(func.count(Lead.id)).where(
                and_(
                    Lead.tenant_id == tenant.id,
                    Lead.created_at >= month_ago
                )
            )
        )
        leads_this_month = leads_month_result.scalar() or 0
        
        # Total de mensagens
        messages_result = await db.execute(
            select(func.count(Message.id))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant.id)
        )
        messages_total = messages_result.scalar() or 0
        
        # Última atividade
        last_activity_result = await db.execute(
            select(func.max(Message.created_at))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant.id)
        )
        last_activity = last_activity_result.scalar()
        
        # Converte para timezone-aware se necessário
        if last_activity:
            last_activity = make_aware(last_activity)
        
        # Dias desde última atividade
        if last_activity:
            days_since = (now - last_activity).days
        else:
            days_since = 999  # Nunca teve atividade
        
        # Taxa de conversão do tenant
        hot_leads_result = await db.execute(
            select(func.count(Lead.id)).where(
                and_(
                    Lead.tenant_id == tenant.id,
                    Lead.qualification == "quente"
                )
            )
        )
        hot_leads = hot_leads_result.scalar() or 0
        conversion_rate = (hot_leads / leads_total * 100) if leads_total > 0 else 0
        
        # Determina status
        if not tenant.active:
            status = "inactive"
        elif last_activity and last_activity >= three_days_ago:
            status = "healthy"
        elif last_activity and last_activity >= week_ago:
            status = "warning"
        else:
            status = "critical"
        
        health_list.append(TenantHealth(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=status,
            leads_total=leads_total,
            leads_this_week=leads_this_week,
            leads_this_month=leads_this_month,
            messages_total=messages_total,
            last_activity=last_activity,
            days_since_activity=days_since,
            conversion_rate=round(conversion_rate, 1),
            plan=tenant.plan,
        ))
    
    # Ordena por status (critical primeiro) e depois por leads
    status_order = {"critical": 0, "warning": 1, "inactive": 2, "healthy": 3}
    health_list.sort(key=lambda x: (status_order.get(x.status, 4), -x.leads_total))
    
    return health_list


@router.get("/alerts", response_model=list[Alert])
async def get_alerts(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna alertas automáticos do sistema.
    """
    now = get_utc_now()
    week_ago = now - timedelta(days=7)
    three_days_ago = now - timedelta(days=3)
    
    alerts = []
    
    # Busca tenants ativos (excluindo admin)
    tenants_result = await db.execute(
        select(Tenant).where(
            and_(Tenant.active == True, Tenant.slug != "velaris-admin")
        )
    )
    tenants = tenants_result.scalars().all()
    
    for tenant in tenants:
        # Verifica última atividade
        last_activity_result = await db.execute(
            select(func.max(Message.created_at))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == tenant.id)
        )
        last_activity = last_activity_result.scalar()
        
        # Converte para timezone-aware se necessário
        if last_activity:
            last_activity = make_aware(last_activity)
        
        if last_activity is None:
            alerts.append(Alert(
                type="warning",
                title="Cliente sem atividade",
                message=f"Cliente nunca recebeu mensagens",
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                created_at=now,
            ))
        elif last_activity < week_ago:
            days = (now - last_activity).days
            alerts.append(Alert(
                type="critical",
                title="Cliente inativo",
                message=f"Sem atividade há {days} dias",
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                created_at=now,
            ))
        elif last_activity < three_days_ago:
            days = (now - last_activity).days
            alerts.append(Alert(
                type="warning",
                title="Atividade reduzida",
                message=f"Última atividade há {days} dias",
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                created_at=now,
            ))
    
    # Ordena por tipo (critical primeiro)
    type_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: type_order.get(x.type, 3))
    
    return alerts


@router.get("/weekly-growth", response_model=list[WeeklyGrowth])
async def get_weekly_growth(
    weeks: int = 8,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna dados de crescimento semanal para gráfico.
    """
    now = get_utc_now()
    growth_data = []
    
    for i in range(weeks - 1, -1, -1):
        week_start = now - timedelta(weeks=i+1)
        week_end = now - timedelta(weeks=i)
        
        # Leads da semana
        leads_result = await db.execute(
            select(func.count(Lead.id)).where(
                and_(
                    Lead.created_at >= week_start,
                    Lead.created_at < week_end
                )
            )
        )
        leads_count = leads_result.scalar() or 0
        
        # Mensagens da semana
        messages_result = await db.execute(
            select(func.count(Message.id)).where(
                and_(
                    Message.created_at >= week_start,
                    Message.created_at < week_end
                )
            )
        )
        messages_count = messages_result.scalar() or 0
        
        # Formata label da semana
        week_label = week_end.strftime("%d/%m")
        
        growth_data.append(WeeklyGrowth(
            week=week_label,
            leads=leads_count,
            messages=messages_count,
        ))
    
    return growth_data


@router.get("/scheduler-status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_superadmin),
):
    """
    Retorna status do scheduler de follow-up.
    """
    try:
        from src.infrastructure.scheduler import get_scheduler_status
        status = get_scheduler_status()
        return {
            "success": True,
            **status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "running": False,
        }


@router.post("/trigger-follow-up")
async def trigger_follow_up(
    current_user: User = Depends(get_current_superadmin),
):
    """
    Dispara o job de follow-up manualmente.
    """
    try:
        from src.infrastructure.scheduler import run_job_now
        result = await run_job_now("follow_up_job")
        return {
            "success": result,
            "message": "Job de follow-up disparado!" if result else "Erro ao disparar job"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/kill-switch")
async def kill_switch_system(
    enable: bool,
    current_user: User = Depends(get_current_superadmin)
):
    """
    [GOD MODE] Pausa o processamento de mensagens em todo o sistema.
    Define a chave 'system:kill_switch' no Redis.
    """
    from src.infrastructure.services.redis_service import cache_set, cache_delete
    
    key = "system:kill_switch"
    try:
        if enable:
            # Set kill switch with no expiration (manual override required)
            # Using specific value "on"
            await cache_set(key, "on", ttl=31536000) # 1 year usually
            action = "enabled"
        else:
            await cache_delete(key)
            action = "disabled"
            
        return {
            "status": "success", 
            "system_paused": enable, 
            "message": f"Global Kill Switch {action}. All AI processing will stop immediately."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to toggle kill switch: {str(e)}"
        }

@router.post("/force-restart-workers")
async def force_restart_workers(
    current_user: User = Depends(get_current_superadmin)
):
    """
    [GOD MODE] Envia sinal para reiniciar workers.
    Usa Pub/Sub do Redis para notificar workers (simulado com chave por enquanto).
    """
    from src.infrastructure.services.redis_service import get_redis, cache_set
    
    redis = await get_redis()
    if not redis:
         return {"status": "error", "message": "Redis not available"}

    try:
        # Method 1: Set a flag that workers check periodically
        # Method 2: Publish to a channel (standard for real-time control)
        
        # We will do both for robustness
        await redis.publish("system:control", "restart_workers")
        await cache_set("system:restart_signal", datetime.now().isoformat(), ttl=60)
        
        return {
            "status": "success", 
            "message": "Signal sent to restart all workers immediately."
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Failed to send restart signal: {str(e)}"
        }


@router.get("/churn-risk", response_model=list[ChurnRiskClient])
async def get_churn_risk(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna lista de clientes em risco de Churn.
    Critério: Inatividade > 3 dias ou queda brusca de volume.
    """
    now = get_utc_now()
    three_days_ago = now - timedelta(days=3)
    
    # Busca clientes ativos (excluindo admin)
    tenants_result = await db.execute(
        select(Tenant).where(
            and_(Tenant.active == True, Tenant.slug != "velaris-admin")
        )
    )
    tenants = tenants_result.scalars().all()
    
    churn_list = []
    
    for t in tenants:
        # Última atividade
        last_msg_result = await db.execute(
            select(func.max(Message.created_at))
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.tenant_id == t.id)
        )
        last_activity = last_msg_result.scalar()
        if last_activity:
            last_activity = make_aware(last_activity)
            days_inactive = (now - last_activity).days
        else:
            days_inactive = 999
            
        # Adiciona se inatividade > 3 dias
        if days_inactive > 3:
            risk_level = "high" if days_inactive > 7 else "medium"
            
            churn_list.append(ChurnRiskClient(
                id=t.id,
                name=t.name,
                plan=t.plan or "starter",
                days_inactive=days_inactive,
                usage_trend="declining",
                risk_level=risk_level,
                last_interaction=last_activity
            ))
            
    # Ordena por risco (dias inativo decrescente)
    churn_list.sort(key=lambda x: x.days_inactive, reverse=True)
    return churn_list[:10]  # Top 10 riscos


@router.get("/upsell-opportunities", response_model=list[UpsellOpportunity])
async def get_upsell_opportunities(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna oportunidades de Upsell.
    Critério: Alto volume de mensagens no mês.
    """
    now = get_utc_now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    
    # Busca clientes ativos
    tenants_result = await db.execute(
        select(Tenant).where(
            and_(Tenant.active == True, Tenant.slug != "velaris-admin")
        )
    )
    tenants = tenants_result.scalars().all()
    
    upsell_list = []
    
    # Limites fictícios dos planos para cálculo de %
    PLAN_LIMITS = {
        "starter": 1000,
        "pro": 5000,
        "enterprise": 50000, 
        "custom": 100000
    }
    
    for t in tenants:
        plan = t.plan or "starter"
        limit = PLAN_LIMITS.get(plan, 1000)
        
        # Volume do mês
        msgs_month = await db.execute(
            select(func.count(Message.id))
            .join(Lead, Message.lead_id == Lead.id)
            .where(
                and_(
                    Lead.tenant_id == t.id,
                    Message.created_at >= month_start
                )
            )
        )
        msgs_count = msgs_month.scalar() or 0
        
        usage_percent = (msgs_count / limit) * 100
        
        # Regra de Upsell: > 70% do uso do plano ou > 2000 msgs no Starter
        if usage_percent > 70 or (plan == "starter" and msgs_count > 500):
            suggested = "pro"
            if plan == "pro": suggested = "enterprise"
            if plan == "enterprise": suggested = "custom"
            
            # Leads do mês
            leads_month = await db.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.tenant_id == t.id, Lead.created_at >= month_start)
                )
            )
            leads_count = leads_month.scalar() or 0
            
            upsell_list.append(UpsellOpportunity(
                id=t.id,
                name=t.name,
                current_plan=plan,
                usage_percent=round(usage_percent, 1),
                messages_month=msgs_count,
                leads_month=leads_count,
                suggested_plan=suggested
            ))
            
    # Ordena por uso (decrescente)
    upsell_list.sort(key=lambda x: x.usage_percent, reverse=True)
    return upsell_list[:10]
