"""
Permission Service (RBAC)

Define o que cada role pode acessar.
Parte da nova arquitetura de permissões.
"""

from typing import Set, Tuple
from src.domain.entities.enums import UserRole
from src.domain.entities.models import User
from .entitlements import ResolvedEntitlements


class PermissionService:
    """
    RBAC - Define o que cada role pode acessar.

    Separação clara de responsabilidades:
    - Entitlements: O que o PLANO oferece
    - Feature Flags: O que está ATIVO operacionalmente
    - Permissions (RBAC): O que cada ROLE pode acessar

    Examples:
        service = PermissionService()

        # Verificar se pode executar ação
        can_export = service.can_perform_action(user, "export_data")

        # Verificar acesso completo a feature
        can_access, reason = service.can_access_feature(
            user=user,
            feature_key="metrics_enabled",
            entitlements=entitlements,
            flags=flags
        )

        if can_access:
            # Permitir acesso
        else:
            # Bloquear: reason = "not_in_plan" | "flag_disabled" | "role_insufficient"
    """

    # Permissões por role (baseado em actions, não features)
    ROLE_PERMISSIONS = {
        UserRole.SUPERADMIN: {
            "actions": ["*"],  # Tudo
        },
        UserRole.ADMIN: {
            "actions": [
                "manage_team",
                "manage_settings",
                "manage_features",
                "view_all_leads",
                "export_data",
                "view_metrics",
                "manage_sellers",
                "create_seller",
                "delete_seller",
                "manage_billing",
            ],
        },
        UserRole.MANAGER: {
            "actions": [
                "manage_features",  # Pode ativar/desativar flags
                "view_all_leads",
                "view_metrics",
                "manage_sellers",
                "create_seller",
            ],
        },
        UserRole.USER: {
            "actions": [
                "view_own_leads",
                "create_lead",
                "send_message",
                "view_own_metrics",
            ],
        },
        UserRole.SELLER: {
            "actions": [
                "view_own_leads",
                "send_message",
                "create_lead",
            ],
        },
    }

    # Features restritas por role (algumas features só para gestores)
    FEATURE_ROLE_REQUIREMENTS = {
        "metrics_enabled": [UserRole.ADMIN, UserRole.MANAGER],
        "export_enabled": [UserRole.ADMIN, UserRole.MANAGER],
        "manage_settings": [UserRole.ADMIN],
        "copilot_enabled": [UserRole.ADMIN, UserRole.MANAGER],
        "ai_guard_enabled": [UserRole.ADMIN],
    }

    def can_perform_action(self, user: User, action: str) -> bool:
        """
        Verifica se usuário pode executar ação.

        Args:
            user: Usuário
            action: Nome da ação (ex: "export_data", "manage_team")

        Returns:
            bool: Se pode executar
        """

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN.value or user.role == UserRole.SUPERADMIN:
            return True

        # Converter string para enum (compatibilidade)
        user_role = user.role
        if isinstance(user_role, str):
            try:
                user_role = UserRole(user_role)
            except ValueError:
                # Role inválido
                return False

        # Permissões do role
        role_perms = self.ROLE_PERMISSIONS.get(user_role, {})
        allowed_actions = role_perms.get("actions", [])

        if "*" in allowed_actions or action in allowed_actions:
            return True

        # Permissões customizadas do usuário (se houver)
        custom_perms = user.custom_permissions or {}
        custom_actions = custom_perms.get("actions", [])

        return action in custom_actions

    def can_access_feature(
        self,
        user: User,
        feature_key: str,
        entitlements: ResolvedEntitlements,
        flags: dict[str, bool]
    ) -> Tuple[bool, str]:
        """
        Verifica acesso completo a uma feature.

        Checa:
        1. Entitlement (plano permite?)
        2. Flag (está ativo?)
        3. Role (usuário tem permissão?)

        Args:
            user: Usuário
            feature_key: Key da feature
            entitlements: Entitlements resolvidos
            flags: Feature flags

        Returns:
            (can_access, reason)
            reason: "allowed" | "not_in_plan" | "plan_disabled" | "flag_disabled" | "role_insufficient"
        """

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN.value or user.role == UserRole.SUPERADMIN:
            return (True, "superadmin_bypass")

        # 1. Feature está nos entitlements? (plano permite?)
        if feature_key not in entitlements.features:
            return (False, "not_in_plan")

        if not entitlements.features[feature_key]:
            return (False, "plan_disabled")

        # 2. Flag está ativo? (gestor liberou?)
        if feature_key not in flags:
            # Se não tem flag explícito, assume ativo (para compatibilidade)
            flag_active = True
        else:
            flag_active = flags[feature_key]

        if not flag_active:
            return (False, "flag_disabled")

        # 3. Role tem permissão para usar essa feature?
        required_roles = self.FEATURE_ROLE_REQUIREMENTS.get(feature_key)

        if required_roles:
            # Converter string para enum
            user_role = user.role
            if isinstance(user_role, str):
                try:
                    user_role = UserRole(user_role)
                except ValueError:
                    return (False, "invalid_role")

            if user_role not in required_roles:
                return (False, "role_insufficient")

        return (True, "allowed")

    def get_allowed_features_for_role(self, role: UserRole) -> Set[str]:
        """
        Retorna features permitidas para um role específico.

        Args:
            role: Role do usuário

        Returns:
            set: Features permitidas
        """
        if role == UserRole.SUPERADMIN:
            # SuperAdmin pode tudo
            return set()  # Empty = bypass

        # Features básicas para todos
        basic_features = {
            "inbox_enabled",
            "leads_enabled",
            "notes_enabled",
            "attachments_enabled",
            "calendar_enabled",
            "templates_enabled",
            "sse_enabled",
            "search_enabled",
        }

        # Features avançadas por role
        if role in [UserRole.ADMIN, UserRole.MANAGER]:
            basic_features.update({
                "metrics_enabled",
                "archive_enabled",
                "export_enabled",
                "copilot_enabled",
            })

        if role == UserRole.ADMIN:
            basic_features.update({
                "ai_guard_enabled",
                "manage_settings",
            })

        return basic_features
