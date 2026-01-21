"""
KNOWLEDGE EMBEDDINGS - Vetores para RAG de FAQ/Documentos
=========================================================

Armazena embeddings de FAQ, documentos, regras de negócio e políticas
para permitir busca semântica (RAG) na base de conhecimento.

Exemplo de uso:
- Cliente: "Como funciona o financiamento?"
- Sistema: Gera embedding da query
- Busca top 3 FAQs com maior similaridade coseno
- IA responde usando o conhecimento encontrado
"""

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, ARRAY, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from typing import Optional, List

from .base import Base, TimestampMixin


class KnowledgeEmbedding(Base, TimestampMixin):
    """
    Embedding vetorial para base de conhecimento (FAQ, documentos, regras).

    Atributos:
        source_type: Tipo da fonte ('faq', 'document', 'rule', 'policy')
        source_id: Identificador único da fonte (para atualizações)
        title: Título ou pergunta (para FAQ)
        content: Conteúdo ou resposta
        embedding: Vetor de 1536 dimensões
        content_hash: Hash MD5 do conteúdo (para detectar mudanças)
        metadata: Dados extras (categoria, tags, prioridade)
        active: Se está ativo para buscas
    """

    __tablename__ = "knowledge_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True
    )

    # Tipo e identificação da fonte
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Conteúdo
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Embedding: vetor de 1536 dimensões (OpenAI text-embedding-3-small)
    embedding: Mapped[List[float]] = mapped_column(ARRAY(Float), nullable=False)

    # Hash do conteúdo (para detectar se precisa regenerar)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Metadata adicional (categoria, tags, prioridade, etc)
    metadata: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    # Status (permite desativar sem excluir)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    def __repr__(self) -> str:
        return f"<KnowledgeEmbedding(id={self.id}, type={self.source_type}, title={self.title[:30] if self.title else 'N/A'})>"
