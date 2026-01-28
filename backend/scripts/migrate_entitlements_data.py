"""
Script de Migração de Dados - Entitlements V2

Migra dados de:
1. Plan.features (JSONB) → plan_entitlements (rows)
2. Plan.limits (JSONB) → plan_entitlements (rows)
3. tenant.settings.team_features → feature_flags
4. tenant.settings.feature_overrides → subscription_overrides

IMPORTANTE: Execute APENAS UMA VEZ após criar as tabelas!
"""

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import async_session
from src.domain.entities.plan import Plan
from src.domain.entities.models import Tenant, User
from src.domain.entities.tenant_subscription import TenantSubscription
from src.domain.entities.plan_entitlement import PlanEntitlement, EntitlementType, EntitlementCategory
from src.domain.entities.subscription_override import SubscriptionOverride
from src.domain.entities.feature_flag import FeatureFlag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_plan_entitlements(session: AsyncSession):
    """
    Migra Plan.features e Plan.limits → plan_entitlements.
    """
    logger.info("=" * 80)
    logger.info("FASE 1: Migrando Plan.features e Plan.limits → plan_entitlements")
    logger.info("=" * 80)

    # Buscar todos os planos
    result = await session.execute(select(Plan))
    plans = result.scalars().all()

    logger.info(f"📦 Encontrados {len(plans)} planos para migrar")

    for plan in plans:
        logger.info(f"\n🔵 Migrando plano: {plan.name} (slug: {plan.slug})")

        # 1. Migrar FEATURES (JSONB → rows)
        features = plan.features or {}
        logger.info(f"  ✓ {len(features)} features encontradas")

        for feature_key, feature_value in features.items():
            # Verificar se já existe
            stmt = select(PlanEntitlement).where(
                PlanEntitlement.plan_id == plan.id,
                PlanEntitlement.entitlement_key == feature_key
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"    ⚠️  {feature_key} já existe, pulando...")
                continue

            # Inferir categoria
            if feature_key in ["calendar_enabled", "templates_enabled", "notes_enabled", "attachments_enabled"]:
                category = EntitlementCategory.CORE
            elif feature_key in ["ai_guard_enabled", "reengagement_enabled", "knowledge_base_enabled"]:
                category = EntitlementCategory.ENTERPRISE
            elif feature_key.startswith("security_"):
                category = EntitlementCategory.SECURITY
            else:
                category = EntitlementCategory.ADVANCED

            # Criar nome legível
            name = feature_key.replace("_enabled", "").replace("_", " ").title()

            entitlement = PlanEntitlement(
                plan_id=plan.id,
                entitlement_type=EntitlementType.FEATURE,
                entitlement_key=feature_key,
                entitlement_value={"included": bool(feature_value)},
                name=name,
                description=f"Feature {name}",
                category=category
            )
            session.add(entitlement)
            logger.info(f"    ✅ Criado: {feature_key} = {feature_value}")

        # 2. Migrar LIMITS (JSONB → rows)
        limits = plan.limits or {}
        logger.info(f"  ✓ {len(limits)} limites encontrados")

        for limit_key, limit_value in limits.items():
            # Verificar se já existe
            stmt = select(PlanEntitlement).where(
                PlanEntitlement.plan_id == plan.id,
                PlanEntitlement.entitlement_key == limit_key
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"    ⚠️  {limit_key} já existe, pulando...")
                continue

            # Criar nome legível
            name = limit_key.replace("_per_", " por ").replace("_", " ").title()

            entitlement = PlanEntitlement(
                plan_id=plan.id,
                entitlement_type=EntitlementType.LIMIT,
                entitlement_key=limit_key,
                entitlement_value={"max": int(limit_value)},
                name=name,
                description=f"Limite de {name}",
                category=EntitlementCategory.LIMIT
            )
            session.add(entitlement)
            logger.info(f"    ✅ Criado: {limit_key} = {limit_value}")

    await session.commit()
    logger.info("\n✅ FASE 1 COMPLETA: Plan entitlements migrados")


