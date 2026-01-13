"""
ENTIDADE: PRODUCT (PRODUTO)
=========================

Cadastro de produtos/serviços para fluxo de atendimento.
Esta é uma entidade genérica que permite ao Velaris atuar em múltiplos nichos.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Boolean, ForeignKey, 
    DateTime, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.mutable import MutableDict, MutableList

from src.domain.entities.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """
    Representa um produto ou serviço cadastrado pelo tenant.
    """
    
    __tablename__ = "products"
    
    # =========================================================================
    # IDENTIFICAÇÃO
    # =========================================================================
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tenants.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # =========================================================================
    # INFORMAÇÕES BÁSICAS
    # =========================================================================
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="active"
    )
    
    url_landing_page: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # =========================================================================
    # GATILHOS DE DETECÇÃO
    # =========================================================================
    
    triggers: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=False
    )
    
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # =========================================================================
    # QUALIFICAÇÃO ESPECÍFICA
    # =========================================================================
    
    qualification_questions: Mapped[list] = mapped_column(
        MutableList.as_mutable(ARRAY(String)),
        default=list,
        nullable=True
    )
    
    ai_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # =========================================================================
    # DESTINO DOS LEADS
    # =========================================================================
    
    seller_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True
    )
    
    distribution_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notify_manager: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # =========================================================================
    # MÉTRICAS
    # =========================================================================
    
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualified_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    converted_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # =========================================================================
    # ATRIBUTOS DINÂMICOS (JSONB)
    # =========================================================================
    
    # Aqui guardamos campos específicos de cada nicho
    # Ex (Imobiliário): {"bairro": "Centro", "quartos": 3, "preco": 500000}
    # Ex (Automotivo): {"marca": "Toyota", "ano": 2024, "preco": 150000}
    attributes: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )
    
    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    
    tenant = relationship("Tenant", back_populates="products")
    seller = relationship("Seller", back_populates="products")
    
    # =========================================================================
    # ÍNDICES
    # =========================================================================
    
    __table_args__ = (
        Index("ix_products_tenant_active", "tenant_id", "active"),
        Index("ix_products_tenant_slug", "tenant_id", "slug", unique=True),
    )
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def matches_message(self, message: str) -> bool:
        if not self.triggers:
            return False
        
        message_lower = message.lower()
        
        for trigger in self.triggers:
            if trigger.lower() in message_lower:
                return True
        
        return False
    
    def to_ai_context(self) -> dict:
        """
        Converte o produto para contexto da IA.
        """
        context = {
            "name": self.name,
            "status": self.status,
            "description": self.description,
        }
        
        # Adiciona todos os atributos dinâmicos
        if self.attributes:
            context.update(self.attributes)
        
        # Perguntas específicas
        if self.qualification_questions:
            context["qualification_questions"] = self.qualification_questions
        
        # Instruções extras
        if self.ai_instructions:
            context["ai_instructions"] = self.ai_instructions
        
        return context
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"
