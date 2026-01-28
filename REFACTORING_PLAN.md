# 🏗️ PLANO DE REFATORAÇÃO DEFINITIVA: PERMISSÕES E PLANOS - VELLARYS

**Versão:** 2.0
**Data:** 2026-01-28
**Status:** PROPOSTA
**Autor:** Claude Code

---

## 📋 ÍNDICE

1. [Diagnóstico Consolidado](#diagnóstico-consolidado)
2. [Modelo de Referência (Mercado)](#modelo-de-referência-mercado)
3. [Arquitetura Proposta](#arquitetura-proposta)
4. [Migration Path](#migration-path)
5. [Implementation Plan](#implementation-plan)
6. [Acceptance Criteria](#acceptance-criteria)

---

## 🔍 DIAGNÓSTICO CONSOLIDADO

### Problemas Críticos Identificados

#### 🔴 P0 - CRÍTICOS (Bloqueiam escala)

1. **Fonte de Verdade Duplicada**
   - Features definidas em DB (`Plan.features`) E hardcoded (`PLAN_FEATURES`)
   - Risco de inconsistência catastrófica
   - Impacto: Todo sistema de permissões

2. **Semântica Invertida (Security Locks)**
   - `security_export_lock_enabled: true` = BLOQUEADO (contraintuitivo)
   - Confunde desenvolvedores e gera bugs
   - Impacto: Segurança e UX

3. **Validação Incompleta (Gestor Override)**
   - Gestor pode tentar alterar `feature_overrides` (deveria ser SuperAdmin-only)
   - Não valida dependências entre features
   - Impacto: Integridade do sistema

#### 🟡 P1 - ALTOS (Dívida técnica pesada)

4. **Role como String (não Enum)**
   - `user.role = "admin"` permite valores inválidos
   - Sem constraint de banco
   - Impacto: Type safety e bugs silenciosos

5. **Permissões Inconsistentes**
   - `UserRole.ADMIN` vs `"admin"` vs `"gestor"` misturado
   - Cada endpoint tem lógica própria
   - Impacto: Manutenibilidade

6. **Limites vs Features (conceitos misturados)**
   - `leads_per_month` (quantitativo) no mesmo nível que `calendar_enabled` (qualitativo)
   - Sem separação clara
   - Impacto: Lógica de billing

#### 🟠 P2 - MÉDIOS (funciona mas frágil)

7. **Trial Expirado sem Lógica**
   - `is_trial_expired()` existe mas não é usado em `/settings/features`
   - Cliente trial expirado vê features erradas
   - Impacto: Monetização

8. **Soft Delete não Enforçado**
   - `Tenant.active = False` não bloqueia endpoints
   - Tenant cancelado pode continuar usando
   - Impacto: Billing e auditoria

9. **custom_limits sem Validação**
   - SuperAdmin pode setar `-999` ou `"unlimited"` (string)
   - Quebra aplicação silenciosamente
   - Impacto: Estabilidade

---

## 🎯 MODELO DE REFERÊNCIA (MERCADO)

### Padrão: **Entitlements-Based Access Control (EBAC)**

Usado por: **Stripe Billing, AWS Organizations, LaunchDarkly, Split.io**

#### Conceitos Fundamentais

```
Plan (Oferta) → Define ENTITLEMENTS (direitos)
    ↓
Subscription (Contrato) → Associa Tenant ao Plan
    ↓
Entitlements (Resolvidos) → O que o tenant PODE usar
    ↓
Feature Flags (Toggles) → O que está ATIVO no momento
    ↓
User Permission (RBAC) → Quem ACESSA cada recurso
```

#### Exemplo: Stripe Billing

```json
// PLAN (produto/oferta)
{
  "id": "plan_premium",
  "name": "Premium Plan",
  "entitlements": {
    "features": {
      "calendar": { "included": true },
      "metrics": { "included": true },
      "copilot": { "included": false }
    },
    "limits": {
      "leads_per_month": { "max": 1000 },
      "messages_per_month": { "max": 10000 }
    }
  }
}

// SUBSCRIPTION (contrato ativo)
{
  "id": "sub_abc123",
  "customer_id": "tenant_5",
  "plan_id": "plan_premium",
  "status": "active",
  "current_period_start": "2026-01-01",
  "current_period_end": "2026-02-01",
  "overrides": {
    "features": {
      "copilot": { "included": true }  // Admin override
    }
  }
}

// RESOLVED ENTITLEMENTS (runtime)
{
  "tenant_id": 5,
  "features": {
    "calendar": true,   // do plano
    "metrics": true,    // do plano
    "copilot": true     // override
  },
  "limits": {
    "leads_per_month": 1000,
    "messages_per_month": 10000
  }
}

// FEATURE FLAGS (toggles operacionais)
{
  "tenant_id": 5,
  "flags": {
    "calendar_active": false,  // Gestor desativou
    "metrics_active": true,    // Gestor ativou
    "copilot_active": true     // Gestor ativou
  }
}

// FINAL RESOLUTION (o que o usuário vê)
function canUseFeature(tenant, feature, user) {
  // 1. Check entitlement (pode usar?)
  const entitled = tenant.entitlements.features[feature]
  if (!entitled) return false

  // 2. Check flag (está ativo?)
  const flagActive = tenant.flags[`${feature}_active`]
  if (!flagActive) return false

  // 3. Check permission (usuário tem acesso?)
  const hasPermission = user.permissions.includes(feature)
  if (!hasPermission) return false

  return true
}
```

#### Vantagens

1. **Separação de Conceitos**
   - Entitlement (plano) ≠ Feature Flag (toggle operacional)
   - Limites (quantitativo) ≠ Features (qualitativo)
   - Permissão (RBAC) ≠ Disponibilidade (plano)

2. **Auditabilidade**
   - Toda mudança é logada
   - Histórico de overrides
   - Compliance

3. **Escalabilidade**
   - Adicionar novo plano = criar entitlements
   - Adicionar nova feature = adicionar entitlement key
   - Zero código custom

4. **Testabilidade**
   - Entitlement resolver = função pura
   - Feature flags = toggles independentes
   - Permissões = policy engine isolada

---

## 🏛️ ARQUITETURA PROPOSTA

### Estrutura de Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│  - Frontend Components (FeatureGate)                            │
│  - API Endpoints (FastAPI routers)                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PERMISSION LAYER (NOVO)                       │
│  - PermissionService (RBAC)                                     │
│  - EntitlementResolver (Plan + Overrides)                       │
│  - FeatureFlagService (Toggles operacionais)                    │
│  - AccessDecisionEngine (combina tudo)                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER                                  │
│  - Tenant, Plan, TenantSubscription (entities)                  │
│  - Entitlement (value object - NOVO)                            │
│  - FeatureFlag (entity - NOVO)                                  │
│  - AuditLog (entity)                                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                             │
│  - PostgreSQL (Entities)                                        │
│  - Redis (Feature Flags cache - opcional)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Nova Modelagem de Dados

#### 1. Entitlements (Nova Tabela)

```python
class PlanEntitlement(Base, TimestampMixin):
    """Define o que um plano OFERECE (pode usar)."""
    __tablename__ = "plan_entitlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))

    # Tipo de entitlement
    entitlement_type: Mapped[str] = mapped_column(String(50))  # "feature" | "limit" | "addon"

    # Key única (ex: "calendar", "leads_per_month")
    entitlement_key: Mapped[str] = mapped_column(String(100), index=True)

    # Valor (JSONB flexível)
    entitlement_value: Mapped[dict] = mapped_column(JSONB)
    # Exemplos:
    # {"included": true, "max_users": null}  # Feature ilimitada
    # {"included": true, "max_users": 5}     # Feature limitada
    # {"max": 1000, "unit": "per_month"}     # Limit quantitativo

    # Metadata
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))  # "core" | "advanced" | "enterprise"

    # Relacionamento
    plan: Mapped["Plan"] = relationship(back_populates="entitlements")

    __table_args__ = (
        UniqueConstraint('plan_id', 'entitlement_key', name='uq_plan_entitlement'),
    )


class Plan(Base, TimestampMixin):
    """Plano de assinatura."""
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))

    # ❌ REMOVER: features e limits de JSONB
    # ✅ USAR: relacionamento com PlanEntitlement
    entitlements: Mapped[list["PlanEntitlement"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    # Helper methods
    def get_entitlements_by_type(self, etype: str) -> dict:
        """Retorna entitlements de um tipo específico."""
        return {
            e.entitlement_key: e.entitlement_value
            for e in self.entitlements
            if e.entitlement_type == etype
        }

    @property
    def features(self) -> dict:
        """Features como dict {key: bool}."""
        return {
            k: v.get("included", False)
            for k, v in self.get_entitlements_by_type("feature").items()
        }

    @property
    def limits(self) -> dict:
        """Limits como dict {key: int}."""
        return {
            k: v.get("max", 0)
            for k, v in self.get_entitlements_by_type("limit").items()
        }
```

#### 2. Subscription Overrides (Nova Tabela)

```python
class SubscriptionOverride(Base, TimestampMixin):
    """Overrides por subscription (SuperAdmin customizações)."""
    __tablename__ = "subscription_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("tenant_subscriptions.id", ondelete="CASCADE")
    )

    # Override key (mesma nomenclatura dos entitlements)
    override_key: Mapped[str] = mapped_column(String(100), index=True)
    override_type: Mapped[str] = mapped_column(String(50))  # "feature" | "limit"

    # Valor do override
    override_value: Mapped[dict] = mapped_column(JSONB)
    # Exemplos:
    # {"included": true}  # Ativa feature não incluída no plano
    # {"included": false} # Desativa feature incluída no plano
    # {"max": 5000}       # Override de limite

    # Auditoria
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relacionamentos
    subscription: Mapped["TenantSubscription"] = relationship(back_populates="overrides")
    created_by: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint('subscription_id', 'override_key', name='uq_subscription_override'),
    )
```

#### 3. Feature Flags (Nova Tabela)

```python
class FeatureFlag(Base, TimestampMixin):
    """Feature flags operacionais (Gestor ativa/desativa)."""
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))

    # Flag key (ex: "calendar", "metrics")
    flag_key: Mapped[str] = mapped_column(String(100), index=True)

    # Estado atual
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Auditoria
    last_changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    last_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    last_changed_by: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint('tenant_id', 'flag_key', name='uq_tenant_feature_flag'),
    )
```

#### 4. Audit Log (Nova Tabela)

```python
class FeatureAuditLog(Base, TimestampMixin):
    """Log de todas as mudanças em features."""
    __tablename__ = "feature_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))

    # O que mudou
    change_type: Mapped[str] = mapped_column(String(50))  # "override" | "flag" | "plan_change"
    entity_type: Mapped[str] = mapped_column(String(50))  # "feature" | "limit"
    entity_key: Mapped[str] = mapped_column(String(100))

    # Valores
    old_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Contexto
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    changed_by: Mapped["User"] = relationship()
```

#### 5. User Permissions (Atualizar Tabela)

```python
class User(Base, TimestampMixin):
    """Usuário do sistema."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))

    # ✅ USAR ENUM COM CONSTRAINT
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),  # ← DB constraint
        nullable=False,
        default=UserRole.USER
    )

    # Permissions específicas (além do role)
    # Ex: Vendedor pode ter permissão especial para metrics
    custom_permissions: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # {"features": ["metrics", "export"], "actions": ["create_lead"]}

    # ... resto igual
```

---

### Nova Camada de Serviços

#### 1. EntitlementResolver

```python
# backend/src/services/entitlements.py

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

@dataclass
class ResolvedEntitlements:
    """Resultado da resolução de entitlements."""
    features: dict[str, bool]
    limits: dict[str, int]
    source: dict[str, str]  # {key: "plan" | "override"}


class EntitlementResolver:
    """Resolve entitlements para um tenant (Plan + Overrides)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_for_tenant(
        self,
        tenant_id: int,
        include_expired_overrides: bool = False
    ) -> ResolvedEntitlements:
        """
        Resolve entitlements finais para um tenant.

        Ordem de precedência:
        1. Plan base entitlements
        2. Subscription overrides (SuperAdmin)
        3. Expired overrides são ignorados (a menos que include_expired=True)
        """

        # 1. Buscar subscription ativa
        stmt = select(TenantSubscription)\
            .options(
                selectinload(TenantSubscription.plan)\
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
            # Fallback para plano starter
            return self._get_starter_entitlements()

        # 2. Carregar entitlements do plano
        plan_features = subscription.plan.features
        plan_limits = subscription.plan.limits

        # 3. Aplicar overrides
        features = dict(plan_features)
        limits = dict(plan_limits)
        source = {k: "plan" for k in features.keys()}
        source.update({k: "plan" for k in limits.keys()})

        for override in subscription.overrides:
            # Ignorar overrides expirados
            if override.expires_at and override.expires_at < datetime.now(timezone.utc):
                if not include_expired_overrides:
                    continue

            if override.override_type == "feature":
                key = override.override_key
                features[key] = override.override_value.get("included", False)
                source[key] = "override"

            elif override.override_type == "limit":
                key = override.override_key
                limits[key] = override.override_value.get("max", 0)
                source[key] = "override"

        return ResolvedEntitlements(
            features=features,
            limits=limits,
            source=source
        )

    def _get_starter_entitlements(self) -> ResolvedEntitlements:
        """Fallback mínimo quando não há subscription."""
        return ResolvedEntitlements(
            features={
                "inbox_enabled": True,
                "leads_enabled": True,
                "notes_enabled": True,
            },
            limits={
                "leads_per_month": 50,
                "messages_per_month": 500,
            },
            source={}
        )
```

#### 2. FeatureFlagService

```python
# backend/src/services/feature_flags.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.domain.entities.feature_flag import FeatureFlag

class FeatureFlagService:
    """Gerencia feature flags operacionais (toggles do Gestor)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_flags(self, tenant_id: int) -> dict[str, bool]:
        """Retorna todos os flags ativos do tenant."""
        stmt = select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        flags = result.scalars().all()

        return {flag.flag_key: flag.is_enabled for flag in flags}

    async def set_flag(
        self,
        tenant_id: int,
        flag_key: str,
        is_enabled: bool,
        changed_by_id: int
    ) -> FeatureFlag:
        """Ativa/desativa um flag."""

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
                last_changed_by_id=changed_by_id
            )
            self.db.add(flag)

        # Audit log
        audit = FeatureAuditLog(
            tenant_id=tenant_id,
            change_type="flag",
            entity_type="feature",
            entity_key=flag_key,
            old_value={"enabled": old_value} if old_value is not None else None,
            new_value={"enabled": is_enabled},
            changed_by_id=changed_by_id
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(flag)

        return flag

    async def bulk_set_flags(
        self,
        tenant_id: int,
        flags: dict[str, bool],
        changed_by_id: int
    ):
        """Atualiza múltiplos flags de uma vez."""
        for key, value in flags.items():
            await self.set_flag(tenant_id, key, value, changed_by_id)
```

#### 3. PermissionService (RBAC)

```python
# backend/src/services/permissions.py

from src.domain.entities.enums import UserRole

class PermissionService:
    """RBAC - Define o que cada role pode acessar."""

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
            ],
        },
        UserRole.MANAGER: {
            "actions": [
                "manage_features",  # Pode ativar/desativar flags
                "view_all_leads",
                "view_metrics",
                "manage_sellers",
            ],
        },
        UserRole.USER: {
            "actions": [
                "view_own_leads",
                "create_lead",
                "send_message",
            ],
        },
        UserRole.SELLER: {
            "actions": [
                "view_own_leads",
                "send_message",
            ],
        },
    }

    def can_perform_action(self, user: User, action: str) -> bool:
        """Verifica se usuário pode executar ação."""

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN:
            return True

        # Permissões do role
        role_perms = self.ROLE_PERMISSIONS.get(user.role, {})
        allowed_actions = role_perms.get("actions", [])

        if "*" in allowed_actions or action in allowed_actions:
            return True

        # Permissões customizadas do usuário
        custom_perms = user.custom_permissions or {}
        custom_actions = custom_perms.get("actions", [])

        return action in custom_actions

    def can_access_feature(
        self,
        user: User,
        feature_key: str,
        entitlements: ResolvedEntitlements,
        flags: dict[str, bool]
    ) -> tuple[bool, str]:
        """
        Verifica acesso completo a uma feature.

        Returns:
            (can_access, reason)
        """

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN:
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
        # (algumas features são restritas por role)
        feature_role_requirements = {
            "metrics": [UserRole.ADMIN, UserRole.MANAGER],
            "export": [UserRole.ADMIN, UserRole.MANAGER],
            "manage_settings": [UserRole.ADMIN],
        }

        required_roles = feature_role_requirements.get(feature_key)
        if required_roles and user.role not in required_roles:
            return (False, "role_insufficient")

        return (True, "allowed")
```

#### 4. AccessDecisionEngine

```python
# backend/src/services/access_decision.py

from dataclasses import dataclass

@dataclass
class AccessDecision:
    """Decisão de acesso com contexto."""
    allowed: bool
    reason: str
    entitled: bool  # Plano permite?
    flag_active: bool  # Flag ativo?
    role_permitted: bool  # Role tem permissão?


class AccessDecisionEngine:
    """Engine central que combina entitlements, flags e permissions."""

    def __init__(
        self,
        entitlement_resolver: EntitlementResolver,
        flag_service: FeatureFlagService,
        permission_service: PermissionService
    ):
        self.entitlement_resolver = entitlement_resolver
        self.flag_service = flag_service
        self.permission_service = permission_service

    async def can_access_feature(
        self,
        tenant_id: int,
        user: User,
        feature_key: str
    ) -> AccessDecision:
        """Decide se usuário pode acessar feature."""

        # SuperAdmin bypass
        if user.role == UserRole.SUPERADMIN:
            return AccessDecision(
                allowed=True,
                reason="superadmin_bypass",
                entitled=True,
                flag_active=True,
                role_permitted=True
            )

        # 1. Resolve entitlements
        entitlements = await self.entitlement_resolver.resolve_for_tenant(tenant_id)
        entitled = entitlements.features.get(feature_key, False)

        # 2. Check flag
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
```

---

## 🚀 MIGRATION PATH

### Fase 1: Criar Nova Estrutura (Sem Quebrar Atual)

**Objetivo:** Adicionar novas tabelas e serviços SEM remover código antigo

**Steps:**

1. **Migration 01: Criar tabelas novas**
   ```bash
   alembic revision --autogenerate -m "add_entitlements_structure"
   ```

   Cria:
   - `plan_entitlements`
   - `subscription_overrides`
   - `feature_flags`
   - `feature_audit_logs`

2. **Migration 02: Popular plan_entitlements**
   ```python
   # Migração de dados
   # Para cada Plan existente:
   for plan in existing_plans:
       # Migrar Plan.features (JSONB) → PlanEntitlement rows
       for key, value in plan.features.items():
           entitlement = PlanEntitlement(
               plan_id=plan.id,
               entitlement_type="feature",
               entitlement_key=key,
               entitlement_value={"included": value},
               name=format_name(key),
               category=infer_category(key)
           )
           db.add(entitlement)

       # Migrar Plan.limits (JSONB) → PlanEntitlement rows
       for key, value in plan.limits.items():
           entitlement = PlanEntitlement(
               plan_id=plan.id,
               entitlement_type="limit",
               entitlement_key=key,
               entitlement_value={"max": value},
               name=format_name(key),
               category="limit"
           )
           db.add(entitlement)
   ```

3. **Migration 03: Migrar tenant.settings → feature_flags**
   ```python
   # Para cada Tenant:
   for tenant in tenants:
       team_features = tenant.settings.get("team_features", {})

       for key, enabled in team_features.items():
           flag = FeatureFlag(
               tenant_id=tenant.id,
               flag_key=key,
               is_enabled=enabled,
               last_changed_by_id=tenant.owner_id  # Ou primeiro admin
           )
           db.add(flag)
   ```

4. **Migration 04: Migrar tenant.settings.feature_overrides → subscription_overrides**
   ```python
   # Para cada Tenant com overrides:
   for tenant in tenants:
       overrides = tenant.settings.get("feature_overrides", {})
       if not overrides:
           continue

       subscription = get_subscription(tenant.id)
       if not subscription:
           continue

       for key, value in overrides.items():
           override = SubscriptionOverride(
               subscription_id=subscription.id,
               override_key=key,
               override_type="feature",
               override_value={"included": value},
               created_by_id=get_first_superadmin_id(),
               reason="Migrated from legacy settings"
           )
           db.add(override)
   ```

5. **Implementar novos serviços**
   - `EntitlementResolver`
   - `FeatureFlagService`
   - `PermissionService`
   - `AccessDecisionEngine`

6. **Criar endpoints paralelos (versão v2)**
   ```python
   # Manter v1 funcionando
   @router.get("/v1/settings/features")  # OLD
   async def get_features_v1(...):
       # Código antigo

   # Adicionar v2 com nova lógica
   @router.get("/v2/settings/features")  # NEW
   async def get_features_v2(...):
       engine = AccessDecisionEngine(...)
       entitlements = await engine.resolve_entitlements(tenant_id)
       flags = await engine.get_flags(tenant_id)
       return {"entitlements": ..., "flags": ...}
   ```

### Fase 2: Migrar Frontend (Dual Mode)

**Objetivo:** Frontend consome ambas APIs durante transição

1. **Adicionar feature flag de migração**
   ```typescript
   const USE_NEW_ENTITLEMENTS_API = process.env.NEXT_PUBLIC_USE_V2_ENTITLEMENTS === 'true'

   async function fetchFeatures() {
     if (USE_NEW_ENTITLEMENTS_API) {
       return fetchFeaturesV2()  // Nova API
     }
     return fetchFeaturesV1()    // API antiga
   }
   ```

2. **Testar v2 em staging**
   - Ativar flag em staging
   - Validar todos os fluxos
   - Corrigir bugs

3. **Rollout gradual em produção**
   - 10% dos usuários → v2
   - 50% dos usuários → v2
   - 100% dos usuários → v2

### Fase 3: Deprecar Código Antigo

**Objetivo:** Remover código legado após 100% migração

1. **Remover campos JSONB antigos**
   ```python
   # Migration: Remover
   op.drop_column('plans', 'features')
   op.drop_column('plans', 'limits')
   op.drop_column('tenants', 'settings')  # Ou limpar keys antigas
   ```

2. **Remover endpoints v1**
   ```python
   # Deletar:
   @router.get("/v1/settings/features")
   @router.patch("/v1/settings/features")
   ```

3. **Remover constante PLAN_FEATURES hardcoded**
   ```python
   # Deletar settings.py:326-428
   # PLAN_FEATURES = {...}
   ```

4. **Remover lógica antiga do FeaturesContext**
   ```typescript
   // Remover fallbacks e compatibilidade
   ```

---

## 📅 IMPLEMENTATION PLAN

### Sprint 1: Fundação (1 semana)

**Objetivo:** Criar estrutura base sem quebrar nada

- [ ] Migration: Criar 4 tabelas novas
- [ ] Models: Adicionar entities novas
- [ ] Services: Implementar `EntitlementResolver`
- [ ] Services: Implementar `FeatureFlagService`
- [ ] Migration: Popular `plan_entitlements` (dados existentes)
- [ ] Tests: Unit tests dos services

### Sprint 2: Migration de Dados (1 semana)

**Objetivo:** Mover dados de JSONB → tabelas normalizadas

- [ ] Migration: `tenant.settings.team_features` → `feature_flags`
- [ ] Migration: `tenant.settings.feature_overrides` → `subscription_overrides`
- [ ] Script: Validar integridade pós-migração
- [ ] Rollback plan: Reverter se necessário

### Sprint 3: Nova API (1 semana)

**Objetivo:** Endpoints v2 funcionando

- [ ] Endpoint: `GET /v2/settings/entitlements` (resolve entitlements)
- [ ] Endpoint: `GET /v2/settings/flags` (lista flags)
- [ ] Endpoint: `PATCH /v2/settings/flags` (atualiza flags)
- [ ] Endpoint: `POST /v2/settings/overrides` (SuperAdmin override)
- [ ] Decorator: `@require_feature` para proteger rotas
- [ ] Tests: Integration tests

### Sprint 4: Frontend Adapters (1 semana)

**Objetivo:** Frontend consome nova API em modo compatibilidade

- [ ] Adapter: `fetchFeaturesV2()`
- [ ] Context: Atualizar `FeaturesContext` para suportar ambas APIs
- [ ] Feature flag: `USE_V2_ENTITLEMENTS_API`
- [ ] Tests: E2E tests com ambas APIs

### Sprint 5: Rollout e Validação (1 semana)

**Objetivo:** 100% produção na nova API

- [ ] Staging: Ativar v2 100%
- [ ] Produção: Rollout gradual (10% → 50% → 100%)
- [ ] Monitoring: Dashboards de uso
- [ ] Rollback: Procedimento documentado

### Sprint 6: Cleanup (1 semana)

**Objetivo:** Remover código legado

- [ ] Migration: Dropar colunas JSONB antigas
- [ ] Code: Remover endpoints v1
- [ ] Code: Remover constantes hardcoded
- [ ] Docs: Atualizar documentação
- [ ] Tests: Limpar testes obsoletos

---

## ✅ ACCEPTANCE CRITERIA

### Critérios Funcionais

1. **Separação de Conceitos**
   - [ ] Entitlements (plano) separados de Feature Flags (toggles)
   - [ ] Limites quantitativos separados de features qualitativas
   - [ ] Permissões (RBAC) separadas de disponibilidade (plano)

2. **Consistência**
   - [ ] Única fonte de verdade (DB, não hardcoded)
   - [ ] Semântica clara (`export_enabled: true` = liberado)
   - [ ] Role como Enum com constraint de banco

3. **Auditabilidade**
   - [ ] Toda mudança logada em `feature_audit_logs`
   - [ ] Histórico de overrides
   - [ ] IP e user_agent capturados

4. **Validações**
   - [ ] Gestor não pode ativar feature fora do plano
   - [ ] Gestor não pode alterar overrides (SuperAdmin-only)
   - [ ] custom_limits validados (não aceita valores inválidos)
   - [ ] Trial expirado volta para Starter

5. **Performance**
   - [ ] Cache de entitlements resolvidos (Redis)
   - [ ] Queries otimizadas (eager loading)
   - [ ] < 100ms para resolver entitlements

### Critérios Não-Funcionais

6. **Segurança**
   - [ ] Soft delete enforçado (tenant.active verificado em TODOS os endpoints)
   - [ ] Vendedor não acessa API de features diretamente
   - [ ] Overrides expirados ignorados automaticamente

7. **Escalabilidade**
   - [ ] Adicionar novo plano = criar entitlements (zero código)
   - [ ] Adicionar nova feature = adicionar entitlement key
   - [ ] Suporta 10,000+ tenants simultâneos

8. **Manutenibilidade**
   - [ ] Código limpo e testável
   - [ ] Serviços isolados (injeção de dependência)
   - [ ] Documentação atualizada

---

## 📚 REFERÊNCIAS

- **Stripe Billing Entitlements:** https://stripe.com/docs/billing/subscriptions/entitlements
- **LaunchDarkly Feature Flags:** https://docs.launchdarkly.com/home/getting-started/feature-flags
- **AWS IAM Policies:** https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html
- **NIST RBAC Model:** https://csrc.nist.gov/projects/role-based-access-control

---

**Próximos Passos:**

1. **Revisar este plano com o time**
2. **Aprovar migração de dados**
3. **Definir prioridades (pode ser faseado?)**
4. **Começar Sprint 1**

---

**Changelog:**

- **2026-01-28:** Versão 2.0 - Plano completo de refatoração
- **2026-01-28:** Versão 1.0 - Análise inicial (PERMISSIONS_ARCHITECTURE.md)
