"""
ADMIN: Gerenciar Planos
========================

CRUD de planos de assinatura.
"""

from typing import Optional, List, Dict, Any
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
# ROTAS
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
    
    plans_data = []
    for plan in plans:
        plans_data.append({
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
        })
    
    return {"plans": plans_data, "total": len(plans_data)}


@router.get("/{plan_id}")
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de um plano."""
    
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
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


@router.post("")
async def create_plan(
    data: PlanCreate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo plano."""
    
    # Verificar se slug já existe
    existing = await db.execute(
        select(Plan).where(Plan.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug já existe")
    
    plan = Plan(
        slug=data.slug,
        name=data.name,
        description=data.description,
        price_monthly=data.price_monthly,
        price_yearly=data.price_yearly,
        limits=data.limits,
        features=data.features,
        sort_order=data.sort_order,
        is_featured=data.is_featured,
        active=data.active,
    )
    db.add(plan)
    await db.flush()
    
    # Log
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
    
    return {
        "success": True,
        "plan": {
            "id": plan.id,
            "slug": plan.slug,
            "name": plan.name,
        }
    }


@router.patch("/{plan_id}")
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um plano."""
    
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    changes = {}
    
    if data.name is not None:
        changes["name"] = {"old": plan.name, "new": data.name}
        plan.name = data.name
    
    if data.description is not None:
        plan.description = data.description
    
    if data.price_monthly is not None:
        changes["price_monthly"] = {"old": float(plan.price_monthly), "new": data.price_monthly}
        plan.price_monthly = data.price_monthly
    
    if data.price_yearly is not None:
        plan.price_yearly = data.price_yearly
    
    if data.limits is not None:
        changes["limits"] = "atualizado"
        plan.limits = data.limits
    
    if data.features is not None:
        changes["features"] = "atualizado"
        plan.features = data.features
    
    if data.sort_order is not None:
        plan.sort_order = data.sort_order
    
    if data.is_featured is not None:
        plan.is_featured = data.is_featured
    
    if data.active is not None:
        changes["active"] = {"old": plan.active, "new": data.active}
        plan.active = data.active
    
    # Log
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


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    permanent: bool = False,
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta ou desativa um plano.

    - permanent=False (padrão): Apenas desativa (soft delete)
    - permanent=True: Deleta permanentemente do banco
    """

    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Verificar se há tenants usando esse plano
    from src.domain.entities.tenant_subscription import TenantSubscription
    subs_result = await db.execute(
        select(TenantSubscription).where(TenantSubscription.plan_id == plan_id)
    )
    has_subscribers = subs_result.scalars().first() is not None

    if has_subscribers:
        raise HTTPException(
            status_code=400,
            detail="Não é possível deletar plano em uso. Migre os clientes para outro plano primeiro."
        )

    if permanent:
        # Hard delete - Remove permanentemente do banco
        plan_name = plan.name
        await db.delete(plan)

        # Log
        log = AdminLog(
            admin_id=current_user.id,
            admin_email=current_user.email,
            action="delete_plan_permanent",
            target_type="plan",
            target_id=plan_id,
            target_name=plan_name,
            details={"permanent": True},
        )
        db.add(log)

        await db.commit()

        return {"success": True, "message": f"Plano '{plan_name}' deletado permanentemente"}
    else:
        # Soft delete - Apenas desativa
        plan.active = False

        # Log
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


@router.post("/seed-defaults")
async def seed_default_plans(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Cria os planos padrão do sistema."""
    
    default_plans = [
        {
            "slug": "essencial",
            "name": "Essencial",
            "description": "Para imobiliárias iniciando com IA",
            "price_monthly": 297.00,
            "price_yearly": 2970.00,
            "sort_order": 1,
            "is_featured": False,
            "limits": {
                "leads_per_month": 300,
                "messages_per_month": 3000,
                "sellers": 3,
                "ai_tokens_per_month": 150000,
            },
            "features": {
                "ai_qualification": True,
                "whatsapp_integration": True,
                "web_chat": True,
                "push_notifications": True,
                "basic_reports": True,
                "lead_export": True,
                "appointment_booking": False,
                "calendar_integration": False,
                "reengagement": False,
                "advanced_reports": False,
                "humanized_voice": False,
                "multi_channel": False,
                "semantic_search": False,
                "api_access": False,
                "white_label": False,
                "priority_support": False,
            },
        },
        {
            "slug": "professional",
            "name": "Professional",
            "description": "Melhor custo-benefício para crescimento",
            "price_monthly": 697.00,
            "price_yearly": 6970.00,
            "sort_order": 2,
            "is_featured": True,
            "limits": {
                "leads_per_month": 1500,
                "messages_per_month": 15000,
                "sellers": 15,
                "ai_tokens_per_month": 750000,
            },
            "features": {
                "ai_qualification": True,
                "whatsapp_integration": True,
                "web_chat": True,
                "push_notifications": True,
                "basic_reports": True,
                "lead_export": True,
                "appointment_booking": True,
                "appointment_mode": "assisted",
                "calendar_integration": True,
                "reengagement": True,
                "advanced_reports": True,
                "humanized_voice": True,
                "multi_channel": True,
                "semantic_search": True,
                "api_access": False,
                "white_label": False,
                "priority_support": False,
            },
        },
        {
            "slug": "enterprise",
            "name": "Enterprise",
            "description": "Solução completa para grandes operações",
            "price_monthly": 1497.00,
            "price_yearly": 14970.00,
            "sort_order": 3,
            "is_featured": False,
            "limits": {
                "leads_per_month": -1,
                "messages_per_month": -1,
                "sellers": -1,
                "ai_tokens_per_month": 2000000,
            },
            "features": {
                "ai_qualification": True,
                "whatsapp_integration": True,
                "web_chat": True,
                "push_notifications": True,
                "basic_reports": True,
                "lead_export": True,
                "appointment_booking": True,
                "appointment_mode": "automatic",
                "calendar_integration": True,
                "appointment_auto_create": True,
                "appointment_reminders": True,
                "calendar_email_invites": True,
                "reengagement": True,
                "advanced_reports": True,
                "humanized_voice": True,
                "multi_channel": True,
                "semantic_search": True,
                "api_access": True,
                "webhooks": True,
                "white_label": True,
                "priority_support": True,
                "account_manager": True,
                "custom_integrations": True,
                "sla_99_5": True,
            },
        },
    ]
    
    created = 0
    skipped = 0
    
    for plan_data in default_plans:
        existing = await db.execute(
            select(Plan).where(Plan.slug == plan_data["slug"])
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        plan = Plan(
            slug=plan_data["slug"],
            name=plan_data["name"],
            description=plan_data["description"],
            price_monthly=plan_data["price_monthly"],
            price_yearly=plan_data["price_yearly"],
            limits=plan_data["limits"],
            features=plan_data["features"],
            sort_order=plan_data["sort_order"],
            is_featured=plan_data["is_featured"],
            active=True,
        )
        db.add(plan)
        created += 1
    
    # Log
    log = AdminLog(
        admin_id=current_user.id,
        admin_email=current_user.email,
        action="seed_plans",
        target_type="plan",
        target_id=None,
        target_name=None,
        details={"created": created, "skipped": skipped},
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "created": created,
        "skipped": skipped,
        "message": f"{created} planos criados, {skipped} já existiam"
    }
