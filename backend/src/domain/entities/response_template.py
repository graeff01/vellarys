"""
ResponseTemplate - Templates de Respostas Rápidas
==================================================

Permite vendedores criarem mensagens pré-formatadas com variáveis:
- Saudações personalizadas
- Respostas sobre disponibilidade
- Solicitação de documentos
- Agradecimentos

Variáveis suportadas:
- {{lead_name}}
- {{seller_name}}
- {{current_date}}
- {{current_time}}
- {{company_name}}
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, User


class ResponseTemplate(Base, TimestampMixin):
    """Template de resposta rápida."""

    __tablename__ = "response_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Identificação do template
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shortcut: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Ex: "/saudacao"

    # Conteúdo com variáveis
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Organização
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "saudacao", "followup", "agradecimento"

    # Controle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relacionamentos
    tenant: Mapped["Tenant"] = relationship()
    created_by: Mapped[Optional["User"]] = relationship()

    # Índices
    __table_args__ = (
        Index("ix_templates_tenant_active", "tenant_id", "is_active"),
        Index("ix_templates_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<ResponseTemplate(id={self.id}, name='{self.name}', shortcut='{self.shortcut}')>"
