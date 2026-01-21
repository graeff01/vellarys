"""
PROPERTY EMBEDDINGS - Vetores para busca semântica
===================================================

Armazena embeddings (vetores) dos imóveis para permitir
busca por similaridade usando pgvector.

Exemplo de uso:
- Cliente: "Quero apartamento perto de escolas boas"
- Sistema: Gera embedding da query
- Busca top 5 imóveis com maior similaridade coseno
- IA responde com os imóveis mais relevantes
"""

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, ARRAY, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from typing import Optional, List

from .base import Base, TimestampMixin


class PropertyEmbedding(Base, TimestampMixin):
    """Embedding vetorial de um imóvel/produto."""
    
    __tablename__ = "property_embeddings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True
    )
    
    # Embedding: vetor de 1536 dimensões
    embedding: Mapped[List[float]] = mapped_column(
        ARRAY(Float),
        nullable=False
    )
    
    # Hash do conteúdo
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )
    
    # Metadata adicional (debug/auditoria)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    
    # Relacionamentos
    # tenant: Mapped["Tenant"] = relationship(back_populates="property_embeddings")
    # product: Mapped["Product"] = relationship(back_populates="embedding")
