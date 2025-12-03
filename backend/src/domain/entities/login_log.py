"""
MODELO: LOGIN LOG
==================

Registra todas as tentativas de login.
Para segurança e auditoria.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LoginLog(Base):
    """
    Log de tentativas de login.
    
    Registra sucessos e falhas para:
    - Detectar ataques de força bruta
    - Auditoria de acessos
    - Rate limiting
    """
    
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Identificação
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Resultado
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Razões: invalid_password, user_not_found, user_inactive, rate_limited
    
    # Quando
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=func.now(), 
        index=True
    )