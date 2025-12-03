"""
ENTIDADE: AUDIT LOG
====================

Registro de auditoria para compliance e segurança.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.base import Base


class AuditLog(Base):
    """Modelo de log de auditoria."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Ação realizada
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info", index=True)
    
    # Contexto
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Origem
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Recurso afetado
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Valores antigo/novo (para alterações)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadados adicionais
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Mensagem descritiva
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.now, 
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.id}: {self.action} at {self.created_at}>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "severity": self.severity,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "lead_id": self.lead_id,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "message": self.message,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }