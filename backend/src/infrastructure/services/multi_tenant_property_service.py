"""
MULTI-TENANT PROPERTY LOOKUP SERVICE
====================================

Serviço de busca de imóveis/produtos que usa DataSources configuráveis.
Substitui o PropertyLookupService hardcoded original.

Uso:
    service = MultiTenantPropertyService(db, tenant_id)
    result = await service.buscar_por_codigo("722585")
"""

import logging
from typing import Optional, Dict, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import DataSource
from src.infrastructure.data_sources import (
    DataSourceFactory,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)
from src.infrastructure.services.encryption_service import decrypt_credentials

logger = logging.getLogger(__name__)


class MultiTenantPropertyService:
    """
    Serviço de busca de imóveis/produtos multi-tenant.

    Carrega DataSources configurados para o tenant e tenta cada um
    por ordem de prioridade até encontrar resultado.
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self._sources: List[DataSource] = []
        self._providers: List[tuple] = []
        self._loaded = False

    async def _load_sources(self) -> None:
        """Carrega e inicializa data sources do tenant."""
        if self._loaded:
            return

        # Busca data sources ativos ordenados por prioridade
        result = await self.db.execute(
            select(DataSource)
            .where(DataSource.tenant_id == self.tenant_id)
            .where(DataSource.active == True)
            .order_by(DataSource.priority.desc())
        )
        self._sources = list(result.scalars().all())

        logger.info(
            f"[PropertyService] Carregando {len(self._sources)} "
            f"data sources para tenant {self.tenant_id}"
        )

        # Inicializa providers para cada source
        for source in self._sources:
            try:
                # Descriptografa credenciais
                credentials = {}
                if source.credentials_encrypted:
                    credentials = decrypt_credentials(source.credentials_encrypted)

                # Cria configuração
                config = DataSourceConfig(
                    source_id=source.id,
                    tenant_id=source.tenant_id,
                    type=source.type,
                    config=source.config or {},
                    credentials=credentials,
                    field_mapping=source.field_mapping or {},
                    cache_ttl=source.cache_ttl_seconds,
                )

                # Obtém provider via factory
                provider = DataSourceFactory.get_provider(config)

                # Se for ManualProvider, injeta sessão de banco
                if source.type == "manual":
                    provider.set_db_session(self.db)

                self._providers.append((source, provider))
                logger.debug(f"[PropertyService] Provider {source.type} inicializado: {source.name}")

            except Exception as e:
                logger.error(
                    f"[PropertyService] Erro ao inicializar provider "
                    f"{source.name}: {e}"
                )

        self._loaded = True

    async def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """
        Busca imóvel/produto pelo código.

        Tenta cada data source por ordem de prioridade até encontrar.
        Mantém interface compatível com o PropertyLookupService original.

        Args:
            codigo: Código do imóvel (ex: "722585")

        Returns:
            Dict com dados do imóvel ou None se não encontrado
        """
        await self._load_sources()

        codigo = str(codigo).strip()
        if not codigo:
            return None

        logger.info(f"[PropertyService] Buscando código: {codigo}")

        # Tenta cada provider
        for source, provider in self._providers:
            try:
                result = await provider.lookup_by_code(codigo)

                if result:
                    logger.info(
                        f"[PropertyService] Encontrado em {source.name} "
                        f"({source.type})"
                    )
                    return self._to_legacy_dict(result)

            except Exception as e:
                logger.error(
                    f"[PropertyService] Erro em {source.name}: {e}"
                )
                continue

        logger.warning(f"[PropertyService] Código {codigo} não encontrado em nenhuma fonte")
        return None

    async def buscar_por_criterios(
        self,
        regiao: Optional[str] = None,
        tipo: Optional[str] = None,
        preco_max: Optional[int] = None,
        quartos_min: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Busca imóveis que atendam aos critérios.

        Agrega resultados de todas as fontes, removendo duplicatas.
        Mantém interface compatível com o PropertyLookupService original.

        Args:
            regiao: Filtro por região/bairro
            tipo: Filtro por tipo (Casa, Apartamento, etc)
            preco_max: Preço máximo
            quartos_min: Número mínimo de quartos
            limit: Máximo de resultados

        Returns:
            Lista de dicts com dados dos imóveis
        """
        await self._load_sources()

        logger.info(
            f"[PropertyService] Busca por critérios: "
            f"regiao={regiao}, tipo={tipo}, preco_max={preco_max}, "
            f"quartos_min={quartos_min}"
        )

        criteria = SearchCriteria(
            region=regiao,
            type=tipo,
            price_max=preco_max,
            bedrooms_min=quartos_min,
            limit=limit,
        )

        all_results: List[PropertyResult] = []

        # Busca em todas as fontes
        for source, provider in self._providers:
            try:
                results = await provider.search(criteria)
                all_results.extend(results)

                # Para se já tem resultados suficientes
                if len(all_results) >= limit * 2:  # Busca um pouco mais para deduplicar
                    break

            except Exception as e:
                logger.error(f"[PropertyService] Erro em {source.name}: {e}")
                continue

        # Remove duplicatas por código
        seen_codes = set()
        unique_results = []

        for result in all_results:
            if result.code and result.code not in seen_codes:
                seen_codes.add(result.code)
                unique_results.append(result)

        # Limita resultados
        final_results = unique_results[:limit]

        logger.info(f"[PropertyService] {len(final_results)} resultados encontrados")

        return [self._to_legacy_dict(r) for r in final_results]

    def _to_legacy_dict(self, result: PropertyResult) -> Dict[str, Any]:
        """
        Converte PropertyResult para formato legado.

        Mantém compatibilidade com o código existente que espera
        o formato do PropertyLookupService original.
        """
        return {
            "codigo": result.code,
            "titulo": result.title,
            "tipo": result.type,
            "regiao": result.region,
            "quartos": result.bedrooms if result.bedrooms else "Consulte",
            "banheiros": result.bathrooms if result.bathrooms else "Consulte",
            "vagas": result.parking if result.parking else "Consulte",
            "metragem": result.area if result.area else "Consulte",
            "preco": result.price_formatted or "Consulte",
            "descricao": result.description or "",
            "link": result.link or "",
            "corretor_nome": result.agent_name,
            "corretor_whatsapp": result.agent_whatsapp,
            # Metadados extras
            "_source_id": result.source_id,
            "_source_type": result.source_type,
        }


