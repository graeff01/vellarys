"""
Entitlement Resolution Service

Resolve entitlements para um tenant (Plan + Overrides).
Parte da nova arquitetura de permissões.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.domain.entities.tenant_subscription import TenantSubscription
from src.domain.entities.plan import Plan
from src.domain.entities.plan_entitlement import PlanEntitlement, EntitlementType
from src.domain.entities.subscription_override import SubscriptionOverride


@dataclass
class ResolvedEntitlements:
    """Resultado da resolução de entitlements."""
    features: Dict[str, bool]  # Features qualitativas
    limits: Dict[str, int]     # Limites quantitativos
    source: Dict[str, str]     # De onde veio cada entitlement ("plan" | "override")


class EntitlementResolver:
    """
    Resolve entitlements para um tenant (Plan + Overrides).

    Ordem de precedência:
    1. Plan base entitlements
    2. Subscription overrides (SuperAdmin)
    3. Expired overrides são ignorados (a menos que include_expired=True)

    Examples:
        resolver = EntitlementResolver(db)
        entitlements = await resolver.resolve_for_tenant(tenant_id=5)

        if entitlements.features.get("calendar_enabled"):
            print("Tenant pode usar calendário")

        max_leads = entitlements.limits.get("leads_per_month", 0)
        print(f"Limite de leads: {max_leads}")
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_for_tenant(
        self,
        tenant_id: int,
        include_expired_overrides: bool = False
    ) -> ResolvedEntitlements:
        """
        Resolve entitlements finais para um tenant.

        Args:
            tenant_id: ID do tenant
            include_expired_overrides: Se deve incluir overrides expirados

        Returns:
            ResolvedEntitlements com features, limits e source
        """

        # 1. Buscar subscription ativa com eager loading
        stmt = select(TenantSubscription)\
            .options(
                selectinload(TenantSubscription.plan)
                    .selectinload(Plan.entitlements),
                selectinload(TenantSubscription.overrides)
            )\
            .where(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status.in_(["active", "trial", "past_due"])
            )

        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription or not subscription.plan:
            # Fallback para entitlements mínimos (starter)
            return self._get_starter_entitlements()

        # 2. Carregar entitlements do plano
        plan = subscription.plan

        # Se plan tem entitlements (nova estrutura), usa
        if plan.entitlements:
            plan_features = plan.features_v2
            plan_limits = plan.limits_v2
        else:
            # Fallback para JSONB antigo
            plan_features = plan.features or {}
            plan_limits = plan.limits or {}

        # 3. Aplicar overrides (se existirem)
        features = dict(plan_features)
        limits = dict(plan_limits)
        source = {k: "plan" for k in features.keys()}
        source.update({k: "plan" for k in limits.keys()})

        if subscription.overrides:
            for override in subscription.overrides:
                # Ignorar overrides expirados
                if override.is_expired and not include_expired_overrides:
                    continue

                if override.is_feature_override:
                    key = override.override_key
                    features[key] = override.is_enabled
                    source[key] = "override"

                elif override.is_limit_override:
                    key = override.override_key
                    max_val = override.max_value
                    if max_val is not None:
                        limits[key] = max_val
                        source[key] = "override"

        return ResolvedEntitlements(
            features=features,
            limits=limits,
            source=source
        )

    async def can_use_feature(
        self,
        tenant_id: int,
        feature_key: str
    ) -> bool:
        """
        Verifica se tenant pode usar uma feature específica.

        Args:
            tenant_id: ID do tenant
            feature_key: Key da feature (ex: "calendar_enabled")

        Returns:
            True se pode usar, False caso contrário
        """
        entitlements = await self.resolve_for_tenant(tenant_id)
        return entitlements.features.get(feature_key, False)

    async def get_limit(
        self,
        tenant_id: int,
        limit_key: str,
        default: int = 0
    ) -> int:
        """
        Retorna limite específico de um tenant.

        Args:
            tenant_id: ID do tenant
            limit_key: Key do limite (ex: "leads_per_month")
            default: Valor padrão se não encontrado

        Returns:
            Valor do limite
        """
        entitlements = await self.resolve_for_tenant(tenant_id)
        return entitlements.limits.get(limit_key, default)

    def _get_starter_entitlements(self) -> ResolvedEntitlements:
        """
        Fallback mínimo quando não há subscription.

        Retorna entitlements básicos do plano starter.
        """
        return ResolvedEntitlements(
            features={
                # Core básico
                "inbox_enabled": True,
                "leads_enabled": True,
                "notes_enabled": True,
                "attachments_enabled": True,
                "calendar_enabled": True,
                "templates_enabled": True,

                # Comunicação básica
                "sse_enabled": True,
                "search_enabled": True,

                # Avançado desabilitado
                "metrics_enabled": False,
                "archive_enabled": False,
                "voice_response_enabled": False,
                "ai_auto_handoff_enabled": False,
                "ai_sentiment_alerts_enabled": False,

                # Security
                "security_ghost_mode_enabled": False,
                "security_export_lock_enabled": False,  # Desbloqueado
                "distrib_auto_assign_enabled": False,

                # Experimental
                "ai_guard_enabled": False,
                "reengagement_enabled": False,
                "knowledge_base_enabled": False,

                # Inteligência (Gestor) - RESTAURADO
                "copilot_enabled": False,  # Apenas Premium/Enterprise
                "simulator_enabled": True,  # TODOS os planos
                "reports_enabled": True,    # TODOS os planos
                "export_enabled": True,      # TODOS os planos
            },
            limits={
                "leads_per_month": 50,
                "messages_per_month": 500,
                "sellers": 2,
                "ai_tokens_per_month": 10000,
            },
            source={}
        )
