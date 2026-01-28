"""
Settings V2 Routes - Nova Arquitetura de Entitlements

Endpoints paralelos (não substituem os v1):
- GET /v2/settings/entitlements - Resolve entitlements (plan + overrides)
- GET /v2/settings/flags - Lista feature flags
- PATCH /v2/settings/flags - Atualiza feature flags (Gestor)
- POST /v2/settings/overrides - Cria/atualiza overrides (SuperAdmin)
"""

import logging
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user, get_current_tenant, get_db
from src.domain.entities.models import User, Tenant
from src.domain.entities.enums import UserRole

from src.services.entitlements import EntitlementResolver
from src.services.feature_flags import FeatureFlagService
from src.services.permissions import PermissionService
from src.services.access_decision import AccessDecisionEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/settings", tags=["Settings V2 (New Architecture)"])


# =============================================================================
# SCHEMAS
# =============================================================================

class EntitlementsResponse(BaseModel):
    """Resposta de entitlements resolvidos."""
    features: Dict[str, bool]
    limits: Dict[str, int]
    source: Dict[str, str]  # De onde veio cada entitlement
    plan_name: Optional[str] = None


class FeatureFlagsResponse(BaseModel):
    """Resposta de feature flags."""
    flags: Dict[str, bool]
    tenant_id: int


class UpdateFlagsRequest(BaseModel):
    """Request para atualizar flags."""
    flags: Dict[str, bool] = Field(..., description="Flags a atualizar {key: enabled}")
    reason: Optional[str] = Field(None, description="Motivo da alteração")


class CreateOverrideRequest(BaseModel):
    """Request para criar override (SuperAdmin)."""
    override_key: str = Field(..., description="Key do entitlement")
    override_type: str = Field(..., description="feature | limit")
    override_value: dict = Field(..., description="Valor do override")
    reason: Optional[str] = Field(None, description="Motivo do override")
    expires_at: Optional[str] = Field(None, description="Data de expiração (ISO 8601)")


class AccessDecisionResponse(BaseModel):
    """Resposta de decisão de acesso."""
    allowed: bool
    reason: str
    entitled: bool
    flag_active: bool
    role_permitted: bool


# =============================================================================
# ENTITLEMENTS ENDPOINTS
# =============================================================================

@router.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna entitlements resolvidos (plano + overrides).

    HIERARQUIA:
    - SuperAdmin: Pode consultar qualquer tenant via target_tenant_id
    - Gestor/Admin: Consulta próprio tenant
    - Vendedor: Não tem acesso (403)

    Returns:
        EntitlementsResponse com features, limits e source
    """

    # Validação: Vendedor não pode acessar
    if user.role not in ["superadmin", "admin", "gestor"]:
        raise HTTPException(403, "Apenas gestores podem consultar entitlements")

    # SuperAdmin pode gerenciar outro tenant
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"🔴 [SUPERADMIN V2] {user.email} consultando entitlements do tenant_id {target_tenant_id}")
        tenant_id = target_tenant_id
    else:
        tenant_id = tenant.id

    # Resolver entitlements
    resolver = EntitlementResolver(db)
    entitlements = await resolver.resolve_for_tenant(tenant_id)

    # Buscar nome do plano
    from sqlalchemy import select
    from src.domain.entities.tenant_subscription import TenantSubscription
    from sqlalchemy.orm import selectinload

    stmt = select(TenantSubscription)\
        .options(selectinload(TenantSubscription.plan))\
        .where(TenantSubscription.tenant_id == tenant_id)

    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    plan_name = None
    if subscription and subscription.plan:
        plan_name = subscription.plan.name

    return EntitlementsResponse(
        features=entitlements.features,
        limits=entitlements.limits,
        source=entitlements.source,
        plan_name=plan_name
    )


# =============================================================================
# FEATURE FLAGS ENDPOINTS
# =============================================================================

@router.get("/flags", response_model=FeatureFlagsResponse)
async def get_flags(
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna feature flags do tenant.

    HIERARQUIA:
    - SuperAdmin: Pode consultar qualquer tenant
    - Gestor/Admin: Consulta próprio tenant
    - Vendedor: Não tem acesso (403)

    Returns:
        FeatureFlagsResponse com flags
    """

    # Validação
    if user.role not in ["superadmin", "admin", "gestor"]:
        raise HTTPException(403, "Apenas gestores podem consultar flags")

    # SuperAdmin pode gerenciar outro tenant
    if target_tenant_id and user.role == "superadmin":
        tenant_id = target_tenant_id
    else:
        tenant_id = tenant.id

    # Buscar flags
    service = FeatureFlagService(db)
    flags = await service.get_flags(tenant_id)

    return FeatureFlagsResponse(
        flags=flags,
        tenant_id=tenant_id
    )


