"""
PUSH SUBSCRIPTION - Assinaturas de Push Notifications
=====================================================

Guarda as subscriptions dos navegadores/dispositivos
para enviar notificações push.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin


class PushSubscription(Base, TimestampMixin):
    """
    Subscription de Push Notification de um usuário/dispositivo.
    
    Cada usuário pode ter múltiplas subscriptions (vários dispositivos).
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Relacionamento com usuário
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    # Relacionamento com tenant (para facilitar queries)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True
    )
    
    # Dados da subscription (do navegador)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    
    # Chaves de autenticação (p256dh e auth)
    keys: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=False
    )
    
    # Metadados do dispositivo
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Última notificação enviada com sucesso
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Contador de falhas (para desativar subscriptions inválidas)
    failure_count: Mapped[int] = mapped_column(default=0)
    
    # Relacionamentos
    user: Mapped["User"] = relationship(back_populates="push_subscriptions")
    tenant: Mapped["Tenant"] = relationship()


# Adicionar ao User o relacionamento reverso
# Isso será feito no __init__.py ou models.py
