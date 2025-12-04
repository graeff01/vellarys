"""
ADMIN: Gerenciar Planos
========================

CRUD de planos de assinatura.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.domain.entities import User, AdminLog
from src.domain.entities.plan import Plan
from src.api.routes.admin.deps import get_current_superadmin

router = APIRouter(prefix="/admin/plans", tags=["Admin - Planos"])


# ============================================
# SCHEMAS
# ============================================

class PlanCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    price_monthly: float = 0
    price_yearly: float = 0
    limits: Dict[str, Any] = {}
    features: Dict[str, Any] = {}
    sort_order: int = 0
    is_featured: bool = False
    active: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    limits: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_featured: Optional[bool] = None
    active: Optional[bool] = None


# ============================================
# LISTAR PLANOS
# ============================================

@router.get("")
async def list_plans(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os planos."""
    
    query = select(Plan)
    if active_only:
        query = query.where(Plan.active == True)
    
    query = query.order_by(Plan.sort_order, Plan.price_monthly)

    result = await db.execute(query)
    plans = result.scalars().all()

    return {
        "plans": [
            {
                "id": p.id,
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "price_monthly": float(p.price_monthly or 0),
                "price_yearly": float(p.price_yearly or 0),
                "limits": p.limits,
                "features": p.features,
                "sort_order": p.sort_order,
                "is_featured": p.is_featured,
                "active": p.active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in plans
        ],
        "total": len(plans),
    }


# ============================================
# GET PLAN
# ============================================

@router.get("/{plan_id}")
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    return {
        "id": plan.id,
        "slug": plan.slug,
        "name": plan.name,
        "description": plan.description,
        "price_monthly": float(plan.price_monthly),
        "price_yearly": float(plan.price_yearly),
        "limits": plan.limits,
        "features": plan.features,
        "sort_order": plan.sort_order,
        "is_featured": plan.is_featured,
        "active": plan.active,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


# ============================================
# CRIAR PLANO
# ============================================

@router.post("")
async def create_plan(
    data: PlanCreate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Plan).where(Plan.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug já existe")

    plan = Plan(**data.dict())
    db.add(plan)
    await db.flush()

    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="create_plan",
        target_type="plan",
        target_id=plan.id,
        target_name=plan.name,
        details={"slug": plan.slug, "price": float(plan.price_monthly)},
    )
    db.add(log)
    
    await db.commit()

    return {"success": True, "plan": {"id": plan.id, "slug": plan.slug, "name": plan.name}}


# ============================================
# ATUALIZAR PLANO
# ============================================

@router.patch("/{plan_id}")
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    changes = {}

    for key, value in data.dict(exclude_unset=True).items():
        old = getattr(plan, key)
        setattr(plan, key, value)
        changes[key] = {"old": old, "new": value}

    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="update_plan",
        target_type="plan",
        target_id=plan.id,
        target_name=plan.name,
        details=changes,
    )
    db.add(log)

    await db.commit()

    return {"success": True, "changes": changes}


# ============================================
# DESATIVAR PLANO
# ============================================

@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    from src.domain.entities.tenant_subscription import TenantSubscription
    subs = await db.execute(
        select(TenantSubscription).where(TenantSubscription.plan_id == plan_id)
    )

    if subs.scalars().first():
        raise HTTPException(400, "Não é possível deletar plano em uso.")

    plan.active = False

    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="delete_plan",
        target_type="plan",
        target_id=plan.id,
        target_name=plan.name,
        details={"soft_delete": True},
    )
    db.add(log)

    await db.commit()

    return {"success": True, "message": "Plano desativado"}


# ============================================
# SEED DEFAULT PLANS (ÚNICO E CORRETO)
# ============================================

@router.post("/seed-defaults")
async def seed_default_plans(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Cria planos padrão caso não existam."""

    default_plans = [
        {
            "slug": "basic",
            "name": "Basic",
            "description": "Plano básico para começar.",
            "price_monthly": 97,
            "price_yearly": 970,
            "limits": {
                "leads_per_month": 200,
                "messages_per_month": 2000,
                "sellers": 1,
                "niches": 1,
                "ai_tokens_per_month": 100000,
            },
            "features": {
                "reengagement": False,
                "advanced_reports": False,
                "api_access": False,
                "priority_support": False,
                "white_label": False,
                "custom_integrations": False,
            },
            "sort_order": 1,
            "is_featured": False,
        },
        {
            "slug": "professional",
            "name": "Professional",
            "description": "Plano ideal para pequenas equipes.",
            "price_monthly": 297,
            "price_yearly": 2970,
            "limits": {
                "leads_per_month": 1000,
                "messages_per_month": 10000,
                "sellers": 5,
                "niches": 3,
                "ai_tokens_per_month": 500000,
            },
            "features": {
                "reengagement": True,
                "advanced_reports": True,
                "api_access": True,
                "priority_support": False,
                "white_label": False,
                "custom_integrations": False,
            },
            "sort_order": 2,
            "is_featured": True,
        },
        {
            "slug": "enterprise",
            "name": "Enterprise",
            "description": "Plano completo para operação de alta escala.",
            "price_monthly": 997,
            "price_yearly": 9970,
            "limits": {
                "leads_per_month": -1,
                "messages_per_month": -1,
                "sellers": -1,
                "niches": 10,
                "ai_tokens_per_month": -1,
            },
            "features": {
                "reengagement": True,
                "advanced_reports": True,
                "api_access": True,
                "priority_support": True,
                "white_label": True,
                "custom_integrations": True,
            },
            "sort_order": 3,
            "is_featured": False,
        },
    ]

    created = 0

    for p in default_plans:
        exists = await db.execute(select(Plan).where(Plan.slug == p["slug"]))
        if not exists.scalars().first():
            db.add(Plan(**p))
            created += 1

    await db.commit()

    return {"success": True, "created": created}
