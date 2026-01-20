"""
DATA SOURCES - Sistema de fontes de dados configuráveis
=======================================================

Este módulo implementa o padrão Factory para permitir que cada tenant
configure suas próprias fontes de dados para lookup de imóveis/produtos.

Providers disponíveis:
- PortalAPIProvider: API JSON de portal (ex: portalinvestimento.com)
- CustomAPIProvider: API REST genérica com autenticação configurável
- WebhookProvider: Recebe dados via POST do sistema do cliente
- ManualProvider: Usa apenas a tabela Products local
"""

from .interface import (
    DataSourceProvider,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)
from .factory import DataSourceFactory

__all__ = [
    "DataSourceProvider",
    "DataSourceConfig",
    "PropertyResult",
    "SearchCriteria",
    "DataSourceFactory",
]
