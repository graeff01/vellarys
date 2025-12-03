"""
MESSAGE RATE LIMITER - Limite de Mensagens
==========================================

Protege contra:
- Flooding (muitas mensagens em pouco tempo)
- Ataques de força bruta
- Abuso do serviço
- Custos excessivos com API OpenAI

Limites configuráveis por:
- Número de telefone
- IP
- Tenant
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from collections import defaultdict
import asyncio


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
# ARMAZENAMENTO EM MEMÓRIA (para produção, usar Redis)
# =============================================================================

class InMemoryRateLimiter:
    """
    Rate limiter em memória.
    
    Para produção com múltiplas instâncias, substituir por Redis.
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
    
    async def _cleanup_old_entries(self, identifier: str, window_seconds: int) -> None:
        """Remove entradas antigas do contador."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self._counters[identifier] = [
            (ts, count) for ts, count in self._counters[identifier]
            if ts > cutoff
        ]
    
    async def _count_in_window(self, identifier: str, window_seconds: int) -> int:
        """Conta requisições na janela de tempo."""
        await self._cleanup_old_entries(identifier, window_seconds)
        return sum(count for _, count in self._counters[identifier])
    
    async def _add_request(self, identifier: str) -> None:
        """Adiciona requisição ao contador."""
        now = datetime.now()
        self._counters[identifier].append((now, 1))
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "phone",
    ) -> RateLimitResult:
        """
        Verifica se o identificador está dentro do limite.
        
        Args:
            identifier: Número de telefone, IP ou tenant_id
            limit_type: 'phone' ou 'tenant'
        
        Returns:
            RateLimitResult
        """
        async with self._lock:
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
                
                count = await self._count_in_window(identifier, window_seconds)
                
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
            await self._add_request(identifier)
            
            # Calcula remaining (baseado no limite por minuto)
            minute_count = await self._count_in_window(identifier, 60)
            remaining = limits.get("per_minute", 10) - minute_count
            
            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                reset_at=datetime.now() + timedelta(seconds=60),
                message=""
            )
    
    async def reset_limits(self, identifier: str) -> None:
        """Reseta limites para um identificador (admin only)."""
        async with self._lock:
            if identifier in self._counters:
                del self._counters[identifier]
            if identifier in self._violations:
                del self._violations[identifier]
            if identifier in self._bans:
                del self._bans[identifier]
    
    async def get_status(self, identifier: str) -> Dict:
        """Retorna status atual do rate limit."""
        async with self._lock:
            minute_count = await self._count_in_window(identifier, 60)
            hour_count = await self._count_in_window(identifier, 3600)
            day_count = await self._count_in_window(identifier, 86400)
            
            is_banned = identifier in self._bans and datetime.now() < self._bans[identifier]
            
            return {
                "identifier": identifier,
                "requests_last_minute": minute_count,
                "requests_last_hour": hour_count,
                "requests_last_day": day_count,
                "violations": self._violations.get(identifier, 0),
                "is_banned": is_banned,
                "ban_until": self._bans.get(identifier).isoformat() if is_banned else None,
            }


# Singleton do rate limiter
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Retorna instância singleton do rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

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