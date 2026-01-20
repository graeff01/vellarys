"""
MESSAGE RATE LIMITER - Limite de Mensagens (v2.0 - Redis)
==========================================================

Protege contra:
- Flooding (muitas mensagens em pouco tempo)
- Ataques de força bruta
- Abuso do serviço
- Custos excessivos com API OpenAI

ATUALIZADO v2.0:
- Usa Redis quando disponível (escalável para múltiplas instâncias)
- Fallback para memória quando Redis não configurado
- Thread-safe e distribuído

Limites configuráveis por:
- Número de telefone
- IP
- Tenant
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimitResult:
    """Resultado da verificação de rate limit."""
    
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_at: datetime,
        retry_after_seconds: int = 0,
        message: str = ""
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after_seconds = retry_after_seconds
        self.message = message
    
    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat(),
            "retry_after_seconds": self.retry_after_seconds,
            "message": self.message,
        }


# =============================================================================
# CONFIGURAÇÕES DE LIMITE
# =============================================================================

class RateLimitConfig:
    """Configurações de rate limiting."""
    
    # Limites por número de telefone
    PHONE_LIMITS = {
        "per_minute": 10,      # Max 10 msgs/min (proteção contra flooding)
        "per_hour": 60,        # Max 60 msgs/hora
        "per_day": 200,        # Max 200 msgs/dia
    }
    
    # Limites por tenant (proteção de custos)
    TENANT_LIMITS = {
        "per_minute": 100,     # Max 100 msgs/min por tenant
        "per_hour": 1000,      # Max 1000 msgs/hora por tenant
    }
    
    # Cooldown após bloqueio (segundos)
    COOLDOWN_SECONDS = 60
    
    # Tempo de ban após múltiplas violações
    BAN_THRESHOLD = 5          # Número de violações para ban
    BAN_DURATION_HOURS = 24    # Duração do ban


# =============================================================================
# REDIS RATE LIMITER (PRODUÇÃO - ESCALÁVEL)
# =============================================================================

class RedisRateLimiter:
    """
    Rate limiter usando Redis.
    
    Funciona com múltiplas instâncias do backend.
    Usa algoritmo de sliding window com contadores.
    """
    
    def __init__(self):
        self._redis = None
        self._initialized = False
    
    async def _get_redis(self):
        """Obtém cliente Redis."""
        if not self._initialized:
            try:
                from src.infrastructure.services.redis_service import get_redis
                self._redis = await get_redis()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Redis não disponível para rate limit: {e}")
                self._initialized = True
        return self._redis
    
    async def is_available(self) -> bool:
        """Verifica se Redis está disponível."""
        redis = await self._get_redis()
        return redis is not None
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "phone",
    ) -> Optional[RateLimitResult]:
        """
        Verifica rate limit usando Redis.
        
        Returns:
            RateLimitResult se Redis disponível, None caso contrário
        """
        redis = await self._get_redis()
        if redis is None:
            return None  # Fallback para memória
        
        try:
            limits = RateLimitConfig.PHONE_LIMITS if limit_type == "phone" else RateLimitConfig.TENANT_LIMITS
            
            # Checa ban primeiro
            ban_key = f"ratelimit:ban:{identifier}"
            ban_until = await redis.get(ban_key)
            if ban_until:
                ban_datetime = datetime.fromisoformat(ban_until)
                if datetime.now() < ban_datetime:
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=ban_datetime,
                        retry_after_seconds=int((ban_datetime - datetime.now()).total_seconds()),
                        message="Você foi temporariamente bloqueado por excesso de mensagens."
                    )
            
            # Verifica cada janela
            for window_name, max_requests in limits.items():
                if window_name == "per_minute":
                    window_seconds = 60
                elif window_name == "per_hour":
                    window_seconds = 3600
                elif window_name == "per_day":
                    window_seconds = 86400
                else:
                    continue
                
                key = f"ratelimit:{identifier}:{window_name}"
                
                # Incrementa e verifica
                pipe = redis.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                results = await pipe.execute()
                
                count = results[0]
                ttl = results[1]
                
                # Define TTL se é a primeira request
                if ttl == -1:
                    await redis.expire(key, window_seconds)
                
                if count > max_requests:
                    # Limite excedido - registra violação
                    violation_key = f"ratelimit:violations:{identifier}"
                    violations = await redis.incr(violation_key)
                    await redis.expire(violation_key, 86400)  # Expira em 24h
                    
                    # Verifica se deve banir
                    if violations >= RateLimitConfig.BAN_THRESHOLD:
                        ban_until_dt = datetime.now() + timedelta(hours=RateLimitConfig.BAN_DURATION_HOURS)
                        await redis.set(ban_key, ban_until_dt.isoformat(), ex=RateLimitConfig.BAN_DURATION_HOURS * 3600)
                        
                        return RateLimitResult(
                            allowed=False,
                            remaining=0,
                            reset_at=ban_until_dt,
                            retry_after_seconds=RateLimitConfig.BAN_DURATION_HOURS * 3600,
                            message="Você foi bloqueado por 24 horas devido ao excesso de mensagens."
                        )
                    
                    reset_at = datetime.now() + timedelta(seconds=RateLimitConfig.COOLDOWN_SECONDS)
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=reset_at,
                        retry_after_seconds=RateLimitConfig.COOLDOWN_SECONDS,
                        message=f"Muitas mensagens. Aguarde {RateLimitConfig.COOLDOWN_SECONDS} segundos."
                    )
            
            # Dentro do limite
            minute_key = f"ratelimit:{identifier}:per_minute"
            minute_count = int(await redis.get(minute_key) or 0)
            remaining = limits.get("per_minute", 10) - minute_count
            
            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                reset_at=datetime.now() + timedelta(seconds=60),
                message=""
            )
            
        except Exception as e:
            logger.error(f"Erro no Redis rate limit: {e}")
            return None  # Fallback para memória
    
    async def reset_limits(self, identifier: str) -> bool:
        """Reseta limites no Redis."""
        redis = await self._get_redis()
        if redis is None:
            return False
        
        try:
            keys_to_delete = [
                f"ratelimit:{identifier}:per_minute",
                f"ratelimit:{identifier}:per_hour",
                f"ratelimit:{identifier}:per_day",
                f"ratelimit:violations:{identifier}",
                f"ratelimit:ban:{identifier}",
            ]
            await redis.delete(*keys_to_delete)
            return True
        except Exception as e:
            logger.error(f"Erro ao resetar rate limit no Redis: {e}")
            return False
    
    async def get_status(self, identifier: str) -> Optional[Dict]:
        """Retorna status do rate limit via Redis."""
        redis = await self._get_redis()
        if redis is None:
            return None
        
        try:
            minute_count = int(await redis.get(f"ratelimit:{identifier}:per_minute") or 0)
            hour_count = int(await redis.get(f"ratelimit:{identifier}:per_hour") or 0)
            day_count = int(await redis.get(f"ratelimit:{identifier}:per_day") or 0)
            violations = int(await redis.get(f"ratelimit:violations:{identifier}") or 0)
            ban_until = await redis.get(f"ratelimit:ban:{identifier}")
            
            is_banned = ban_until is not None and datetime.now() < datetime.fromisoformat(ban_until)
            
            return {
                "identifier": identifier,
                "requests_last_minute": minute_count,
                "requests_last_hour": hour_count,
                "requests_last_day": day_count,
                "violations": violations,
                "is_banned": is_banned,
                "ban_until": ban_until if is_banned else None,
                "backend": "redis",
            }
        except Exception as e:
            logger.error(f"Erro ao obter status do Redis: {e}")
            return None


# =============================================================================
# IN-MEMORY RATE LIMITER (FALLBACK)
# =============================================================================

class InMemoryRateLimiter:
    """
    Rate limiter em memória.
    
    Usado como fallback quando Redis não está disponível.
    NÃO funciona com múltiplas instâncias!
    """
    
    def __init__(self):
        # Contador: {identifier: [(timestamp, count), ...]}
        self._counters: Dict[str, list] = defaultdict(list)
        
        # Violações: {identifier: count}
        self._violations: Dict[str, int] = defaultdict(int)
        
        # Bans: {identifier: ban_until}
        self._bans: Dict[str, datetime] = {}
        
        # Lock para thread safety
        self._lock = asyncio.Lock()
    
    def _cleanup_old_entries(self, identifier: str, window_seconds: int) -> None:
        """Remove entradas antigas do contador."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self._counters[identifier] = [
            (ts, count) for ts, count in self._counters[identifier]
            if ts > cutoff
        ]
    
    def _count_in_window(self, identifier: str, window_seconds: int) -> int:
        """Conta requisições na janela de tempo."""
        self._cleanup_old_entries(identifier, window_seconds)
        return sum(count for _, count in self._counters[identifier])
    
    def _add_request(self, identifier: str) -> None:
        """Adiciona requisição ao contador."""
        now = datetime.now()
        self._counters[identifier].append((now, 1))
    
    def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "phone",
    ) -> RateLimitResult:
        """
        Verifica se o identificador está dentro do limite.
        
        NOTA: Versão síncrona para facilitar testes.
        """
        # Verifica se está banido
        if identifier in self._bans:
            if datetime.now() < self._bans[identifier]:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=self._bans[identifier],
                    retry_after_seconds=int((self._bans[identifier] - datetime.now()).total_seconds()),
                    message="Você foi temporariamente bloqueado por excesso de mensagens."
                )
            else:
                # Ban expirou
                del self._bans[identifier]
                self._violations[identifier] = 0
        
        # Seleciona limites baseado no tipo
        limits = RateLimitConfig.PHONE_LIMITS if limit_type == "phone" else RateLimitConfig.TENANT_LIMITS
        
        # Verifica cada janela de tempo
        for window_name, max_requests in limits.items():
            if window_name == "per_minute":
                window_seconds = 60
            elif window_name == "per_hour":
                window_seconds = 3600
            elif window_name == "per_day":
                window_seconds = 86400
            else:
                continue
            
            count = self._count_in_window(identifier, window_seconds)
            
            if count >= max_requests:
                # Limite excedido
                self._violations[identifier] += 1
                
                # Verifica se deve banir
                if self._violations[identifier] >= RateLimitConfig.BAN_THRESHOLD:
                    ban_until = datetime.now() + timedelta(hours=RateLimitConfig.BAN_DURATION_HOURS)
                    self._bans[identifier] = ban_until
                    
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=ban_until,
                        retry_after_seconds=RateLimitConfig.BAN_DURATION_HOURS * 3600,
                        message="Você foi bloqueado por 24 horas devido ao excesso de mensagens."
                    )
                
                reset_at = datetime.now() + timedelta(seconds=RateLimitConfig.COOLDOWN_SECONDS)
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after_seconds=RateLimitConfig.COOLDOWN_SECONDS,
                    message=f"Muitas mensagens. Aguarde {RateLimitConfig.COOLDOWN_SECONDS} segundos."
                )
        
        # Dentro do limite - adiciona requisição
        self._add_request(identifier)
        
        # Calcula remaining (baseado no limite por minuto)
        minute_count = self._count_in_window(identifier, 60)
        remaining = limits.get("per_minute", 10) - minute_count
        
        return RateLimitResult(
            allowed=True,
            remaining=max(0, remaining),
            reset_at=datetime.now() + timedelta(seconds=60),
            message=""
        )
    
    def reset_limits(self, identifier: str) -> None:
        """Reseta limites para um identificador (admin only)."""
        if identifier in self._counters:
            del self._counters[identifier]
        if identifier in self._violations:
            del self._violations[identifier]
        if identifier in self._bans:
            del self._bans[identifier]
    
    def get_status(self, identifier: str) -> Dict:
        """Retorna status atual do rate limit."""
        minute_count = self._count_in_window(identifier, 60)
        hour_count = self._count_in_window(identifier, 3600)
        day_count = self._count_in_window(identifier, 86400)
        
        is_banned = identifier in self._bans and datetime.now() < self._bans[identifier]
        
        return {
            "identifier": identifier,
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "requests_last_day": day_count,
            "violations": self._violations.get(identifier, 0),
            "is_banned": is_banned,
            "ban_until": self._bans.get(identifier).isoformat() if is_banned else None,
            "backend": "memory",
        }


