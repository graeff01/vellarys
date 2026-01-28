"""
Feature Flag Service

Gerencia feature flags operacionais (toggles do Gestor).
Parte da nova arquitetura de permissões.
"""

from typing import Dict, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities.feature_flag import FeatureFlag
from src.domain.entities.feature_audit_log import FeatureAuditLog, ChangeType


class FeatureFlagService:
    """
    Gerencia feature flags operacionais (toggles do Gestor).

    Feature flags permitem que gestores ativem/desativem features
    operacionalmente, dentro do que o plano permite.

    Examples:
        service = FeatureFlagService(db)

        # Buscar todos os flags de um tenant
        flags = await service.get_flags(tenant_id=5)
        # {"calendar_enabled": True, "metrics_enabled": False}

        # Ativar uma feature
        await service.set_flag(
            tenant_id=5,
            flag_key="calendar_enabled",
            is_enabled=True,
            changed_by_id=10,
            reason="Equipe pediu para ativar"
        )

        # Desativar várias features de uma vez
        await service.bulk_set_flags(
            tenant_id=5,
            flags={"calendar_enabled": False, "metrics_enabled": False},
            changed_by_id=10
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_flags(self, tenant_id: int) -> Dict[str, bool]:
        """
        Retorna todos os flags ativos do tenant.

        Args:
            tenant_id: ID do tenant

        Returns:
            dict: {flag_key: is_enabled}
        """
        stmt = select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        flags = result.scalars().all()

        return {flag.flag_key: flag.is_enabled for flag in flags}

    async def get_flag(
        self,
        tenant_id: int,
        flag_key: str,
        default: bool = True
    ) -> bool:
        """
        Retorna estado de um flag específico.

        Args:
            tenant_id: ID do tenant
            flag_key: Key do flag
            default: Valor padrão se não encontrado

        Returns:
            bool: Se o flag está ativo
        """
        stmt = select(FeatureFlag).where(
            FeatureFlag.tenant_id == tenant_id,
            FeatureFlag.flag_key == flag_key
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()

        if flag:
            return flag.is_enabled

        return default

    async def set_flag(
        self,
        tenant_id: int,
        flag_key: str,
        is_enabled: bool,
        changed_by_id: int,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> FeatureFlag:
        """
        Ativa/desativa um flag.

        Args:
            tenant_id: ID do tenant
            flag_key: Key do flag
            is_enabled: Novo estado
            changed_by_id: ID do usuário que alterou
            reason: Motivo da alteração (opcional)
            ip_address: IP do usuário (opcional)
            user_agent: User agent (opcional)

        Returns:
            FeatureFlag atualizado
        """

        # Buscar flag existente
        stmt = select(FeatureFlag).where(
            FeatureFlag.tenant_id == tenant_id,
            FeatureFlag.flag_key == flag_key
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()

        if flag:
            # Atualizar
            old_value = flag.is_enabled
            flag.is_enabled = is_enabled
            flag.last_changed_by_id = changed_by_id
            flag.last_changed_at = datetime.now(timezone.utc)
        else:
            # Criar
            old_value = None
            flag = FeatureFlag(
                tenant_id=tenant_id,
                flag_key=flag_key,
                is_enabled=is_enabled,
                last_changed_by_id=changed_by_id,
                last_changed_at=datetime.now(timezone.utc)
            )
            self.db.add(flag)

        # Audit log
        audit = FeatureAuditLog(
            tenant_id=tenant_id,
            change_type=ChangeType.FLAG,
            entity_type="feature",
            entity_key=flag_key,
            old_value={"enabled": old_value} if old_value is not None else None,
            new_value={"enabled": is_enabled},
            changed_by_id=changed_by_id,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(flag)

        return flag

    async def bulk_set_flags(
        self,
        tenant_id: int,
        flags: Dict[str, bool],
        changed_by_id: int,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Atualiza múltiplos flags de uma vez.

        Args:
            tenant_id: ID do tenant
            flags: dict {flag_key: is_enabled}
            changed_by_id: ID do usuário
            reason: Motivo (opcional)
            ip_address: IP (opcional)
            user_agent: User agent (opcional)
        """
        for key, value in flags.items():
            await self.set_flag(
                tenant_id=tenant_id,
                flag_key=key,
                is_enabled=value,
                changed_by_id=changed_by_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )

    async def reset_to_defaults(
        self,
        tenant_id: int,
        changed_by_id: int,
        reason: str = "Reset para padrões"
    ):
        """
        Remove todos os flags customizados (volta para padrões do plano).

        Args:
            tenant_id: ID do tenant
            changed_by_id: ID do usuário
            reason: Motivo do reset
        """
        # Buscar todos os flags
        stmt = select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        flags = result.scalars().all()

        # Deletar todos (volta para padrões)
        for flag in flags:
            # Audit log
            audit = FeatureAuditLog(
                tenant_id=tenant_id,
                change_type=ChangeType.FLAG,
                entity_type="feature",
                entity_key=flag.flag_key,
                old_value={"enabled": flag.is_enabled},
                new_value=None,  # Removido
                changed_by_id=changed_by_id,
                reason=reason
            )
            self.db.add(audit)

            await self.db.delete(flag)

        await self.db.commit()
