"""
REDIS SERVICE - Cache e Rate Limiting Distribuído
=================================================

Serviço centralizado de cache usando Redis.
Crítico para escalabilidade com múltiplas instâncias.

Funcionalidades:
- Cache de dados frequentes (settings, tenant info)
- Rate limiting distribuído
- Sessões compartilhadas

Configuração no Railway:
    REDIS_URL=redis://default:xxx@xxx.railway.app:6379
"""

import json
import logging
from typing import Optional, Any
from datetime import timedelta

from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# =============================================================================
# CLIENTE REDIS
# =============================================================================

_redis_client = None


async def get_redis():
    """
    Obtém conexão Redis singleton.
    
    Em produção, conecta ao Redis do Railway.
    Em desenvolvimento sem Redis, retorna None (fallback para in-memory).
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = getattr(settings, 'redis_url', None)
    
    if not redis_url:
        logger.warning("⚠️ REDIS_URL não configurada. Usando cache em memória (não recomendado para produção)")
        return None
    
    try:
        from redis.asyncio import Redis
        _redis_client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Testa conexão
        await _redis_client.ping()
        logger.info("✅ Redis conectado com sucesso!")
        return _redis_client
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao Redis: {e}")
        return None


async def close_redis():
    """Fecha conexão Redis."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


# =============================================================================
# CACHE BÁSICO
# =============================================================================

async def cache_get(key: str) -> Optional[str]:
    """
    Obtém valor do cache.
    
    Returns:
        Valor como string ou None se não existir
    """
    redis = await get_redis()
    if redis is None:
        return None
    
    try:
        return await redis.get(key)
    except Exception as e:
        logger.error(f"Erro ao ler cache: {e}")
        return None


async def cache_set(
    key: str, 
    value: str | dict | list, 
    ttl: int = 300,  # 5 minutos padrão
) -> bool:
    """
    Define valor no cache.
    
    Args:
        key: Chave única
        value: Valor (string, dict ou list - serializado automaticamente)
        ttl: Tempo de vida em segundos
    
    Returns:
        True se sucesso
    """
    redis = await get_redis()
    if redis is None:
        return False
    
    try:
        # Serializa dicts/lists
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        
        await redis.set(key, value, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Erro ao escrever cache: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Remove chave do cache."""
    redis = await get_redis()
    if redis is None:
        return False
    
    try:
        await redis.delete(key)
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar cache: {e}")
        return False


async def cache_get_json(key: str) -> Optional[dict | list]:
    """Obtém valor do cache e deserializa JSON."""
    value = await cache_get(key)
    if value is None:
        return None
    
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


# =============================================================================
# CACHE ESPECÍFICO PARA TENANT
# =============================================================================

def tenant_settings_key(tenant_id: int) -> str:
    """Gera chave de cache para settings do tenant."""
    return f"tenant:{tenant_id}:settings"


def tenant_info_key(tenant_slug: str) -> str:
    """Gera chave de cache para info do tenant."""
    return f"tenant:slug:{tenant_slug}"


async def cache_tenant_settings(tenant_id: int, settings_dict: dict, ttl: int = 300):
    """Cacheia settings do tenant por 5 minutos."""
    return await cache_set(
        tenant_settings_key(tenant_id),
        settings_dict,
        ttl=ttl
    )


async def get_cached_tenant_settings(tenant_id: int) -> Optional[dict]:
    """Obtém settings do tenant do cache."""
    return await cache_get_json(tenant_settings_key(tenant_id))


async def invalidate_tenant_cache(tenant_id: int):
    """Invalida cache do tenant (chamado após updates)."""
    await cache_delete(tenant_settings_key(tenant_id))


# =============================================================================
# RATE LIMITING DISTRIBUÍDO
# =============================================================================

async def rate_limit_check(
    identifier: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int, int]:
    """
    Verifica rate limit usando Redis.
    
    Args:
        identifier: ID único (phone, tenant_id, etc)
        limit: Máximo de requests permitidos
        window_seconds: Janela de tempo em segundos
    
    Returns:
        (is_allowed, current_count, ttl_remaining)
    """
    redis = await get_redis()
    
    if redis is None:
        # Fallback: sempre permite (sem Redis)
        return True, 0, 0
    
    key = f"ratelimit:{identifier}"
    
    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        
        current_count = results[0]
        ttl = results[1]
        
        # Se é a primeira request, define TTL
        if ttl == -1:
            await redis.expire(key, window_seconds)
            ttl = window_seconds
        
        is_allowed = current_count <= limit
        
        return is_allowed, current_count, ttl if ttl > 0 else 0
        
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        return True, 0, 0  # Fallback: permite


async def rate_limit_reset(identifier: str) -> bool:
    """Reseta rate limit para um identificador."""
    redis = await get_redis()
    if redis is None:
        return False
    
    key = f"ratelimit:{identifier}"
    try:
        await redis.delete(key)
        return True
    except Exception as e:
        logger.error(f"Erro ao resetar rate limit: {e}")
        return False


# =============================================================================
# MÉTRICAS SIMPLES
# =============================================================================

async def increment_metric(metric_name: str, labels: dict = None):
    """
    Incrementa contador de métrica.
    
    Ex: increment_metric("leads_created", {"tenant": "imob123"})
    """
    redis = await get_redis()
    if redis is None:
        return
    
    key = f"metric:{metric_name}"
    if labels:
        label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
        key = f"{key}:{label_str}"
    
    try:
        await redis.incr(key)
    except Exception as e:
        logger.debug(f"Erro ao incrementar métrica: {e}")


async def get_metric(metric_name: str, labels: dict = None) -> int:
    """Obtém valor de métrica."""
    redis = await get_redis()
    if redis is None:
        return 0
    
    key = f"metric:{metric_name}"
    if labels:
        label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
        key = f"{key}:{label_str}"
    
    try:
        value = await redis.get(key)
        return int(value) if value else 0
    except Exception as e:
        logger.debug(f"Erro ao ler métrica: {e}")
        return 0


# =============================================================================
# HEALTH CHECK
# =============================================================================

async def redis_health_check() -> dict:
    """
    Verifica saúde do Redis.
    
    Returns:
        {"status": "ok/error", "latency_ms": float, "info": dict}
    """
    import time
    
    redis = await get_redis()
    
    if redis is None:
        return {
            "status": "disabled",
            "message": "Redis não configurado",
            "latency_ms": 0,
        }
    
    try:
        start = time.time()
        await redis.ping()
        latency = (time.time() - start) * 1000
        
        info = await redis.info("server")
        
        return {
            "status": "ok",
            "latency_ms": round(latency, 2),
            "version": info.get("redis_version", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "latency_ms": 0,
        }