async def migrate_feature_flags(session: AsyncSession):
    """
    Migra tenant.settings.team_features → feature_flags.
    """
    logger.info("\n" + "=" * 80)
    logger.info("FASE 2: Migrando tenant.settings.team_features → feature_flags")
    logger.info("=" * 80)

    # Buscar todos os tenants
    result = await session.execute(select(Tenant))
    tenants = result.scalars().all()

    logger.info(f"📦 Encontrados {len(tenants)} tenants para migrar")

    # Buscar primeiro admin de cada tenant para usar como changed_by
    total_migrated = 0

    for tenant in tenants:
        settings = tenant.settings or {}
        team_features = settings.get("team_features", {})

        if not team_features:
            logger.info(f"  ⚠️  Tenant {tenant.name} (ID {tenant.id}) não tem team_features, pulando...")
            continue

        logger.info(f"\n🟢 Migrando tenant: {tenant.name} (ID: {tenant.id})")
        logger.info(f"  ✓ {len(team_features)} flags encontrados")

        # Buscar primeiro admin/gestor do tenant
        stmt = select(User).where(
            User.tenant_id == tenant.id,
            User.role.in_(["admin", "gestor"])
        ).limit(1)
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            # Fallback: buscar qualquer usuário
            stmt = select(User).where(User.tenant_id == tenant.id).limit(1)
            result = await session.execute(stmt)
            admin_user = result.scalar_one_or_none()

        if not admin_user:
            logger.warning(f"    ⚠️  Nenhum usuário encontrado para tenant {tenant.id}, criando flags sem owner")
            changed_by_id = 1  # Fallback para superadmin
        else:
            changed_by_id = admin_user.id

        for flag_key, flag_value in team_features.items():
            # Verificar se já existe
            stmt = select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant.id,
                FeatureFlag.flag_key == flag_key
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"    ⚠️  {flag_key} já existe, atualizando...")
                existing.is_enabled = bool(flag_value)
                existing.last_changed_by_id = changed_by_id
                continue

            # Criar flag
            flag = FeatureFlag(
                tenant_id=tenant.id,
                flag_key=flag_key,
                is_enabled=bool(flag_value),
                last_changed_by_id=changed_by_id
            )
            session.add(flag)
            total_migrated += 1
            logger.info(f"    ✅ Criado: {flag_key} = {flag_value}")

    await session.commit()
    logger.info(f"\n✅ FASE 2 COMPLETA: {total_migrated} feature flags migrados")


async def migrate_subscription_overrides(session: AsyncSession):
    """
    Migra tenant.settings.feature_overrides → subscription_overrides.
    """
    logger.info("\n" + "=" * 80)
    logger.info("FASE 3: Migrando tenant.settings.feature_overrides → subscription_overrides")
    logger.info("=" * 80)

    # Buscar todos os tenants com overrides
    result = await session.execute(select(Tenant))
    tenants = result.scalars().all()

    # Buscar superadmin para usar como created_by
    stmt = select(User).where(User.role == "superadmin").limit(1)
    result = await session.execute(stmt)
    superadmin = result.scalar_one_or_none()

    if not superadmin:
        logger.warning("⚠️  Superadmin não encontrado, usando ID 1 como fallback")
        created_by_id = 1
    else:
        created_by_id = superadmin.id

    total_migrated = 0

    for tenant in tenants:
        settings = tenant.settings or {}
        feature_overrides = settings.get("feature_overrides", {})

        if not feature_overrides:
            continue

        logger.info(f"\n🔴 Migrando overrides do tenant: {tenant.name} (ID: {tenant.id})")
        logger.info(f"  ✓ {len(feature_overrides)} overrides encontrados")

        # Buscar subscription do tenant
        stmt = select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant.id
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"    ⚠️  Subscription não encontrada para tenant {tenant.id}, pulando...")
            continue

        for override_key, override_value in feature_overrides.items():
            # Verificar se já existe
            stmt = select(SubscriptionOverride).where(
                SubscriptionOverride.subscription_id == subscription.id,
                SubscriptionOverride.override_key == override_key
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"    ⚠️  {override_key} já existe, atualizando...")
                existing.override_value = {"included": bool(override_value)}
                continue

            # Criar override
            override = SubscriptionOverride(
                subscription_id=subscription.id,
                override_key=override_key,
                override_type="feature",
                override_value={"included": bool(override_value)},
                created_by_id=created_by_id,
                reason="Migrado de tenant.settings.feature_overrides"
            )
            session.add(override)
            total_migrated += 1
            logger.info(f"    ✅ Criado: {override_key} = {override_value}")

    await session.commit()
    logger.info(f"\n✅ FASE 3 COMPLETA: {total_migrated} subscription overrides migrados")


async def main():
    """Execute migration."""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 MIGRAÇÃO DE DADOS - ENTITLEMENTS V2")
    logger.info("=" * 80)
    logger.info("\nEste script migra dados de JSONB → tabelas normalizadas")
    logger.info("Execute APENAS UMA VEZ após criar as tabelas!\n")

    async with async_session() as session:
        try:
            # Fase 1: Plan entitlements
            await migrate_plan_entitlements(session)

            # Fase 2: Feature flags
            await migrate_feature_flags(session)

            # Fase 3: Subscription overrides
            await migrate_subscription_overrides(session)

            logger.info("\n" + "=" * 80)
            logger.info("✅ MIGRAÇÃO COMPLETA!")
            logger.info("=" * 80)
            logger.info("\nPróximos passos:")
            logger.info("1. Verificar dados migrados no banco")
            logger.info("2. Testar API v2 (GET /api/v2/settings/entitlements)")
            logger.info("3. Validar que sistema continua funcionando")
            logger.info("4. Quando validado, pode remover JSONB antigos\n")

        except Exception as e:
            logger.error(f"\n❌ ERRO NA MIGRAÇÃO: {e}", exc_info=True)
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
