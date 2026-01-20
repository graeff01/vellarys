"""
DATA SOURCE FACTORY
===================

Factory para criar instâncias de providers baseado no tipo.
Segue o padrão já utilizado no LLMFactory e WhatsAppService.
"""

import logging
from typing import Optional, Dict, Type

from .interface import DataSourceProvider, DataSourceConfig

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """
    Factory para criar instâncias de data source providers.

    Uso:
        config = DataSourceConfig(...)
        provider = DataSourceFactory.get_provider(config)
        result = await provider.lookup_by_code("722585")
    """

    # Registry de providers disponíveis
    _providers: Dict[str, Type[DataSourceProvider]] = {}

    # Cache de instâncias por source_id
    _instances: Dict[int, DataSourceProvider] = {}

    @classmethod
    def register_provider(cls, type_name: str, provider_class: Type[DataSourceProvider]) -> None:
        """
        Registra um novo tipo de provider.

        Args:
            type_name: Nome do tipo (ex: "portal_api")
            provider_class: Classe do provider
        """
        cls._providers[type_name] = provider_class
        logger.info(f"Registered data source provider: {type_name}")

    @classmethod
    def get_provider(
        cls,
        config: DataSourceConfig,
        force_new: bool = False
    ) -> DataSourceProvider:
        """
        Obtém ou cria um provider para a configuração dada.

        Args:
            config: Configuração do data source
            force_new: Se True, cria nova instância mesmo se existir no cache

        Returns:
            Instância do provider

        Raises:
            ValueError: Se tipo de provider não registrado
        """
        cache_key = config.source_id

        # Retorna do cache se existir e não for forçado
        if not force_new and cache_key in cls._instances:
            logger.debug(f"Returning cached provider for source {cache_key}")
            return cls._instances[cache_key]

        # Busca classe do provider
        provider_class = cls._providers.get(config.type)

        if not provider_class:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown data source type: {config.type}. "
                f"Available: {available}"
            )

        logger.info(
            f"Creating {config.type} provider for source {config.source_id} "
            f"(tenant {config.tenant_id})"
        )

        # Cria instância
        instance = provider_class(config)

        # Armazena no cache
        cls._instances[cache_key] = instance

        return instance

    @classmethod
    def clear_cache(cls, source_id: Optional[int] = None) -> None:
        """
        Limpa cache de instâncias.

        Args:
            source_id: Se fornecido, limpa apenas esse. Senão, limpa todos.
        """
        if source_id is not None:
            removed = cls._instances.pop(source_id, None)
            if removed:
                logger.info(f"Cleared cache for source {source_id}")
        else:
            count = len(cls._instances)
            cls._instances.clear()
            logger.info(f"Cleared all {count} cached providers")

    @classmethod
    def list_provider_types(cls) -> list:
        """Lista tipos de providers disponíveis."""
        return list(cls._providers.keys())

    @classmethod
    def is_type_registered(cls, type_name: str) -> bool:
        """Verifica se um tipo está registrado."""
        return type_name in cls._providers


# =============================================================================
# AUTO-REGISTRO DOS PROVIDERS
# =============================================================================

def _register_providers():
    """Registra todos os providers disponíveis."""
    from .portal_api_provider import PortalAPIProvider
    from .custom_api_provider import CustomAPIProvider
    from .manual_provider import ManualProvider
    from .webhook_provider import WebhookProvider

    DataSourceFactory.register_provider("portal_api", PortalAPIProvider)
    DataSourceFactory.register_provider("custom_api", CustomAPIProvider)
    DataSourceFactory.register_provider("manual", ManualProvider)
    DataSourceFactory.register_provider("webhook", WebhookProvider)


# Registra providers ao importar o módulo
try:
    _register_providers()
except ImportError as e:
    logger.warning(f"Could not register all providers: {e}")
