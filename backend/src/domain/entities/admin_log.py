"""
MODELO: ADMIN LOG
==================

Registra todas as ações feitas no painel admin.
Para auditoria e segurança.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AdminLog(Base):
    """
    Log de ações administrativas.
    
    Registra quem fez o quê e quando.
    """
    
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Quem fez
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)  # Backup caso user seja deletado
    
    # O que fez
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Ações: create_tenant, update_tenant, delete_tenant, create_niche, update_niche, etc.
    
    # Em qual recurso
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # tenant, niche, user, settings
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Nome para referência
    
    # Detalhes
    details: Mapped[dict] = mapped_column(JSONB, default=dict)  # Dados alterados
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Quando
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)