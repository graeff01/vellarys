"""
ROTAS ADMIN: TENANTS (CLIENTES)
================================

CRUD de clientes da plataforma.
Inclui criação de usuário admin e subscription para o cliente.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from src.infrastructure.database import get_db
from src.infrastructure.services.auth_service import hash_password
from src.domain.entities import Tenant, User, Lead, Message, Channel, AdminLog, Seller
from src.domain.entities.enums import UserRole
from src.domain.entities.plan import Plan
from src.domain.entities.tenant_subscription import TenantSubscription
from src.domain.entities.tenant_usage import TenantUsage
from src.api.routes.admin.deps import get_current_superadmin


router = APIRouter(prefix="/admin/tenants", tags=["Admin - Clientes"])

# Dias de trial padrão
DEFAULT_TRIAL_DAYS = 30


# ============================================
# SCHEMAS
# ============================================

class TenantCreate(BaseModel):
    """Schema para criar cliente com usuário admin."""
    # Dados do Tenant
    name: str
    slug: str
    plan: str = "starter"  # slug do plano
    niche: str = "services"
    
    # Dados do Usuário Admin do Cliente
    admin_name: str
    admin_email: EmailStr
    admin_password: str
    
    # Opções de assinatura
    billing_cycle: str = "monthly"  # monthly ou yearly
    trial_days: int = DEFAULT_TRIAL_DAYS  # 0 = sem trial
    
    # Integração WhatsApp / 360dialog
    whatsapp_number: Optional[str] = None
    dialog360_api_key: Optional[str] = None
    webhook_verify_token: Optional[str] = None


class TenantUpdate(BaseModel):
    """Schema para atualizar cliente."""
    name: Optional[str] = None
    plan: Optional[str] = None  # slug do plano
    settings: Optional[dict] = None
    active: Optional[bool] = None
    billing_cycle: Optional[str] = None
    custom_limits: Optional[dict] = None


class SubscriptionUpdate(BaseModel):
    """Schema para atualizar subscription."""
    plan: Optional[str] = None
    status: Optional[str] = None
    billing_cycle: Optional[str] = None
    extend_trial_days: Optional[int] = None
    reset_limits: Optional[bool] = None
    custom_limits: Optional[dict] = None


class UserCreate(BaseModel):
    """Schema para criar usuário adicional para um cliente."""
    name: str
    email: EmailStr
    password: str
    role: str = "user"  # user, manager, admin


# ============================================
# ROTAS
# ============================================

@router.get("")
async def list_tenants(
    search: Optional[str] = None,
    plan: Optional[str] = None,
    active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """Lista todos os clientes com filtros."""
    
    query = select(Tenant)
    
    # Filtros
    if search:
        query = query.where(
            Tenant.name.ilike(f"%{search}%") | 
            Tenant.slug.ilike(f"%{search}%")
        )
    if plan:
        query = query.where(Tenant.plan == plan)
    if active is not None:
        query = query.where(Tenant.active == active)
    
    # Ordenação e paginação
    query = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    # Conta leads e usuários para cada tenant
    tenants_data = []
    for tenant in tenants:
        # Conta leads
        leads_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
        )
        leads_count = leads_result.scalar() or 0
        
        # Conta usuários
        users_result = await db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        )
        users_count = users_result.scalar() or 0
        
        # Busca subscription
        sub_result = await db.execute(
            select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id)
        )
        subscription = sub_result.scalar_one_or_none()
        
        tenants_data.append({
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "active": tenant.active,
            "settings": tenant.settings,
            "leads_count": leads_count,
            "users_count": users_count,
            "subscription": {
                "status": subscription.status if subscription else "none",
                "billing_cycle": subscription.billing_cycle if subscription else None,
                "is_trial": subscription.is_trial() if subscription else False,
                "trial_days_remaining": subscription.days_remaining_trial() if subscription else 0,
                "is_blocked": subscription.is_blocked() if subscription else False,
            } if subscription else None,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        })
    
    return {"tenants": tenants_data, "total": len(tenants_data)}


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """Retorna detalhes completos de um cliente específico."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    # Busca usuários do tenant
    users_result = await db.execute(
        select(User).where(User.tenant_id == tenant.id).order_by(User.created_at)
    )
    users = users_result.scalars().all()
    
    # Busca vendedores do tenant
    sellers_result = await db.execute(
        select(Seller).where(Seller.tenant_id == tenant.id).order_by(Seller.name)
    )
    sellers = sellers_result.scalars().all()
    
    # Conta leads por vendedor
    sellers_data = []
    for seller in sellers:
        seller_leads_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.assigned_seller_id == seller.id)
        )
        seller_leads_count = seller_leads_result.scalar() or 0
        sellers_data.append({
            "id": seller.id,
            "name": seller.name,
            "email": seller.email,
            "active": seller.active,
            "leads_count": seller_leads_count,
        })

    
    # Conta leads total
    leads_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.tenant_id == tenant.id)
    )
    leads_count = leads_result.scalar() or 0
    
    # Conta mensagens
    messages_result = await db.execute(
        select(func.count(Message.id))
        .join(Lead, Message.lead_id == Lead.id)
        .where(Lead.tenant_id == tenant.id)
    )
    messages_count = messages_result.scalar() or 0
    
    # Busca leads recentes
    recent_leads_result = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant.id)
        .order_by(Lead.created_at.desc())
        .limit(10)
    )
    recent_leads = recent_leads_result.scalars().all()
    
    # Busca subscription com plano
    sub_result = await db.execute(
        select(TenantSubscription)
        .options(selectinload(TenantSubscription.plan))
        .where(TenantSubscription.tenant_id == tenant.id)
    )
    subscription = sub_result.scalar_one_or_none()
    
    # Busca uso atual
    current_period = TenantUsage.get_current_period()
    usage_result = await db.execute(
        select(TenantUsage).where(
            TenantUsage.tenant_id == tenant.id,
            TenantUsage.period == current_period
        )
    )
    usage = usage_result.scalar_one_or_none()
    
    # Monta resposta
    response = {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "active": tenant.active,
        "settings": tenant.settings,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        
        # Contagens
        "leads_count": leads_count,
        "users_count": len(users),
        "sellers_count": len([s for s in sellers if s.active]),
        "messages_count": messages_count,
        
        # Usuários
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "active": u.active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        
        # Vendedores
        "sellers": sellers_data,
        
        # Leads recentes
        "recent_leads": [
            {
                "id": l.id,
                "name": l.name,
                "phone": l.phone,
                "qualification": l.qualification,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in recent_leads
        ],
    }
    
    # Subscription info
    if subscription:
        response["subscription"] = {
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "is_trial": subscription.is_trial(),
            "trial_started_at": subscription.trial_started_at.isoformat() if subscription.trial_started_at else None,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
            "days_remaining_trial": subscription.days_remaining_trial() if subscription.is_trial() else 0,
            "is_blocked": subscription.is_blocked(),
            "limit_exceeded_reason": subscription.limit_exceeded_reason,
            "custom_limits": subscription.custom_limits,
        }
        
        # Limites do plano
        if subscription.plan:
            response["plan_limits"] = {
                "leads_per_month": subscription.get_limit("leads_per_month"),
                "messages_per_month": subscription.get_limit("messages_per_month"),
                "sellers": subscription.get_limit("sellers"),
            }
    
    # Uso atual
    if usage:
        response["usage"] = {
            "period": usage.period,
            "leads_count": usage.leads_count,
            "messages_count": usage.messages_count,
            "ai_tokens_used": usage.ai_tokens_used,
        }
    else:
        response["usage"] = {
            "period": current_period,
            "leads_count": 0,
            "messages_count": 0,
            "ai_tokens_used": 0,
        }
    
    return response


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """
    Cria novo cliente com usuário admin e subscription.
    
    Cria:
    1. Tenant (empresa)
    2. Usuário admin para o cliente
    3. Canal WhatsApp padrão
    4. Subscription com trial (se configurado)
    5. Registro de uso inicial
    """
    
    # Verifica se slug já existe
    result = await db.execute(
        select(Tenant).where(Tenant.slug == data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug já está em uso",
        )
    
    # Verifica se email já existe
    result = await db.execute(
        select(User).where(User.email == data.admin_email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está cadastrado",
        )
    
    # Busca o plano
    plan_result = await db.execute(
        select(Plan).where(Plan.slug == data.plan, Plan.active == True)
    )
    plan = plan_result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plano '{data.plan}' não encontrado ou inativo",
        )
    
    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        plan=data.plan,
        settings={
            "niche": data.niche,
            "company_name": data.name,
            "tone": "cordial",
            "custom_questions": [],
            "custom_rules": [],
            # 360dialog config
            "whatsapp_number": data.whatsapp_number,
            "dialog360_api_key": data.dialog360_api_key,
            "webhook_verify_token": data.webhook_verify_token or "velaris_webhook_token",
        },
        active=True,
    )
    db.add(tenant)
    await db.flush()
    
    # Cria usuário admin do cliente
    user = User(
        tenant_id=tenant.id,
        name=data.admin_name,
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        role=UserRole.ADMIN.value,
        active=True,
    )
    db.add(user)
    
# Cria canal WhatsApp padrão com config do 360dialog
    channel = Channel(
        tenant_id=tenant.id,
        type="whatsapp",
        name="WhatsApp Principal",
        config={
            "phone_number": data.whatsapp_number,
            "api_key": data.dialog360_api_key,
            "webhook_verify_token": data.webhook_verify_token or "velaris_webhook_token",
        } if data.dialog360_api_key else {},
        active=True,
    )
    db.add(channel)
    
    # Cria subscription
    now = datetime.now(timezone.utc)
    
    subscription = TenantSubscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        billing_cycle=data.billing_cycle,
        status="trial" if data.trial_days > 0 else "active",
        trial_started_at=now if data.trial_days > 0 else None,
        trial_ends_at=now + timedelta(days=data.trial_days) if data.trial_days > 0 else None,
        started_at=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30) if data.billing_cycle == "monthly" else now + timedelta(days=365),
    )
    db.add(subscription)
    
    # Cria registro de uso inicial
    usage = TenantUsage(
        tenant_id=tenant.id,
        period=TenantUsage.get_current_period(),
    )
    db.add(usage)
    
    # Log da ação
    log = AdminLog(
        admin_id=admin.id,
        admin_email=admin.email,
        action="create_tenant",
        target_type="tenant",
        target_id=tenant.id,
        target_name=tenant.name,
        details={
            "plan": data.plan,
            "niche": data.niche,
            "admin_email": data.admin_email,
            "billing_cycle": data.billing_cycle,
            "trial_days": data.trial_days,
            "whatsapp_configured": bool(data.dialog360_api_key),
        },
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Cliente criado com sucesso",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
        },
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "subscription": {
            "status": subscription.status,
            "trial_days": data.trial_days,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
        },
        "whatsapp": {
            "configured": bool(data.dialog360_api_key),
            "number": data.whatsapp_number,
            "webhook_url": f"https://hopeful-purpose-production-3a2b.up.railway.app/api/v1/webhook/360dialog",
        },
    }


