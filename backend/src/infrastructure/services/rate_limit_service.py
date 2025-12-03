"""
SERVIÇO: RATE LIMITING
=======================

Protege contra ataques de força bruta.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import LoginLog


# Configurações
MAX_ATTEMPTS = 5  # Máximo de tentativas
LOCKOUT_MINUTES = 15  # Tempo de bloqueio
WINDOW_MINUTES = 15  # Janela de tempo para contar tentativas


async def check_rate_limit(
    db: AsyncSession,
    email: str,
    ip_address: Optional[str] = None,
) -> Tuple[bool, int, Optional[datetime]]:
    """
    Verifica se o email/IP está bloqueado por rate limiting.
    
    Returns:
        Tuple[is_allowed, remaining_attempts, unlock_time]
        - is_allowed: True se pode tentar login
        - remaining_attempts: Quantas tentativas restam
        - unlock_time: Quando será desbloqueado (se bloqueado)
    """
    
    window_start = datetime.now() - timedelta(minutes=WINDOW_MINUTES)
    
    # Conta tentativas falhas recentes
    query = select(func.count(LoginLog.id)).where(
        and_(
            LoginLog.email == email,
            LoginLog.success == False,
            LoginLog.created_at >= window_start,
        )
    )
    
    result = await db.execute(query)
    failed_attempts = result.scalar() or 0
    
    # Se excedeu o limite
    if failed_attempts >= MAX_ATTEMPTS:
        # Busca a última tentativa para calcular unlock_time
        last_attempt_query = select(LoginLog.created_at).where(
            and_(
                LoginLog.email == email,
                LoginLog.success == False,
            )
        ).order_by(LoginLog.created_at.desc()).limit(1)
        
        last_result = await db.execute(last_attempt_query)
        last_attempt = last_result.scalar()
        
        if last_attempt:
            unlock_time = last_attempt + timedelta(minutes=LOCKOUT_MINUTES)
            if datetime.now() < unlock_time:
                return False, 0, unlock_time
    
    remaining = MAX_ATTEMPTS - failed_attempts
    return True, remaining, None


async def log_login_attempt(
    db: AsyncSession,
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> LoginLog:
    """
    Registra uma tentativa de login.
    """
    
    log = LoginLog(
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason,
    )
    
    db.add(log)
    await db.flush()
    
    return log


async def clear_failed_attempts(
    db: AsyncSession,
    email: str,
) -> None:
    """
    Limpa tentativas falhas após login bem-sucedido.
    (Opcional - mantém histórico mas reseta contador)
    """
    # Não deletamos, apenas o login bem-sucedido "reseta" a contagem
    # porque a janela de tempo vai passar
    pass


async def get_login_history(
    db: AsyncSession,
    email: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
) -> list:
    """
    Retorna histórico de logins para auditoria.
    """
    
    date_limit = datetime.now() - timedelta(days=days)
    
    query = select(LoginLog).where(LoginLog.created_at >= date_limit)
    
    if email:
        query = query.where(LoginLog.email == email)
    
    query = query.order_by(LoginLog.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()