# =============================================================================
# HYBRID RATE LIMITER (Redis + Memory Fallback)
# =============================================================================

class HybridRateLimiter:
    """
    Rate limiter híbrido.
    
    Usa Redis quando disponível, fallback para memória.
    """
    
    def __init__(self):
        self._redis_limiter = RedisRateLimiter()
        self._memory_limiter = InMemoryRateLimiter()
        self._using_redis = None  # None = não verificado ainda
    
    async def _use_redis(self) -> bool:
        """Verifica se deve usar Redis."""
        if self._using_redis is None:
            self._using_redis = await self._redis_limiter.is_available()
            if self._using_redis:
                logger.info("✅ Rate Limiter usando REDIS (distribuído)")
            else:
                logger.warning("⚠️ Rate Limiter usando MEMÓRIA (não escalável)")
        return self._using_redis
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "phone",
    ) -> RateLimitResult:
        """Verifica rate limit usando backend disponível."""
        
        if await self._use_redis():
            result = await self._redis_limiter.check_rate_limit(identifier, limit_type)
            if result is not None:
                return result
        
        # Fallback para memória
        return self._memory_limiter.check_rate_limit(identifier, limit_type)
    
    async def reset_limits(self, identifier: str) -> None:
        """Reseta limites em ambos backends."""
        if await self._use_redis():
            await self._redis_limiter.reset_limits(identifier)
        self._memory_limiter.reset_limits(identifier)
    
    async def get_status(self, identifier: str) -> Dict:
        """Retorna status do backend ativo."""
        if await self._use_redis():
            status = await self._redis_limiter.get_status(identifier)
            if status is not None:
                return status
        
        return self._memory_limiter.get_status(identifier)


