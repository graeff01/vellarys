"""
LIMITS SERVICE - Serviço de Limites
====================================

Gerencia verificação e contagem de uso por tenant.

Funcionalidades:
- Verificar se pode usar recurso
- Incrementar contadores
- Verificar status de bloqueio
- Tolerância de 10% antes de bloquear
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Tenant
from src.domain.entities.plan import Plan
from src.domain.entities.tenant_usage import TenantUsage
from src.domain.entities.tenant_subscription import TenantSubscription


# Tolerância: permite usar 10% além do limite antes de bloquear
TOLERANCE_PERCENTAGE = 10

# Alerta quando atingir 80% do limite
WARNING_THRESHOLD = 80


class LimitType:
    """Tipos de limites disponíveis."""
    LEADS = "leads_per_month"
    MESSAGES = "messages_per_month"
    SELLERS = "sellers"
    NICHES = "niches"
    AI_TOKENS = "ai_tokens_per_month"


class LimitStatus:
    """Status do limite."""
    OK = "ok"                    # Dentro do limite
    WARNING = "warning"          # Acima de 80%
    EXCEEDED = "exceeded"        # Acima de 100% mas na tolerância
    BLOCKED = "blocked"          # Acima da tolerância, bloqueado


class LimitCheckResult:
    """Resultado da verificação de limite."""
    
    def __init__(
        self,
        allowed: bool,
        status: str,
        current: int,
        limit: int,
        percentage: float,
        message: str = ""
    ):
        self.allowed = allowed
        self.status = status
        self.current = current
        self.limit = limit
        self.percentage = percentage
        self.message = message
    
    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "status": self.status,
            "current": self.current,
            "limit": self.limit,
            "percentage": self.percentage,
            "message": self.message,
        }


async def get_or_create_usage(
    db: AsyncSession,
    tenant_id: int,
    period: Optional[str] = None
) -> TenantUsage:
    """
    Obtém ou cria o registro de uso do período.
    """
    if not period:
        period = TenantUsage.get_current_period()
    
    result = await db.execute(
        select(TenantUsage).where(
            TenantUsage.tenant_id == tenant_id,
            TenantUsage.period == period
        )
    )
    usage = result.scalar_one_or_none()
    
    if not usage:
        usage = TenantUsage(
            tenant_id=tenant_id,
            period=period,
        )
        db.add(usage)
        await db.flush()
    
    return usage


async def get_subscription(
    db: AsyncSession,
    tenant_id: int
) -> Optional[TenantSubscription]:
    """
    Obtém a assinatura do tenant (sem carregar plano).
    """
    result = await db.execute(
        select(TenantSubscription)
        .where(TenantSubscription.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_subscription_with_plan(
    db: AsyncSession,
    tenant_id: int
) -> Optional[TenantSubscription]:
    """
    Obtém a assinatura do tenant COM o plano carregado.
    """
    result = await db.execute(
        select(TenantSubscription)
        .options(selectinload(TenantSubscription.plan))
        .where(TenantSubscription.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def check_limit(
    db: AsyncSession,
    tenant_id: int,
    limit_type: str,
    increment: int = 1
) -> LimitCheckResult:
    """
    Verifica se o tenant pode usar mais do recurso.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        limit_type: Tipo do limite (LimitType.LEADS, etc)
        increment: Quantidade a adicionar
        
    Returns:
        LimitCheckResult com status e detalhes
    """
    
    # Buscar assinatura (COM o plano carregado para evitar lazy loading)
    subscription = await get_subscription_with_plan(db, tenant_id)
    
    if not subscription:
        return LimitCheckResult(
            allowed=False,
            status=LimitStatus.BLOCKED,
            current=0,
            limit=0,
            percentage=0,
            message="Assinatura não encontrada"
        )
    
    # Verificar se assinatura está ativa
    if not subscription.is_active():
        return LimitCheckResult(
            allowed=False,
            status=LimitStatus.BLOCKED,
            current=0,
            limit=0,
            percentage=0,
            message="Assinatura inativa ou cancelada"
        )
    
    # Verificar trial expirado
    if subscription.is_trial() and subscription.is_trial_expired():
        return LimitCheckResult(
            allowed=False,
            status=LimitStatus.BLOCKED,
            current=0,
            limit=0,
            percentage=0,
            message="Período de teste expirado. Assine um plano para continuar."
        )
    
    # Obter limite do plano
    limit = subscription.get_limit(limit_type)
    
    # -1 significa ilimitado
    if limit == -1:
        return LimitCheckResult(
            allowed=True,
            status=LimitStatus.OK,
            current=0,
            limit=-1,
            percentage=0,
            message="Ilimitado"
        )
    
    # Obter uso atual
    usage = await get_or_create_usage(db, tenant_id)
    
    # Mapear tipo de limite para campo do usage
    usage_field_map = {
        LimitType.LEADS: "leads_count",
        LimitType.MESSAGES: "messages_count",
        LimitType.AI_TOKENS: "ai_tokens_used",
    }
    
    # Para limites que não são mensais (sellers, niches), verificar contagem atual
    if limit_type == LimitType.SELLERS:
        from src.domain.entities import Seller
        result = await db.execute(
            select(Seller).where(
                Seller.tenant_id == tenant_id,
                Seller.active == True
            )
        )
        current = len(result.scalars().all())
    elif limit_type == LimitType.NICHES:
        # Niches são globais, mas podemos limitar por tenant se necessário
        current = 1  # Por enquanto, cada tenant tem 1 nicho
    else:
        # Limites mensais
        field = usage_field_map.get(limit_type, "leads_count")
        current = getattr(usage, field, 0)
    
    # Calcular porcentagem
    percentage = (current / limit * 100) if limit > 0 else 0
    
    # Limite com tolerância
    limit_with_tolerance = int(limit * (1 + TOLERANCE_PERCENTAGE / 100))
    
    # Verificar status
    if current + increment > limit_with_tolerance:
        # Bloqueado - acima da tolerância
        return LimitCheckResult(
            allowed=False,
            status=LimitStatus.BLOCKED,
            current=current,
            limit=limit,
            percentage=percentage,
            message=f"Limite excedido. Você usou {current} de {limit} ({percentage:.0f}%). Faça upgrade do plano para continuar."
        )
    elif current >= limit:
        # Excedido mas na tolerância - permitir com aviso
        return LimitCheckResult(
            allowed=True,
            status=LimitStatus.EXCEEDED,
            current=current,
            limit=limit,
            percentage=percentage,
            message=f"Limite atingido! Você está usando a tolerância de {TOLERANCE_PERCENTAGE}%. Considere fazer upgrade."
        )
    elif percentage >= WARNING_THRESHOLD:
        # Aviso - acima de 80%
        return LimitCheckResult(
            allowed=True,
            status=LimitStatus.WARNING,
            current=current,
            limit=limit,
            percentage=percentage,
            message=f"Atenção: {percentage:.0f}% do limite usado ({current}/{limit})."
        )
    else:
        # OK - dentro do limite
        return LimitCheckResult(
            allowed=True,
            status=LimitStatus.OK,
            current=current,
            limit=limit,
            percentage=percentage,
            message=""
        )


async def increment_usage(
    db: AsyncSession,
    tenant_id: int,
    limit_type: str,
    amount: int = 1
) -> bool:
    """
    Incrementa o contador de uso.
    
    Retorna True se incrementou, False se bloqueado.
    """
    
    # Verificar limite primeiro
    check = await check_limit(db, tenant_id, limit_type, amount)
    
    if not check.allowed:
        return False
    
    # Obter uso
    usage = await get_or_create_usage(db, tenant_id)
    
    # Mapear tipo para campo
    field_map = {
        LimitType.LEADS: "leads_count",
        LimitType.MESSAGES: "messages_count",
        LimitType.AI_TOKENS: "ai_tokens_used",
    }
    
    field = field_map.get(limit_type)
    if field:
        current = getattr(usage, field, 0)
        setattr(usage, field, current + amount)
        await db.flush()
    
    # Se excedeu o limite (mas está na tolerância), marcar na subscription
    if check.status == LimitStatus.EXCEEDED:
        subscription = await get_subscription(db, tenant_id)
        if subscription and not subscription.is_limit_exceeded:
            subscription.is_limit_exceeded = True
            subscription.limit_exceeded_at = datetime.now()
            subscription.limit_exceeded_reason = limit_type
            subscription.tolerance_used = check.percentage - 100
            await db.flush()
    
    return True


async def get_usage_summary(
    db: AsyncSession,
    tenant_id: int
) -> dict:
    """
    Retorna resumo do uso atual do tenant.
    """
    
    # Usar a versão que carrega o plano junto
    subscription = await get_subscription_with_plan(db, tenant_id)
    usage = await get_or_create_usage(db, tenant_id)
    
    if not subscription:
        return {"error": "Assinatura não encontrada"}
    
    # Buscar contagem de vendedores
    from src.domain.entities import Seller
    sellers_result = await db.execute(
        select(Seller).where(
            Seller.tenant_id == tenant_id,
            Seller.active == True
        )
    )
    sellers_count = len(sellers_result.scalars().all())
    
    # Obter limites do plano
    leads_limit = subscription.get_limit(LimitType.LEADS)
    messages_limit = subscription.get_limit(LimitType.MESSAGES)
    sellers_limit = subscription.get_limit(LimitType.SELLERS)
    
    # Montar resumo de limites
    limits = {
        "leads": {
            "current": usage.leads_count,
            "limit": leads_limit,
            "percentage": (usage.leads_count / leads_limit * 100) if leads_limit > 0 else 0,
            "unlimited": leads_limit == -1,
        },
        "messages": {
            "current": usage.messages_count,
            "limit": messages_limit,
            "percentage": (usage.messages_count / messages_limit * 100) if messages_limit > 0 else 0,
            "unlimited": messages_limit == -1,
        },
        "sellers": {
            "current": sellers_count,
            "limit": sellers_limit,
            "percentage": (sellers_count / sellers_limit * 100) if sellers_limit > 0 else 0,
            "unlimited": sellers_limit == -1,
        },
    }
    
    # Zerar porcentagem para ilimitados
    for key in limits:
        if limits[key]["unlimited"]:
            limits[key]["percentage"] = 0
    
    # Obter nome e features do plano
    plan_name = "N/A"
    plan_slug = "N/A"
    features = {}
    
    if subscription.plan:
        plan_name = subscription.plan.name
        plan_slug = subscription.plan.slug
        features = subscription.plan.features or {}
    
    return {
        "period": usage.period,
        "plan": plan_name,
        "plan_slug": plan_slug,
        "status": subscription.status,
        "is_trial": subscription.is_trial(),
        "trial_days_remaining": subscription.days_remaining_trial() if subscription.is_trial() else 0,
        "is_blocked": subscription.is_blocked(),
        "limits": limits,
        "features": features,
    }


async def can_use_feature(
    db: AsyncSession,
    tenant_id: int,
    feature: str
) -> bool:
    """
    Verifica se o tenant pode usar uma feature.
    """
    subscription = await get_subscription_with_plan(db, tenant_id)
    
    if not subscription:
        return False
    
    if not subscription.is_active():
        return False
    
    return subscription.has_feature(feature)