"""
Access Decision Engine

Engine central que combina entitlements, flags e permissions.
Parte da nova arquitetura de permissões.
"""

from dataclasses import dataclass
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import User
from src.domain.entities.enums import UserRole

from .entitlements import EntitlementResolver, ResolvedEntitlements
from .feature_flags import FeatureFlagService
from .permissions import PermissionService


@dataclass
class AccessDecision:
    """
    Decisão de acesso com contexto completo.

    Attributes:
        allowed: Se o acesso é permitido
        reason: Motivo ("allowed" | "not_entitled_by_plan" | "flag_disabled_by_manager" | "role_insufficient")
        entitled: Se o plano oferece a feature
        flag_active: Se o flag está ativo
        role_permitted: Se o role tem permissão
    """
    allowed: bool
    reason: str
    entitled: bool
    flag_active: bool
    role_permitted: bool


class AccessDecisionEngine:
    """
    Engine central que combina entitlements, flags e permissions.

    Fluxo de decisão:
    1. Resolve entitlements (plano + overrides)
    2. Busca feature flags (gestor toggles)
    3. Verifica permissions (RBAC)
    4. Retorna decisão final com contexto

    Examples:
        # Inicializar
        engine = AccessDecisionEngine(
            db=db,
            entitlement_resolver=EntitlementResolver(db),
            flag_service=FeatureFlagService(db),
            permission_service=PermissionService()
        )

        # Decidir acesso
        decision = await engine.can_access_feature(
            tenant_id=5,
            user=user,
            feature_key="calendar_enabled"
        )

        if decision.allowed:
            # Acesso permitido
            pass
        else:
            # Acesso negado
            # decision.reason = "not_entitled_by_plan" | "flag_disabled_by_manager" | etc
            # decision.entitled = True/False
            # decision.flag_active = True/False
            # decision.role_permitted = True/False
    """

    def __init__(
        self,
        db: AsyncSession,
        entitlement_resolver: EntitlementResolver = None,
        flag_service: FeatureFlagService = None,
        permission_service: PermissionService = None
    ):
        self.db = db
        self.entitlement_resolver = entitlement_resolver or EntitlementResolver(db)
        self.flag_service = flag_service or FeatureFlagService(db)
        self.permission_service = permission_service or PermissionService()

    async def can_access_feature(
        self,
        tenant_id: int,
        user: User,
        feature_key: str
    ) -> AccessDecision:
        """
        Decide se usuário pode acessar feature.

        Args:
            tenant_id: ID do tenant
            user: Usuário
            feature_key: Key da feature (ex: "calendar_enabled")

        Returns:
            AccessDecision com contexto completo
        """

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN.value or user.role == UserRole.SUPERADMIN:
            return AccessDecision(
                allowed=True,
                reason="superadmin_bypass",
                entitled=True,
                flag_active=True,
                role_permitted=True
            )

        # 1. Resolve entitlements (plano + overrides)
        entitlements = await self.entitlement_resolver.resolve_for_tenant(tenant_id)
        entitled = entitlements.features.get(feature_key, False)

        # 2. Check flag (gestor toggle)
        flags = await self.flag_service.get_flags(tenant_id)
        flag_active = flags.get(feature_key, True)  # Default true se não configurado

        # 3. Check role permission
        role_permitted, role_reason = self.permission_service.can_access_feature(
            user, feature_key, entitlements, flags
        )

        # Decision
        if not entitled:
            return AccessDecision(
                allowed=False,
                reason="not_entitled_by_plan",
                entitled=False,
                flag_active=flag_active,
                role_permitted=role_permitted
            )

        if not flag_active:
            return AccessDecision(
                allowed=False,
                reason="flag_disabled_by_manager",
                entitled=True,
                flag_active=False,
                role_permitted=role_permitted
            )

        if not role_permitted:
            return AccessDecision(
                allowed=False,
                reason=role_reason,
                entitled=True,
                flag_active=True,
                role_permitted=False
            )

        return AccessDecision(
            allowed=True,
            reason="allowed",
            entitled=True,
            flag_active=True,
            role_permitted=True
        )

    async def resolve_all_features(
        self,
        tenant_id: int,
        user: User
    ) -> Dict[str, AccessDecision]:
        """
        Resolve acesso para TODAS as features de uma vez.

        Útil para popular o FeaturesContext no frontend.

        Args:
            tenant_id: ID do tenant
            user: Usuário

        Returns:
            dict: {feature_key: AccessDecision}
        """

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN.value or user.role == UserRole.SUPERADMIN:
            # Retornar todas as features como allowed
            entitlements = await self.entitlement_resolver.resolve_for_tenant(tenant_id)
            return {
                key: AccessDecision(
                    allowed=True,
                    reason="superadmin_bypass",
                    entitled=True,
                    flag_active=True,
                    role_permitted=True
                )
                for key in entitlements.features.keys()
            }

        # Resolve para cada feature
        entitlements = await self.entitlement_resolver.resolve_for_tenant(tenant_id)
        flags = await self.flag_service.get_flags(tenant_id)

        decisions = {}
        for feature_key in entitlements.features.keys():
            decisions[feature_key] = await self.can_access_feature(
                tenant_id=tenant_id,
                user=user,
                feature_key=feature_key
            )

        return decisions

    async def get_entitlements(self, tenant_id: int) -> ResolvedEntitlements:
        """
        Retorna entitlements resolvidos (plano + overrides).

        Args:
            tenant_id: ID do tenant

        Returns:
            ResolvedEntitlements
        """
        return await self.entitlement_resolver.resolve_for_tenant(tenant_id)

    async def get_flags(self, tenant_id: int) -> Dict[str, bool]:
        """
        Retorna feature flags (gestor toggles).

        Args:
            tenant_id: ID do tenant

        Returns:
            dict: {flag_key: is_enabled}
        """
        return await self.flag_service.get_flags(tenant_id)