# =============================================================================
# SINGLETON E FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

_rate_limiter: Optional[HybridRateLimiter] = None


def get_rate_limiter() -> HybridRateLimiter:
    """Retorna instância singleton do rate limiter híbrido."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = HybridRateLimiter()
    return _rate_limiter


async def check_message_rate_limit(
    phone: str,
    tenant_id: int = None,
) -> RateLimitResult:
    """
    Verifica rate limit para uma mensagem.
    
    Verifica tanto o limite por telefone quanto por tenant.
    """
    limiter = get_rate_limiter()
    
    # Verifica limite por telefone
    phone_result = await limiter.check_rate_limit(f"phone:{phone}", "phone")
    if not phone_result.allowed:
        return phone_result
    
    # Verifica limite por tenant
    if tenant_id:
        tenant_result = await limiter.check_rate_limit(f"tenant:{tenant_id}", "tenant")
        if not tenant_result.allowed:
            return tenant_result
    
    return phone_result


async def get_rate_limit_status(phone: str) -> Dict:
    """Retorna status do rate limit para um telefone."""
    limiter = get_rate_limiter()
    return await limiter.get_status(f"phone:{phone}")


async def reset_rate_limit(phone: str) -> None:
    """Reseta rate limit para um telefone (admin only)."""
    limiter = get_rate_limiter()
    await limiter.reset_limits(f"phone:{phone}")


def get_rate_limit_response() -> str:
    """Retorna mensagem padrão quando rate limit é excedido."""
    return (
        "Você está enviando muitas mensagens. "
        "Por favor, aguarde um momento antes de continuar. "
        "Isso ajuda a garantir a qualidade do atendimento para todos. 🙏"
    )
