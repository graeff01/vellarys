"""
ROTAS: SALES & GOALS
=====================

Endpoints para metas de vendas e métricas comerciais.

Endpoints:
- GET /sales/goals - Busca meta do mês atual
- POST /sales/goals - Define/atualiza meta
- GET /sales/metrics - Métricas de vendas detalhadas
- PUT /sales/deal - Registra uma venda
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import User, Lead, Seller
from src.domain.entities.enums import LeadStatus
from src.domain.entities.dashboard_config import SalesGoal
from src.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["Sales"])


# =============================================
# SCHEMAS
# =============================================

class SalesGoalInput(BaseModel):
    """Input para definir meta de vendas."""
    revenue_goal: Optional[int] = Field(None, description="Meta de receita em centavos")
    deals_goal: Optional[int] = Field(None, description="Meta de número de vendas")
    leads_goal: Optional[int] = Field(None, description="Meta de leads a captar")
    period: Optional[str] = Field(None, description="Período YYYY-MM (default: mês atual)")


class SalesGoalResponse(BaseModel):
    """Resposta da meta de vendas."""
    id: Optional[int] = None
    period: str
    revenue_goal: Optional[int] = None
    revenue_actual: int = 0
    revenue_progress: float = 0
    deals_goal: Optional[int] = None
    deals_actual: int = 0
    deals_progress: float = 0
    leads_goal: Optional[int] = None
    leads_actual: int = 0
    leads_progress: float = 0
    days_remaining: int = 0
    days_passed: int = 0
    total_days: int = 30


class DealInput(BaseModel):
    """Input para registrar uma venda."""
    lead_id: int
    revenue: int = Field(..., description="Valor da venda em centavos")
    notes: Optional[str] = None


class SellerRankingItem(BaseModel):
    """Item do ranking de vendedores."""
    seller_id: int
    seller_name: str
    deals_count: int
    conversion_rate: float
    leads_assigned: int


class SalesMetricsResponse(BaseModel):
    """Resposta completa de métricas de vendas."""
    # Métricas do mês
    total_deals: int = 0
    total_revenue: int = 0  # em centavos
    average_ticket: int = 0  # em centavos
    conversion_rate: float = 0

    # Meta e progresso
    goal: Optional[SalesGoalResponse] = None

    # Projeção
    projected_deals: int = 0
    projected_revenue: int = 0
    on_track: bool = True

    # Ranking
    seller_ranking: List[SellerRankingItem] = []

    # Temporal
    days_remaining: int = 0
    deals_today: int = 0
    deals_this_week: int = 0

    # Revenue Attribution (ROI)
    revenue_by_source: dict[str, int] = {}

    # Pulse (Latest Activities)
    pulse: List[dict] = []


# =============================================
# HELPERS
# =============================================

def get_current_period() -> str:
    """Retorna período atual no formato YYYY-MM."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_period_dates(period: str):
    """Retorna datas de início e fim do período."""
    year, month = map(int, period.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)

    _, last_day = monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    return start, end


def calculate_days_info(period: str):
    """Calcula informações de dias do período."""
    start, end = get_period_dates(period)
    now = datetime.now(timezone.utc)

    total_days = (end - start).days + 1
    days_passed = max(0, min((now - start).days + 1, total_days))
    days_remaining = max(0, total_days - days_passed)

    return total_days, days_passed, days_remaining


# =============================================
# ENDPOINTS
# =============================================

@router.get("/goals", response_model=SalesGoalResponse)
async def get_sales_goal(
    period: Optional[str] = Query(None, description="Período YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca meta de vendas do período.

    Se não especificado, usa o mês atual.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        target_period = period or get_current_period()
        total_days, days_passed, days_remaining = calculate_days_info(target_period)
        start_date, end_date = get_period_dates(target_period)

        # Busca meta
        result = await db.execute(
            select(SalesGoal)
            .where(
                and_(
                    SalesGoal.tenant_id == tenant_id,
                    SalesGoal.period == target_period
                )
            )
            .limit(1)
        )
        goal = result.scalar_one_or_none()

        # Conta leads do período
        leads_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.created_at >= start_date)
            .where(Lead.created_at <= end_date)
        )
        leads_actual = leads_result.scalar() or 0

        if goal:
            # Calcula progressos
            revenue_progress = 0
            if goal.revenue_goal and goal.revenue_goal > 0:
                revenue_progress = min((goal.revenue_actual / goal.revenue_goal) * 100, 100)

            deals_progress = 0
            if goal.deals_goal and goal.deals_goal > 0:
                deals_progress = min((goal.deals_actual / goal.deals_goal) * 100, 100)

            leads_progress = 0
            if goal.leads_goal and goal.leads_goal > 0:
                leads_progress = min((leads_actual / goal.leads_goal) * 100, 100)

            return SalesGoalResponse(
                id=goal.id,
                period=target_period,
                revenue_goal=goal.revenue_goal,
                revenue_actual=goal.revenue_actual,
                revenue_progress=round(revenue_progress, 1),
                deals_goal=goal.deals_goal,
                deals_actual=goal.deals_actual,
                deals_progress=round(deals_progress, 1),
                leads_goal=goal.leads_goal,
                leads_actual=leads_actual,
                leads_progress=round(leads_progress, 1),
                days_remaining=days_remaining,
                days_passed=days_passed,
                total_days=total_days,
            )

        # Sem meta definida
        return SalesGoalResponse(
            period=target_period,
            leads_actual=leads_actual,
            days_remaining=days_remaining,
            days_passed=days_passed,
            total_days=total_days,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro buscando meta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar meta")


@router.post("/goals", response_model=SalesGoalResponse)
async def set_sales_goal(
    goal_input: SalesGoalInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Define ou atualiza meta de vendas.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        target_period = goal_input.period or get_current_period()

        # Busca meta existente
        result = await db.execute(
            select(SalesGoal)
            .where(
                and_(
                    SalesGoal.tenant_id == tenant_id,
                    SalesGoal.period == target_period
                )
            )
            .limit(1)
        )
        goal = result.scalar_one_or_none()

        if goal:
            # Atualiza
            if goal_input.revenue_goal is not None:
                goal.revenue_goal = goal_input.revenue_goal
            if goal_input.deals_goal is not None:
                goal.deals_goal = goal_input.deals_goal
            if goal_input.leads_goal is not None:
                goal.leads_goal = goal_input.leads_goal
        else:
            # Cria nova
            goal = SalesGoal(
                tenant_id=tenant_id,
                period=target_period,
                revenue_goal=goal_input.revenue_goal,
                deals_goal=goal_input.deals_goal,
                leads_goal=goal_input.leads_goal,
            )
            db.add(goal)

        await db.commit()
        await db.refresh(goal)

        logger.info(f"✅ Meta definida: {target_period} (tenant={tenant_id})")

        # Retorna via get para calcular tudo
        return await get_sales_goal(target_period, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro definindo meta: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao definir meta")


@router.put("/deal")
async def register_deal(
    deal: DealInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra uma venda (incrementa contadores da meta).
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        # Verifica se lead existe
        lead_result = await db.execute(
            select(Lead)
            .where(Lead.id == deal.lead_id)
            .where(Lead.tenant_id == tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Atualiza status do lead
        lead.status = LeadStatus.CONVERTED.value
        
        # Atribuição automática se o lead estiver "sem dono"
        if not lead.assigned_seller_id and current_user.seller_id:
            lead.assigned_seller_id = current_user.seller_id
            lead.assigned_at = datetime.now(timezone.utc)
            lead.assignment_method = "direct_sale"
            logger.info(f"🤝 Lead {lead.id} atribuído automaticamente ao vendedor {current_user.seller_id} na venda")

        # Atualiza meta do mês atual
        current_period = get_current_period()
        result = await db.execute(
            select(SalesGoal)
            .where(
                and_(
                    SalesGoal.tenant_id == tenant_id,
                    SalesGoal.period == current_period
                )
            )
            .limit(1)
        )
        goal = result.scalar_one_or_none()

        if goal:
            goal.deals_actual += 1
            goal.revenue_actual += deal.revenue
        else:
            # Cria meta se não existe
            goal = SalesGoal(
                tenant_id=tenant_id,
                period=current_period,
                deals_actual=1,
                revenue_actual=deal.revenue,
            )
            db.add(goal)

        await db.commit()

        logger.info(f"💰 Venda registrada: R${deal.revenue/100:.2f} (lead={deal.lead_id})")

        return {"success": True, "message": "Venda registrada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro registrando venda: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar venda")


@router.get("/metrics", response_model=SalesMetricsResponse)
async def get_sales_metrics(
    period: Optional[str] = Query(None, description="Período YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas completas de vendas.

    Inclui projeções e ranking de vendedores.
    """
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant")

        target_period = period or get_current_period()
        start_date, end_date = get_period_dates(target_period)
        total_days, days_passed, days_remaining = calculate_days_info(target_period)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        # Busca meta
        goal_response = await get_sales_goal(target_period, current_user, db)

        # Conta leads convertidos no período
        converted_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.status == LeadStatus.CONVERTED.value)
            .where(Lead.updated_at >= start_date)
            .where(Lead.updated_at <= end_date)
        )
        total_deals = converted_result.scalar() or 0

        # Total de leads no período
        total_leads_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.created_at >= start_date)
            .where(Lead.created_at <= end_date)
        )
        total_leads = total_leads_result.scalar() or 0

        # Taxa de conversão
        conversion_rate = (total_deals / total_leads * 100) if total_leads > 0 else 0

        # Valores da meta
        total_revenue = goal_response.revenue_actual
        average_ticket = total_revenue // total_deals if total_deals > 0 else 0

        # Projeções baseadas na velocidade atual
        if days_passed > 0:
            daily_rate = total_deals / days_passed
            projected_deals = int(daily_rate * total_days)

            daily_revenue_rate = total_revenue / days_passed
            projected_revenue = int(daily_revenue_rate * total_days)
        else:
            projected_deals = 0
            projected_revenue = 0

        # Verifica se está no caminho certo
        on_track = True
        if goal_response.deals_goal and goal_response.deals_goal > 0:
            expected_progress = (days_passed / total_days) * 100
            on_track = goal_response.deals_progress >= (expected_progress * 0.8)  # 80% do esperado

        # Deals hoje
        deals_today_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.status == LeadStatus.CONVERTED.value)
            .where(Lead.updated_at >= today_start)
        )
        deals_today = deals_today_result.scalar() or 0

        # Deals esta semana
        deals_week_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.status == LeadStatus.CONVERTED.value)
            .where(Lead.updated_at >= week_start)
        )
        deals_this_week = deals_week_result.scalar() or 0

        # Ranking de vendedores
        seller_ranking = []
        try:
            sellers_result = await db.execute(
                select(Seller)
                .where(Seller.tenant_id == tenant_id)
                .where(Seller.active == True)
            )
            sellers = sellers_result.scalars().all()

            for seller in sellers:
                # Leads atribuídos (verifica pela data de atribuição, não de criação)
                assigned_result = await db.execute(
                    select(func.count(Lead.id))
                    .where(Lead.tenant_id == tenant_id)
                    .where(Lead.assigned_seller_id == seller.id)
                    .where(
                        or_(
                            Lead.assigned_at >= start_date,
                            and_(Lead.assigned_at.is_(None), Lead.created_at >= start_date)
                        )
                    )
                )
                leads_assigned = assigned_result.scalar() or 0

                # Leads convertidos (mesma janela de tempo)
                converted_seller_result = await db.execute(
                    select(func.count(Lead.id))
                    .where(Lead.tenant_id == tenant_id)
                    .where(Lead.assigned_seller_id == seller.id)
                    .where(Lead.status == LeadStatus.CONVERTED.value)
                    .where(Lead.updated_at >= start_date)
                )
                seller_deals = converted_seller_result.scalar() or 0

                seller_conversion = (seller_deals / leads_assigned * 100) if leads_assigned > 0 else 0

                if leads_assigned > 0 or seller_deals > 0:  # Inclui se tem atividade ou vendas
                    seller_ranking.append(SellerRankingItem(
                        seller_id=seller.id,
                        seller_name=seller.name,
                        deals_count=seller_deals,
                        conversion_rate=round(seller_conversion, 1),
                        leads_assigned=leads_assigned,
                    ))

            # Ordena por conversões
            seller_ranking.sort(key=lambda x: x.deals_count, reverse=True)
            seller_ranking = seller_ranking[:5]  # Top 5

        except Exception as e:
            logger.warning(f"Erro calculando ranking: {e}")

        # ROI por Canal (Revenue by Source)
        revenue_by_source = {}
        try:
            from src.domain.entities import Opportunity
            roi_result = await db.execute(
                select(
                    Lead.source,
                    func.sum(Opportunity.value).label('revenue')
                )
                .join(Opportunity, Lead.id == Opportunity.lead_id)
                .where(Opportunity.tenant_id == tenant_id)
                .where(Opportunity.status == "ganho")
                .group_by(Lead.source)
            )
            revenue_by_source = {row.source: row.revenue for row in roi_result}
        except Exception as e:
            logger.warning(f"Erro calculando ROI por canal: {e}")

        # Sales Pulse (Latest Events)
        pulse = []
        try:
            from src.domain.entities import LeadEvent
            pulse_result = await db.execute(
                select(LeadEvent, Lead.name)
                .join(Lead, LeadEvent.lead_id == Lead.id)
                .where(Lead.tenant_id == tenant_id)
                .order_by(LeadEvent.created_at.desc())
                .limit(10)
            )
            pulse = [
                {
                    "id": ev.id,
                    "type": ev.event_type,
                    "lead_name": name,
                    "description": ev.description,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None
                }
                for ev, name in pulse_result
            ]
        except Exception as e:
            logger.warning(f"Erro buscando Pulse: {e}")

        return SalesMetricsResponse(
            total_deals=total_deals,
            total_revenue=total_revenue,
            average_ticket=average_ticket,
            conversion_rate=round(conversion_rate, 1),
            goal=goal_response if goal_response.id else None,
            projected_deals=projected_deals,
            projected_revenue=projected_revenue,
            on_track=on_track,
            seller_ranking=seller_ranking,
            deals_today=deals_today,
            deals_this_week=deals_this_week,
            revenue_by_source=revenue_by_source,
            pulse=pulse,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro buscando métricas de vendas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao buscar métricas")
