"""
PORTAL API PROVIDER
===================

Provider para APIs JSON de portais imobiliários.
Migrado do código original de PropertyLookupService.

Exemplo de configuração:
{
    "base_url": "https://portalinvestimento.com",
    "regions": ["canoas", "poa", "sc", "pb"],
    "url_pattern": "/imoveis/{region}/{region}.json",
    "timeout": 5.0,
    "fallback_file": "data/fallback_canoas.json"
}
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from .interface import (
    DataSourceProvider,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)

logger = logging.getLogger(__name__)


class PortalAPIProvider(DataSourceProvider):
    """
    Provider para APIs JSON de portais imobiliários.

    Espera endpoints que retornam arrays JSON de imóveis.
    Suporta múltiplas regiões e fallback para arquivo local.
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # Cache em memória por região
    _region_cache: Dict[str, tuple] = {}

    def _validate_config(self) -> None:
        """Valida configuração do portal."""
        required = ["base_url"]
        for field in required:
            if field not in self.config.config:
                raise ValueError(f"PortalAPIProvider requires '{field}' in config")

    @property
    def base_url(self) -> str:
        return self.config.config["base_url"].rstrip("/")

    @property
    def regions(self) -> List[str]:
        return self.config.config.get("regions", [])

    @property
    def timeout(self) -> float:
        return self.config.config.get("timeout", 5.0)

    @property
    def url_pattern(self) -> str:
        return self.config.config.get(
            "url_pattern",
            "/imoveis/{region}/{region}.json"
        )

    @property
    def fallback_file(self) -> Optional[str]:
        return self.config.config.get("fallback_file")

    @property
    def headers(self) -> Dict[str, str]:
        custom = self.config.config.get("headers", {})
        return {**self.DEFAULT_HEADERS, **custom}

    def _get_cache(self, key: str) -> Optional[Any]:
        """Obtém valor do cache se não expirado."""
        cache_key = f"{self.config.source_id}_{key}"
        if cache_key in self._region_cache:
            value, expires = self._region_cache[cache_key]
            if datetime.now() < expires:
                return value
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Armazena valor no cache."""
        cache_key = f"{self.config.source_id}_{key}"
        ttl = self.config.cache_ttl or 300
        self._region_cache[cache_key] = (
            value,
            datetime.now() + timedelta(seconds=ttl)
        )

    def _build_region_url(self, region: str) -> str:
        """Constrói URL para uma região específica."""
        pattern = self.url_pattern.format(region=region)
        return f"{self.base_url}{pattern}"

    async def _fetch_http(self, url: str) -> Optional[List[Dict]]:
        """
        Faz request HTTP com múltiplas bibliotecas como fallback.
        """
        # Tenta com httpx primeiro (async nativo)
        try:
            import httpx
            logger.debug(f"[PortalAPI] Tentando httpx: {url}")
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.debug(f"[PortalAPI] httpx OK - {len(response.json())} items")
                    return response.json()
                else:
                    logger.warning(f"[PortalAPI] httpx Status: {response.status_code}")
        except Exception as e:
            logger.error(f"[PortalAPI] httpx erro: {type(e).__name__}: {e}")

        # Fallback para requests (sync)
        try:
            import requests
            logger.debug(f"[PortalAPI] Tentando requests: {url}")
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self.headers
            )
            if response.status_code == 200:
                logger.debug(f"[PortalAPI] requests OK")
                return response.json()
        except Exception as e:
            logger.error(f"[PortalAPI] requests erro: {type(e).__name__}: {e}")

        # Fallback para urllib
        try:
            import urllib.request
            logger.debug(f"[PortalAPI] Tentando urllib: {url}")
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    logger.debug(f"[PortalAPI] urllib OK")
                    return data
        except Exception as e:
            logger.error(f"[PortalAPI] urllib erro: {type(e).__name__}: {e}")

        return None

    async def _load_region(self, region: str) -> Optional[List[Dict]]:
        """Carrega dados de uma região específica."""
        # Verifica cache
        cached = self._get_cache(f"region_{region}")
        if cached:
            logger.debug(f"[PortalAPI] Região {region} do cache")
            return cached

        # Busca da API
        url = self._build_region_url(region)
        logger.info(f"[PortalAPI] Buscando {url}")
        data = await self._fetch_http(url)

        # Fallback para arquivo local (se configurado)
        if not data and self.fallback_file:
            # Verifica se é a região do fallback (geralmente a primeira)
            fallback_region = self.regions[0] if self.regions else None
            if region == fallback_region and os.path.exists(self.fallback_file):
                logger.warning(f"[PortalAPI] Usando fallback local: {self.fallback_file}")
                try:
                    with open(self.fallback_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    logger.error(f"[PortalAPI] Erro ao carregar fallback: {e}")

        if data:
            self._set_cache(f"region_{region}", data)
            logger.info(f"[PortalAPI] {len(data)} imóveis carregados de {region}")

        return data

    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexão com o portal."""
        try:
            if not self.regions:
                return {
                    "success": False,
                    "message": "Nenhuma região configurada",
                    "details": {}
                }

            region = self.regions[0]
            url = self._build_region_url(region)
            data = await self._fetch_http(url)

            if data:
                return {
                    "success": True,
                    "message": f"Conectado. {len(data)} imóveis em {region}.",
                    "details": {
                        "region": region,
                        "count": len(data),
                        "url": url
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Falha ao conectar com {url}",
                    "details": {"url": url}
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "details": {}
            }

    async def lookup_by_code(self, code: str) -> Optional[PropertyResult]:
        """Busca imóvel pelo código em todas as regiões."""
        code = str(code).strip()
        logger.info(f"[PortalAPI] Buscando código: {code}")

        if not code:
            return None

        # Verifica cache por código
        cached = self._get_cache(f"code_{code}")
        if cached:
            logger.info(f"[PortalAPI] Código {code} do cache")
            return cached

        # Busca em todas as regiões
        for region in self.regions:
            properties = await self._load_region(region)

            if not properties:
                continue

            for prop in properties:
                prop_code = str(prop.get("codigo", ""))
                if prop_code == code:
                    result = self._to_property_result(prop, region)
                    self._set_cache(f"code_{code}", result)
                    logger.info(f"[PortalAPI] Encontrado {code} em {region}")
                    return result

        logger.warning(f"[PortalAPI] Código {code} não encontrado")
        return None

    async def search(self, criteria: SearchCriteria) -> List[PropertyResult]:
        """Busca imóveis por critérios."""
        logger.info(f"[PortalAPI] Busca por critérios: {criteria}")
        results = []

        for region in self.regions:
            # Filtro por região se especificada
            if criteria.region:
                if criteria.region.lower() not in region.lower():
                    continue

            properties = await self._load_region(region)

            if not properties:
                continue

            for prop in properties:
                if self._matches_criteria(prop, criteria):
                    results.append(self._to_property_result(prop, region))

                    if len(results) >= criteria.limit:
                        break

            if len(results) >= criteria.limit:
                break

        logger.info(f"[PortalAPI] {len(results)} resultados encontrados")
        return results

    async def sync_all(self) -> Dict[str, Any]:
        """Sincroniza dados de todas as regiões."""
        total = 0
        errors = []

        for region in self.regions:
            try:
                properties = await self._load_region(region)
                if properties:
                    total += len(properties)
                else:
                    errors.append({"region": region, "error": "Sem dados"})
            except Exception as e:
                errors.append({"region": region, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "count": total,
            "errors": errors
        }

    def _matches_criteria(self, prop: Dict, criteria: SearchCriteria) -> bool:
        """Verifica se imóvel atende aos critérios."""
        # Filtro por região/bairro
        if criteria.region:
            prop_region = str(prop.get("regiao", "")).lower()
            if criteria.region.lower() not in prop_region:
                return False

        # Filtro por tipo
        if criteria.type:
            prop_type = str(prop.get("tipo", "")).lower()
            if criteria.type.lower() not in prop_type:
                return False

        # Filtro por preço máximo
        if criteria.price_max:
            try:
                price = int(prop.get("preco", 0))
                if price > criteria.price_max or price == 0:
                    return False
            except (ValueError, TypeError):
                pass

        # Filtro por preço mínimo
        if criteria.price_min:
            try:
                price = int(prop.get("preco", 0))
                if price < criteria.price_min:
                    return False
            except (ValueError, TypeError):
                pass

        # Filtro por quartos mínimos
        if criteria.bedrooms_min:
            try:
                bedrooms = int(prop.get("quartos", 0))
                if bedrooms < criteria.bedrooms_min:
                    return False
            except (ValueError, TypeError):
                pass

        # Filtro por área mínima
        if criteria.area_min:
            try:
                area = float(prop.get("metragem", 0))
                if area < criteria.area_min:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def _to_property_result(self, prop: Dict, region: str) -> PropertyResult:
        """Converte dados brutos para PropertyResult."""
        # Aplica mapeamento de campos se configurado
        mapped = self._apply_field_mapping(prop)

        # Formata preço
        price = prop.get("preco")
        price_formatted = self._format_price(price)

        # Monta link
        code = str(prop.get("codigo", ""))
        link = f"{self.base_url}/imovel.html?codigo={code}" if code else None

        return PropertyResult(
            code=code,
            title=mapped.get("title", prop.get("titulo", "Imóvel")),
            type=mapped.get("type", prop.get("tipo", "Imóvel")),
            region=mapped.get("region", prop.get("regiao", region.upper())),
            price=self._safe_float(price),
            price_formatted=price_formatted,
            bedrooms=self._safe_int(prop.get("quartos")),
            bathrooms=self._safe_int(prop.get("banheiros")),
            parking=self._safe_int(prop.get("vagas")),
            area=self._safe_float(prop.get("metragem")),
            description=prop.get("descricao", ""),
            link=link,
            agent_name=prop.get("corretor_nome"),
            agent_whatsapp=prop.get("corretor_whatsapp"),
            attributes=mapped.get("attributes", {}),
            source_id=self.config.source_id,
            source_type=self.config.type,
            raw_data=prop
        )
