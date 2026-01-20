"""
HEALTH CHECK ENDPOINTS
======================
Monitora saúde do sistema em tempo real.

Usado por:
- UptimeRobot (monitoramento externo)
- Dashboard interno
- Debugging
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Tenant, Message
from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


# =============================================================================
# HEALTH CHECK SIMPLES (PARA UPTIMEROBOT)
# =============================================================================

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check simples e rápido.
    
    Retorna 200 se tudo OK, 503 se algo crítico falhou.
    
    Verificações:
    - ✅ Database conectado
    - ✅ Último lead recebido (não pode estar muito antigo)
    - ✅ Sistema respondendo
    """
    try:
        status = "healthy"
        checks = {}
        
        # 1. Verifica conexão com banco
        try:
            await db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            status = "unhealthy"
        
        # 2. Verifica se está recebendo leads recentemente
        try:
            result = await db.execute(
                select(func.max(Lead.created_at))
            )
            last_lead_time = result.scalar()
            
            if last_lead_time:
                time_since_last_lead = datetime.now(timezone.utc) - last_lead_time
                minutes_ago = int(time_since_last_lead.total_seconds() / 60)
                
                # Se não recebe lead há mais de 2 horas, pode ser problema
                if minutes_ago > 120:
                    checks["leads"] = f"warning: {minutes_ago} min ago"
                else:
                    checks["leads"] = f"ok: {minutes_ago} min ago"
            else:
                checks["leads"] = "no_leads_yet"
        except Exception as e:
            checks["leads"] = f"error: {str(e)}"
        
        # 3. Timestamp atual
        checks["timestamp"] = datetime.now(timezone.utc).isoformat()
        checks["environment"] = settings.environment
        
        # Se status unhealthy, retorna 503
        if status == "unhealthy":
            raise HTTPException(status_code=503, detail={
                "status": status,
                "checks": checks
            })
        
        return {
            "status": status,
            "checks": checks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "error": str(e)
        })


# =============================================================================
# HEALTH CHECK DETALHADO (PARA ADMIN/DEBUG)
# =============================================================================

