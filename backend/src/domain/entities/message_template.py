"""
Entidade: Message Template
Templates de mensagens pré-definidas para respostas rápidas
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class MessageTemplate(Base):
    """Template de mensagem para respostas rápidas."""
    
    __tablename__ = "message_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # Nome do template
    shortcut = Column(String(50), nullable=True)  # Atalho (ex: /saudacao)
    category = Column(String(50), nullable=True)  # saudacao, objecao, despedida, etc
    content = Column(Text, nullable=False)  # Conteúdo com variáveis {{nome}}, {{produto}}
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relacionamentos
    tenant = relationship("Tenant")
