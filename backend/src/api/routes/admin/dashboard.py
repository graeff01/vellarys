"""
ADMIN: Dashboard
=================

Métricas gerais de todos os tenants.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, Lead, Message, User, Niche
from src.api.routes.admin.deps import get_current_superadmin

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@router.get("")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas gerais do sistema.
    
    - Total de clientes (ativos/inativos)
    - Total de leads
    - Total de mensagens
    - Leads por status
    - Clientes por plano
    """
    
    # Total de tenants
    total_tenants = await db.execute(select(func.count(Tenant.id)))
    total_tenants = total_tenants.scalar() or 0
    
    active_tenants = await db.execute(
        select(func.count(Tenant.id)).where(Tenant.active == True)
    )
    active_tenants = active_tenants.scalar() or 0
    
    # Total de leads
    total_leads = await db.execute(select(func.count(Lead.id)))
    total_leads = total_leads.scalar() or 0
    
    # Leads quentes
    hot_leads = await db.execute(
        select(func.count(Lead.id)).where(Lead.qualification == "quente")
    )
    hot_leads = hot_leads.scalar() or 0
    
    # Total de mensagens
    total_messages = await db.execute(select(func.count(Message.id)))
    total_messages = total_messages.scalar() or 0
    
    # Total de usuários
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar() or 0
    
    # Total de nichos
    total_niches = await db.execute(select(func.count(Niche.id)))
    total_niches = total_niches.scalar() or 0
    
    # Tenants por plano
    tenants_by_plan = await db.execute(
        select(Tenant.plan, func.count(Tenant.id))
        .group_by(Tenant.plan)
    )
    tenants_by_plan = {row[0]: row[1] for row in tenants_by_plan.all()}
    
    # Leads por status
    leads_by_status = await db.execute(
        select(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
    )
    leads_by_status = {row[0]: row[1] for row in leads_by_status.all()}
    
    # Top 5 tenants por leads
    top_tenants = await db.execute(
        select(Tenant.id, Tenant.name, Tenant.slug, func.count(Lead.id).label("leads_count"))
        .join(Lead, Lead.tenant_id == Tenant.id, isouter=True)
        .group_by(Tenant.id)
        .order_by(func.count(Lead.id).desc())
        .limit(5)
    )
    top_tenants = [
        {"id": row[0], "name": row[1], "slug": row[2], "leads_count": row[3]}
        for row in top_tenants.all()
    ]
    
    return {
        "tenants": {
            "total": total_tenants,
            "active": active_tenants,
            "inactive": total_tenants - active_tenants,
        },
        "leads": {
            "total": total_leads,
            "hot": hot_leads,
        },
        "messages": {
            "total": total_messages,
        },
        "users": {
            "total": total_users,
        },
        "niches": {
            "total": total_niches,
        },
        "tenants_by_plan": tenants_by_plan,
        "leads_by_status": leads_by_status,
        "top_tenants": top_tenants,
    }