@router.get("/detailed")
async def health_check_detailed(db: AsyncSession = Depends(get_db)):
    """
    Health check completo com métricas detalhadas.
    
    Mostra:
    - Status de todas as dependências
    - Métricas de leads (hoje, última hora)
    - Status por tenant
    - Performance do sistema
    """
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_hour = now - timedelta(hours=1)
        
        health_data = {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "environment": settings.environment,
            "uptime": "TODO",  # Implementar depois
            "checks": {},
            "metrics": {},
            "warnings": [],
        }
        
        # =====================================================================
        # 1. DATABASE
        # =====================================================================
        try:
            start = datetime.now(timezone.utc)
            await db.execute(text("SELECT 1"))
            query_time = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            health_data["checks"]["database"] = {
                "status": "ok",
                "response_time_ms": round(query_time, 2)
            }
            
            if query_time > 500:
                health_data["warnings"].append(f"Database slow: {query_time}ms")
                
        except Exception as e:
            health_data["checks"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_data["status"] = "unhealthy"
        
        # =====================================================================
        # 2. LEADS METRICS
        # =====================================================================
        try:
            # Total de leads
            total_leads = (await db.execute(
                select(func.count(Lead.id))
            )).scalar() or 0
            
            # Leads hoje
            leads_today = (await db.execute(
                select(func.count(Lead.id))
                .where(Lead.created_at >= today_start)
            )).scalar() or 0
            
            # Leads última hora
            leads_last_hour = (await db.execute(
                select(func.count(Lead.id))
                .where(Lead.created_at >= last_hour)
            )).scalar() or 0
            
            # Último lead
            result = await db.execute(
                select(Lead.created_at)
                .order_by(Lead.created_at.desc())
                .limit(1)
            )
            last_lead = result.scalar_one_or_none()
            
            minutes_since_last_lead = None
            if last_lead:
                time_diff = now - last_lead
                minutes_since_last_lead = int(time_diff.total_seconds() / 60)
                
                # Warning se não recebe lead há muito tempo
                if total_leads > 10 and minutes_since_last_lead > 120:
                    health_data["warnings"].append(
                        f"No leads received in {minutes_since_last_lead} minutes"
                    )
            
            health_data["metrics"]["leads"] = {
                "total": total_leads,
                "today": leads_today,
                "last_hour": leads_last_hour,
                "last_received_minutes_ago": minutes_since_last_lead
            }
            
        except Exception as e:
            health_data["checks"]["leads_metrics"] = {
                "status": "error",
                "error": str(e)
            }
        
        # =====================================================================
        # 3. MESSAGES METRICS
        # =====================================================================
        try:
            # Mensagens processadas hoje
            messages_today = (await db.execute(
                select(func.count(Message.id))
                .where(Message.created_at >= today_start)
            )).scalar() or 0
            
            # Média de tokens por mensagem (hoje)
            avg_tokens = (await db.execute(
                select(func.avg(Message.tokens_used))
                .where(Message.created_at >= today_start)
                .where(Message.tokens_used.isnot(None))
            )).scalar()
            
            health_data["metrics"]["messages"] = {
                "today": messages_today,
                "avg_tokens_today": round(float(avg_tokens), 2) if avg_tokens else 0
            }
            
        except Exception as e:
            health_data["checks"]["messages_metrics"] = {
                "status": "error",
                "error": str(e)
            }
        
        # =====================================================================
        # 4. TENANTS STATUS
        # =====================================================================
        try:
            # Total de tenants ativos
            total_tenants = (await db.execute(
                select(func.count(Tenant.id))
                .where(Tenant.active == True)
            )).scalar() or 0
            
            # Tenants com leads hoje
            tenants_with_leads_today = (await db.execute(
                select(func.count(func.distinct(Lead.tenant_id)))
                .where(Lead.created_at >= today_start)
            )).scalar() or 0
            
            health_data["metrics"]["tenants"] = {
                "total_active": total_tenants,
                "with_leads_today": tenants_with_leads_today
            }
            
        except Exception as e:
            health_data["checks"]["tenants_metrics"] = {
                "status": "error",
                "error": str(e)
            }
        
        # =====================================================================
        # 5. EXTERNAL APIS (básico)
        # =====================================================================
        
        # OpenAI
        try:
            from src.infrastructure.services.openai_service import openai_client
            if openai_client:
                health_data["checks"]["openai"] = {"status": "configured"}
            else:
                health_data["checks"]["openai"] = {"status": "not_configured"}
                health_data["warnings"].append("OpenAI not configured")
        except Exception as e:
            health_data["checks"]["openai"] = {"status": "error", "error": str(e)}
        
        # WhatsApp/Z-API
        try:
            from src.infrastructure.services.zapi_service import get_zapi_client
            zapi = get_zapi_client()
            if zapi and zapi.is_configured():
                health_data["checks"]["whatsapp"] = {"status": "configured"}
            else:
                health_data["checks"]["whatsapp"] = {"status": "not_configured"}
                health_data["warnings"].append("WhatsApp/Z-API not configured")
        except Exception as e:
            health_data["checks"]["whatsapp"] = {"status": "error", "error": str(e)}
        
        # =====================================================================
        # 6. REDIS (Cache & Rate Limiting)
        # =====================================================================
        try:
            from src.infrastructure.services.redis_service import redis_health_check
            redis_status = await redis_health_check()
            
            health_data["checks"]["redis"] = redis_status
            
            if redis_status["status"] == "disabled":
                health_data["warnings"].append("Redis not configured - using in-memory rate limiting (not scalable)")
            elif redis_status["status"] == "error":
                health_data["warnings"].append(f"Redis error: {redis_status.get('message', 'unknown')}")
                
        except Exception as e:
            health_data["checks"]["redis"] = {"status": "error", "error": str(e)}
            health_data["warnings"].append(f"Redis check failed: {e}")
        
        # =====================================================================
        # STATUS FINAL
        # =====================================================================
        
        if health_data["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=health_data)
        
        return health_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "error": str(e)
        })