# =============================================================================
# FUNÇÕES AUXILIARES (compatibilidade com código existente)
# =============================================================================

async def get_property_service(
    db: AsyncSession,
    tenant_id: int
) -> MultiTenantPropertyService:
    """
    Factory function para criar PropertyService.

    Args:
        db: Sessão de banco de dados
        tenant_id: ID do tenant

    Returns:
        Instância de MultiTenantPropertyService
    """
    return MultiTenantPropertyService(db, tenant_id)


async def buscar_imovel_multi_tenant(
    db: AsyncSession,
    tenant_id: int,
    codigo: str
) -> Optional[Dict]:
    """
    Busca imóvel usando o serviço multi-tenant.

    Função utilitária para uso direto em outros módulos.
    """
    service = MultiTenantPropertyService(db, tenant_id)
    return await service.buscar_por_codigo(codigo)


async def buscar_imoveis_por_criterios_multi_tenant(
    db: AsyncSession,
    tenant_id: int,
    regiao: Optional[str] = None,
    tipo: Optional[str] = None,
    preco_max: Optional[int] = None,
    quartos_min: Optional[int] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Busca imóveis por critérios usando o serviço multi-tenant.

    Função utilitária para uso direto em outros módulos.
    """
    service = MultiTenantPropertyService(db, tenant_id)
    return await service.buscar_por_criterios(
        regiao=regiao,
        tipo=tipo,
        preco_max=preco_max,
        quartos_min=quartos_min,
        limit=limit
    )
