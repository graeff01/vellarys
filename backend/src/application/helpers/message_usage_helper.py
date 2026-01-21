"""
HELPER: Increment Message Usage
================================

Helper para incrementar contador de mensagens após envio.
Usado em process_message.py
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.application.services.limits_service import increment_usage, LimitType

logger = logging.getLogger(__name__)


async def increment_message_count(db: AsyncSession, tenant_id: int) -> bool:
    """
    Incrementa contador de mensagens do tenant.
    
    Retorna True se incrementou, False se bloqueado.
    """
    try:
        success = await increment_usage(
            db=db,
            tenant_id=tenant_id,
            limit_type=LimitType.MESSAGES,
            amount=1
        )
        
        if not success:
            logger.warning(f"⚠️ Limite de mensagens atingido para tenant {tenant_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Erro ao incrementar mensagens: {e}")
        # Não bloqueia o fluxo em caso de erro
        return True