@router.post("/{tenant_id}/users", status_code=status.HTTP_201_CREATED)
async def create_tenant_user(
    tenant_id: int,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """Cria usuário adicional para um cliente."""
    
    # Verifica se tenant existe
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    # Verifica se email já existe
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está cadastrado",
        )
    
    # Valida role
    valid_roles = ["user", "manager", "admin"]
    if data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role inválido. Use: {', '.join(valid_roles)}",
        )
    
    # Cria usuário
    user = User(
        tenant_id=tenant.id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        active=True,
    )
    db.add(user)
    
    # Log da ação
    log = AdminLog(
        admin_id=admin.id,
        admin_email=admin.email,
        action="create_user",
        target_type="user",
        target_id=None,
        target_name=data.email,
        details={
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "role": data.role,
        },
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Usuário criado com sucesso",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """Atualiza dados de um cliente."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    # Busca subscription
    sub_result = await db.execute(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    subscription = sub_result.scalar_one_or_none()
    
    # Atualiza campos do tenant
    changes = {}
    if data.name is not None:
        changes["name"] = {"from": tenant.name, "to": data.name}
        tenant.name = data.name
    
    if data.plan is not None and data.plan != tenant.plan:
        # Busca novo plano
        plan_result = await db.execute(
            select(Plan).where(Plan.slug == data.plan, Plan.active == True)
        )
        new_plan = plan_result.scalar_one_or_none()
        
        if not new_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plano '{data.plan}' não encontrado ou inativo",
            )
        
        changes["plan"] = {"from": tenant.plan, "to": data.plan}
        tenant.plan = data.plan
        
        # Atualiza subscription
        if subscription:
            subscription.plan_id = new_plan.id
            # Reseta bloqueio se estava bloqueado
            if subscription.is_limit_exceeded:
                subscription.is_limit_exceeded = False
                subscription.limit_exceeded_at = None
                subscription.limit_exceeded_reason = None
                subscription.tolerance_used = 0
    
    if data.settings is not None:
        changes["settings"] = "updated"
        tenant.settings = {**(tenant.settings or {}), **data.settings}
    
    if data.active is not None:
        changes["active"] = {"from": tenant.active, "to": data.active}
        tenant.active = data.active
    
    # Atualiza subscription
    if subscription:
        if data.billing_cycle is not None:
            changes["billing_cycle"] = {"from": subscription.billing_cycle, "to": data.billing_cycle}
            subscription.billing_cycle = data.billing_cycle
        
        if data.custom_limits is not None:
            changes["custom_limits"] = "updated"
            subscription.custom_limits = data.custom_limits
    
    # Log da ação
    log = AdminLog(
        admin_id=admin.id,
        admin_email=admin.email,
        action="update_tenant",
        target_type="tenant",
        target_id=tenant.id,
        target_name=tenant.name,
        details=changes,
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Cliente atualizado",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "active": tenant.active,
        },
    }