@router.patch("/flags")
async def update_flags(
    payload: UpdateFlagsRequest,
    request: Request,
    target_tenant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza feature flags (Gestor).

    HIERARQUIA:
    - SuperAdmin: Pode atualizar flags de qualquer tenant
    - Gestor/Admin: Atualiza próprio tenant (COM VALIDAÇÃO de plano)
    - Vendedor: Não tem acesso (403)

    VALIDAÇÃO IMPORTANTE:
    - Gestor NÃO pode ativar features além do plano
    - Gestor PODE desativar features do plano
    """

    # Validação de permissão
    if user.role not in ["superadmin", "admin", "gestor"]:
        raise HTTPException(403, "Apenas gestores podem alterar flags")

    # SuperAdmin pode gerenciar outro tenant
    is_managing_other = False
    if target_tenant_id and user.role == "superadmin":
        logger.info(f"🔴 [SUPERADMIN V2] {user.email} alterando flags do tenant_id {target_tenant_id}")
        tenant_id = target_tenant_id
        is_managing_other = True
    else:
        tenant_id = tenant.id

    # Validação: Gestor não pode ativar além do plano
    if user.role in ["admin", "gestor"] and not is_managing_other:
        resolver = EntitlementResolver(db)
        entitlements = await resolver.resolve_for_tenant(tenant_id)

        for flag_key, flag_value in payload.flags.items():
            # Se tentando ATIVAR
            if flag_value:
                # Verificar se plano permite
                plan_allows = entitlements.features.get(flag_key, False)
                if not plan_allows:
                    logger.error(f"⛔ Gestor tentou ativar '{flag_key}' fora do plano")
                    raise HTTPException(
                        403,
                        f"Feature '{flag_key}' não disponível no seu plano. Faça upgrade para usar."
                    )

    # Atualizar flags
    service = FeatureFlagService(db)

    # Contexto da requisição
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await service.bulk_set_flags(
        tenant_id=tenant_id,
        flags=payload.flags,
        changed_by_id=user.id,
        reason=payload.reason,
        ip_address=ip_address,
        user_agent=user_agent
    )

    logger.info(f"✅ Flags atualizados com sucesso para tenant {tenant_id}")

    return {
        "success": True,
        "message": "Flags atualizados com sucesso",
        "tenant_id": tenant_id,
        "updated_flags": payload.flags
    }


# =============================================================================
# OVERRIDES ENDPOINTS (SuperAdmin only)
# =============================================================================

@router.post("/overrides")
async def create_override(
    payload: CreateOverrideRequest,
    target_tenant_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria/atualiza override de entitlement (SuperAdmin apenas).

    Permite que SuperAdmin:
    - Ative features não incluídas no plano
    - Desative features incluídas no plano
    - Customize limites

    IMPORTANTE: Apenas SuperAdmin pode criar overrides!
    """

    # Validação: Apenas SuperAdmin
    if user.role != "superadmin":
        raise HTTPException(403, "Apenas SuperAdmin pode criar overrides")

    # Buscar subscription
    from sqlalchemy import select
    from src.domain.entities.tenant_subscription import TenantSubscription

    stmt = select(TenantSubscription).where(
        TenantSubscription.tenant_id == target_tenant_id
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(404, f"Subscription não encontrada para tenant {target_tenant_id}")

    # Criar/atualizar override
    from src.domain.entities.subscription_override import SubscriptionOverride
    from datetime import datetime

    # Verificar se já existe
    stmt = select(SubscriptionOverride).where(
        SubscriptionOverride.subscription_id == subscription.id,
        SubscriptionOverride.override_key == payload.override_key
    )
    result = await db.execute(stmt)
    override = result.scalar_one_or_none()

    if override:
        # Atualizar existente
        old_value = override.override_value
        override.override_value = payload.override_value
        override.override_type = payload.override_type
        override.reason = payload.reason
        if payload.expires_at:
            override.expires_at = datetime.fromisoformat(payload.expires_at)
    else:
        # Criar novo
        old_value = None
        override = SubscriptionOverride(
            subscription_id=subscription.id,
            override_key=payload.override_key,
            override_type=payload.override_type,
            override_value=payload.override_value,
            created_by_id=user.id,
            reason=payload.reason,
            expires_at=datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
        )
        db.add(override)

    # Audit log
    from src.domain.entities.feature_audit_log import FeatureAuditLog, ChangeType

    audit = FeatureAuditLog(
        tenant_id=target_tenant_id,
        change_type=ChangeType.OVERRIDE,
        entity_type=payload.override_type,
        entity_key=payload.override_key,
        old_value=old_value,
        new_value=payload.override_value,
        changed_by_id=user.id,
        reason=payload.reason,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit)

    await db.commit()
    await db.refresh(override)

    logger.info(f"✅ Override criado/atualizado: {payload.override_key} para tenant {target_tenant_id}")

    return {
        "success": True,
        "message": "Override criado/atualizado com sucesso",
        "override": override.to_dict()
    }


# =============================================================================
# ACCESS DECISION ENDPOINT (útil para debug)
# =============================================================================

@router.get("/access-decision/{feature_key}", response_model=AccessDecisionResponse)
async def check_access_decision(
    feature_key: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Verifica decisão de acesso para uma feature específica.

    Útil para debug e entender por que uma feature está bloqueada.

    Returns:
        AccessDecisionResponse com contexto completo
    """

    engine = AccessDecisionEngine(db)
    decision = await engine.can_access_feature(
        tenant_id=tenant.id,
        user=user,
        feature_key=feature_key
    )

    return AccessDecisionResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        entitled=decision.entitled,
        flag_active=decision.flag_active,
        role_permitted=decision.role_permitted
    )
