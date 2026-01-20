"""
MANUAL PROVIDER
===============

Provider que usa a tabela Products local do banco de dados.
Para tenants que não têm API externa e cadastram produtos manualmente.

Configuração mínima - usa a tabela Products existente.
"""

import logging
from typing import Optional, Dict, List, Any

from .interface import (
    DataSourceProvider,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)

logger = logging.getLogger(__name__)


class ManualProvider(DataSourceProvider):
    """
    Provider que busca dados da tabela Products local.

    Não requer configuração externa - usa os produtos cadastrados
    no sistema para o tenant.
    """

    # Referência para sessão de banco (injetada em runtime)
    _db_session = None

    def _validate_config(self) -> None:
        """Configuração mínima - sempre válido."""
        pass

    @property
    def include_inactive(self) -> bool:
        return self.config.config.get("include_inactive", False)

    @property
    def default_status(self) -> Optional[str]:
        return self.config.config.get("default_status")

    def set_db_session(self, db_session) -> None:
        """
        Injeta sessão de banco de dados.
        Deve ser chamado antes de usar o provider.
        """
        self._db_session = db_session

    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexão verificando se consegue acessar Products."""
        try:
            if not self._db_session:
                return {
                    "success": False,
                    "message": "Sessão de banco não configurada",
                    "details": {}
                }

            # Importa aqui para evitar circular
            from sqlalchemy import select, func
            from src.domain.entities import Product

            result = await self._db_session.execute(
                select(func.count(Product.id))
                .where(Product.tenant_id == self.config.tenant_id)
                .where(Product.active == True)
            )
            count = result.scalar() or 0

            return {
                "success": True,
                "message": f"Conectado. {count} produtos ativos.",
                "details": {"count": count}
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "details": {}
            }

    async def lookup_by_code(self, code: str) -> Optional[PropertyResult]:
        """Busca produto por código (slug ou ID)."""
        code = str(code).strip()
        logger.info(f"[Manual] Buscando código: {code}")

        if not code or not self._db_session:
            return None

        try:
            from sqlalchemy import select, or_
            from src.domain.entities import Product

            # Busca por slug ou por código em attributes
            query = (
                select(Product)
                .where(Product.tenant_id == self.config.tenant_id)
                .where(
                    or_(
                        Product.slug == code,
                        Product.attributes["codigo"].astext == code
                    )
                )
            )

            if not self.include_inactive:
                query = query.where(Product.active == True)

            result = await self._db_session.execute(query)
            product = result.scalar_one_or_none()

            if product:
                logger.info(f"[Manual] Encontrado: {product.name}")
                return self._product_to_result(product)

            logger.warning(f"[Manual] Código {code} não encontrado")
            return None

        except Exception as e:
            logger.error(f"[Manual] Erro ao buscar: {e}")
            return None

    async def search(self, criteria: SearchCriteria) -> List[PropertyResult]:
        """Busca produtos por critérios."""
        logger.info(f"[Manual] Busca por critérios: {criteria}")

        if not self._db_session:
            return []

        try:
            from sqlalchemy import select
            from src.domain.entities import Product

            query = (
                select(Product)
                .where(Product.tenant_id == self.config.tenant_id)
            )

            if not self.include_inactive:
                query = query.where(Product.active == True)

            # Ordena por prioridade
            query = query.order_by(Product.priority.desc())

            # Limite
            query = query.limit(criteria.limit)

            result = await self._db_session.execute(query)
            products = result.scalars().all()

            # Filtra em memória por critérios específicos
            results = []
            for product in products:
                if self._matches_criteria(product, criteria):
                    results.append(self._product_to_result(product))

            logger.info(f"[Manual] {len(results)} resultados encontrados")
            return results

        except Exception as e:
            logger.error(f"[Manual] Erro ao buscar: {e}")
            return []

    async def sync_all(self) -> Dict[str, Any]:
        """Conta produtos (não há sync externo para Manual)."""
        try:
            if not self._db_session:
                return {
                    "success": False,
                    "count": 0,
                    "errors": [{"error": "Sessão de banco não configurada"}]
                }

            from sqlalchemy import select, func
            from src.domain.entities import Product

            result = await self._db_session.execute(
                select(func.count(Product.id))
                .where(Product.tenant_id == self.config.tenant_id)
                .where(Product.active == True)
            )
            count = result.scalar() or 0

            return {
                "success": True,
                "count": count,
                "errors": [],
                "message": "Produtos locais contados (sem sync externo)"
            }
        except Exception as e:
            return {
                "success": False,
                "count": 0,
                "errors": [{"error": str(e)}]
            }

    def _matches_criteria(self, product, criteria: SearchCriteria) -> bool:
        """Filtra produto por critérios."""
        attrs = product.attributes or {}

        # Preço máximo
        if criteria.price_max:
            price = self._safe_float(attrs.get("preco", attrs.get("price", 0)))
            if price and price > criteria.price_max:
                return False

        # Preço mínimo
        if criteria.price_min:
            price = self._safe_float(attrs.get("preco", attrs.get("price", 0)))
            if price and price < criteria.price_min:
                return False

        # Quartos mínimos
        if criteria.bedrooms_min:
            bedrooms = self._safe_int(attrs.get("quartos", attrs.get("bedrooms", 0)))
            if bedrooms and bedrooms < criteria.bedrooms_min:
                return False

        # Tipo
        if criteria.type:
            product_type = str(attrs.get("tipo", attrs.get("type", ""))).lower()
            if criteria.type.lower() not in product_type:
                return False

        # Região
        if criteria.region:
            product_region = str(attrs.get("regiao", attrs.get("region", ""))).lower()
            if criteria.region.lower() not in product_region:
                return False

        return True

    def _product_to_result(self, product) -> PropertyResult:
        """Converte Product para PropertyResult."""
        attrs = product.attributes or {}

        # Aplica mapeamento de campos se configurado
        mapped = self._apply_field_mapping(attrs)

        return PropertyResult(
            code=str(mapped.get("code", attrs.get("codigo", product.slug))),
            title=mapped.get("title", product.name),
            type=mapped.get("type", attrs.get("tipo", "")),
            region=mapped.get("region", attrs.get("regiao", "")),
            price=self._safe_float(mapped.get("price", attrs.get("preco"))),
            price_formatted=self._format_price(mapped.get("price", attrs.get("preco"))),
            bedrooms=self._safe_int(mapped.get("bedrooms", attrs.get("quartos"))),
            bathrooms=self._safe_int(mapped.get("bathrooms", attrs.get("banheiros"))),
            parking=self._safe_int(mapped.get("parking", attrs.get("vagas"))),
            area=self._safe_float(mapped.get("area", attrs.get("metragem"))),
            description=mapped.get("description", product.description or ""),
            link=attrs.get("link"),
            agent_name=attrs.get("corretor_nome"),
            agent_whatsapp=attrs.get("corretor_whatsapp"),
            attributes=mapped.get("attributes", attrs),
            source_id=self.config.source_id,
            source_type=self.config.type,
            raw_data={"product_id": product.id, **attrs}
        )