@router.patch("/{tenant_id}/subscription")
async def update_subscription(
    tenant_id: int,
    data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """
    Atualiza a subscription de um cliente.
    
    - plan: Muda o plano
    - status: trial, active, past_due, canceled, suspended
    - extend_trial_days: Adiciona dias ao trial
    - reset_limits: Desbloqueia se estava bloqueado por limite
    """
    
    # Busca subscription
    result = await db.execute(
        select(TenantSubscription)
        .options(selectinload(TenantSubscription.plan))
        .where(TenantSubscription.tenant_id == tenant_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription não encontrada",
        )
    
    changes = {}
    
    # Mudar plano
    if data.plan is not None:
        plan_result = await db.execute(
            select(Plan).where(Plan.slug == data.plan, Plan.active == True)
        )
        new_plan = plan_result.scalar_one_or_none()
        
        if not new_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plano '{data.plan}' não encontrado ou inativo",
            )
        
        changes["plan"] = {"from": subscription.plan.slug if subscription.plan else None, "to": data.plan}
        subscription.plan_id = new_plan.id
        
        # Atualiza também no tenant
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if tenant:
            tenant.plan = data.plan
    
    # Mudar status
    if data.status is not None:
        valid_statuses = ["trial", "active", "past_due", "canceled", "suspended"]
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido. Use: {', '.join(valid_statuses)}",
            )
        changes["status"] = {"from": subscription.status, "to": data.status}
        subscription.status = data.status
    
    # Mudar ciclo
    if data.billing_cycle is not None:
        changes["billing_cycle"] = {"from": subscription.billing_cycle, "to": data.billing_cycle}
        subscription.billing_cycle = data.billing_cycle
    
    # Estender trial
    if data.extend_trial_days is not None and data.extend_trial_days > 0:
        if subscription.trial_ends_at:
            new_end = subscription.trial_ends_at + timedelta(days=data.extend_trial_days)
        else:
            new_end = datetime.now(timezone.utc) + timedelta(days=data.extend_trial_days)
            subscription.trial_started_at = datetime.now(timezone.utc)
        
        changes["trial_extended"] = {"days": data.extend_trial_days, "new_end": new_end.isoformat()}
        subscription.trial_ends_at = new_end
        
        # Se estava com status diferente de trial, voltar para trial
        if subscription.status != "trial":
            changes["status"] = {"from": subscription.status, "to": "trial"}
            subscription.status = "trial"
    
    # Resetar limites (desbloquear)
    if data.reset_limits:
        changes["limits_reset"] = True
        subscription.is_limit_exceeded = False
        subscription.limit_exceeded_at = None
        subscription.limit_exceeded_reason = None
        subscription.tolerance_used = 0
    
    # Custom limits
    if data.custom_limits is not None:
        changes["custom_limits"] = "updated"
        subscription.custom_limits = data.custom_limits
    
    # Log
    log = AdminLog(
        admin_id=admin.id,
        admin_email=admin.email,
        action="update_subscription",
        target_type="subscription",
        target_id=subscription.id,
        target_name=f"Tenant #{tenant_id}",
        details=changes,
    )
    db.add(log)
    
    await db.commit()
    
    return {
        "success": True,
        "changes": changes,
        "subscription": {
            "status": subscription.status,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
            "is_blocked": subscription.is_blocked(),
        },
    }


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin),
):
    """
    Desativa um cliente (soft delete).
    
    Não deleta permanentemente para manter histórico.
    """
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    
    # Não permite deletar tenant admin
    if tenant.slug == "velaris-admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível desativar o tenant admin",
        )
    
    tenant.active = False
    
    # Cancela subscription
    sub_result = await db.execute(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    subscription = sub_result.scalar_one_or_none()
    if subscription:
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(timezone.utc)
    
    # Log da ação
    log = AdminLog(
        admin_id=admin.id,
        admin_email=admin.email,
        action="delete_tenant",
        target_type="tenant",
        target_id=tenant.id,
        target_name=tenant.name,
        details={"action": "soft_delete"},
    )
    db.add(log)
    
    await db.commit()
    
    return {"success": True, "message": "Cliente desativado"}