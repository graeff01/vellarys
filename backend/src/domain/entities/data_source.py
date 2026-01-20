"""
DATA SOURCE - Fontes de dados configuráveis por tenant
======================================================

Permite que cada tenant configure suas próprias fontes de dados
para a IA buscar informações sobre imóveis/produtos.

Tipos suportados:
- portal_api: API JSON de portal (ex: portalinvestimento.com)
- custom_api: API REST genérica com autenticação configurável
- webhook: Recebe dados via POST do sistema do cliente
- manual: Usa apenas a tabela Products local
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, Boolean, ForeignKey,
    DateTime, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

from .base import Base, TimestampMixin


class DataSourceType:
    """Constantes para tipos de data source."""
    PORTAL_API = "portal_api"
    CUSTOM_API = "custom_api"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class DataSource(Base, TimestampMixin):
    """
    Fonte de dados configurável para um tenant.

    Cada tenant pode ter múltiplas fontes com diferentes prioridades.
    O sistema tenta cada fonte por ordem de prioridade até encontrar resultado.
    """

    __tablename__ = "data_sources"

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
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tipo: portal_api, custom_api, webhook, manual
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # =========================================================================
    # CONFIGURAÇÃO DE CONEXÃO (JSONB - varia por tipo)
    # =========================================================================

    # Armazena configuração específica do tipo:
    #
    # portal_api: {
    #   "base_url": "https://portalinvestimento.com",
    #   "regions": ["canoas", "poa", "sc", "pb"],
    #   "url_pattern": "/imoveis/{region}/{region}.json",
    #   "timeout": 5.0,
    #   "headers": {}
    # }
    #
    # custom_api: {
    #   "endpoint": "https://api.cliente.com/properties",
    #   "method": "GET",
    #   "auth_type": "bearer|basic|api_key|none",
    #   "headers": {},
    #   "response_path": "data.items",
    #   "code_field": "id",
    #   "lookup_endpoint": "/properties/{code}"
    # }
    #
    # webhook: {
    #   "secret_key": "webhook_secret_123",
    #   "expected_format": "json"
    # }
    #
    # manual: {} (usa tabela Products)
    config: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=False
    )

    # =========================================================================
    # CREDENCIAIS (criptografadas)
    # =========================================================================

    # Armazena credenciais criptografadas:
    # {
    #   "_encrypted": true,
    #   "data": "base64_encrypted_string"
    # }
    #
    # Quando descriptografado:
    # {
    #   "api_key": "xxx",
    #   "token": "xxx",
    #   "username": "xxx",
    #   "password": "xxx"
    # }
    credentials_encrypted: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    # =========================================================================
    # MAPEAMENTO DE CAMPOS
    # =========================================================================

    # Mapeia campos externos para schema interno:
    # {
    #   "codigo": "code",
    #   "titulo": "title",
    #   "tipo": "type",
    #   "regiao": "region",
    #   "preco": "price",
    #   "quartos": "bedrooms",
    #   "banheiros": "bathrooms",
    #   "vagas": "parking",
    #   "metragem": "area",
    #   "descricao": "description"
    # }
    field_mapping: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    # =========================================================================
    # CACHE
    # =========================================================================

    cache_ttl_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,  # 5 minutos
        nullable=False
    )
    cache_strategy: Mapped[str] = mapped_column(
        String(50),
        default="memory",  # memory, redis, none
        nullable=False
    )

    # =========================================================================
    # STATUS DE SINCRONIZAÇÃO
    # =========================================================================

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_sync_status: Mapped[Optional[str]] = mapped_column(
        String(50),  # success, partial, failed
        nullable=True
    )
    last_sync_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================

    tenant = relationship("Tenant", back_populates="data_sources")

    # =========================================================================
    # ÍNDICES
    # =========================================================================

    __table_args__ = (
        Index("ix_data_sources_tenant_active", "tenant_id", "active"),
        Index("ix_data_sources_tenant_slug", "tenant_id", "slug", unique=True),
        Index("ix_data_sources_tenant_priority", "tenant_id", "priority"),
    )

    def __repr__(self) -> str:
        return f"<DataSource {self.name} ({self.type}) tenant={self.tenant_id}>"
