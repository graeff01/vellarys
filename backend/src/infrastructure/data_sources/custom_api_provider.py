"""
CUSTOM API PROVIDER
===================

Provider para APIs REST genéricas com autenticação configurável.

Exemplo de configuração:
{
    "endpoint": "https://api.cliente.com/properties",
    "method": "GET",
    "auth_type": "bearer",  # none, bearer, basic, api_key
    "headers": {},
    "response_path": "data.items",  # caminho para array de itens
    "code_field": "id",  # campo que contém o código
    "lookup_endpoint": "/properties/{code}",  # endpoint para busca por código
    "pagination": {
        "enabled": false,
        "page_param": "page",
        "limit_param": "limit",
        "limit": 100
    }
}

Credenciais (criptografadas):
{
    "api_key": "xxx",
    "token": "xxx",
    "username": "xxx",
    "password": "xxx",
    "key_name": "X-API-Key",
    "key_value": "xxx"
}
"""

import base64
import logging
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin

from .interface import (
    DataSourceProvider,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)

logger = logging.getLogger(__name__)


class CustomAPIProvider(DataSourceProvider):
    """
    Provider para APIs REST genéricas.

    Suporta:
    - Múltiplos métodos HTTP (GET, POST)
    - Autenticação: Bearer, Basic, API Key, Custom Headers
    - Mapeamento de campos flexível
    - Paginação configurável
    """

    def _validate_config(self) -> None:
        """Valida configuração da API."""
        required = ["endpoint"]
        for field in required:
            if field not in self.config.config:
                raise ValueError(f"CustomAPIProvider requires '{field}' in config")

    @property
    def endpoint(self) -> str:
        return self.config.config["endpoint"]

    @property
    def method(self) -> str:
        return self.config.config.get("method", "GET").upper()

    @property
    def custom_headers(self) -> Dict[str, str]:
        return self.config.config.get("headers", {})

    @property
    def auth_type(self) -> Optional[str]:
        return self.config.config.get("auth_type", "none")

    @property
    def response_path(self) -> Optional[str]:
        """Caminho JSON para array de itens (ex: "data.items")."""
        return self.config.config.get("response_path")

    @property
    def code_field(self) -> str:
        """Nome do campo que contém o código/ID."""
        return self.config.config.get("code_field", "id")

    @property
    def lookup_endpoint(self) -> Optional[str]:
        """Endpoint para busca por código (ex: "/properties/{code}")."""
        return self.config.config.get("lookup_endpoint")

    @property
    def search_endpoint(self) -> Optional[str]:
        """Endpoint para busca com critérios."""
        return self.config.config.get("search_endpoint")

    @property
    def timeout(self) -> float:
        return self.config.config.get("timeout", 10.0)

    def _build_headers(self) -> Dict[str, str]:
        """Constrói headers com autenticação."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.custom_headers
        }

        creds = self.config.credentials or {}

        if self.auth_type == "bearer":
            token = creds.get("token") or creds.get("api_key")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == "api_key":
            key_name = creds.get("key_name", "X-API-Key")
            key_value = creds.get("key_value") or creds.get("api_key")
            if key_value:
                headers[key_name] = key_value

        elif self.auth_type == "basic":
            username = creds.get("username", "")
            password = creds.get("password", "")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    def _extract_items(self, response_data: Any) -> List[Dict]:
        """Extrai array de itens do response usando response_path."""
        if not self.response_path:
            if isinstance(response_data, list):
                return response_data
            return []

        # Navega pelo caminho (ex: "data.items")
        parts = self.response_path.split(".")
        current = response_data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, [])
            else:
                return []

        return current if isinstance(current, list) else []

    async def _fetch_api(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Optional[Any]:
        """Faz request para a API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._build_headers(),
                    params=params,
                    json=body if method == "POST" else None
                )

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.warning(
                        f"[CustomAPI] HTTP {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    return None

        except Exception as e:
            logger.error(f"[CustomAPI] Request error: {type(e).__name__}: {e}")
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexão com a API."""
        try:
            data = await self._fetch_api(self.endpoint, self.method)

            if data is not None:
                items = self._extract_items(data)
                return {
                    "success": True,
                    "message": f"Conectado. {len(items)} itens encontrados.",
                    "details": {"count": len(items), "endpoint": self.endpoint}
                }
            else:
                return {
                    "success": False,
                    "message": "Falha ao conectar com a API",
                    "details": {"endpoint": self.endpoint}
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "details": {}
            }

    async def lookup_by_code(self, code: str) -> Optional[PropertyResult]:
        """Busca item por código."""
        code = str(code).strip()
        logger.info(f"[CustomAPI] Buscando código: {code}")

        if not code:
            return None

        # Se tem endpoint de lookup específico, usa
        if self.lookup_endpoint:
            url = urljoin(
                self.endpoint,
                self.lookup_endpoint.format(code=code)
            )
            data = await self._fetch_api(url)

            if data:
                # Se response_path configurado, extrai
                if self.response_path:
                    items = self._extract_items(data)
                    if items:
                        return self._to_property_result(items[0])
                else:
                    # Assume que retornou objeto direto
                    if isinstance(data, dict):
                        return self._to_property_result(data)

        # Fallback: busca todos e filtra
        all_items = await self._fetch_all()
        for item in all_items:
            if str(item.get(self.code_field, "")) == code:
                return self._to_property_result(item)

        logger.warning(f"[CustomAPI] Código {code} não encontrado")
        return None

    async def _fetch_all(self) -> List[Dict]:
        """Busca todos os itens da API."""
        data = await self._fetch_api(self.endpoint, self.method)
        if data:
            return self._extract_items(data)
        return []

    async def search(self, criteria: SearchCriteria) -> List[PropertyResult]:
        """Busca por critérios."""
        logger.info(f"[CustomAPI] Busca por critérios: {criteria}")

        # Se tem endpoint de busca específico
        if self.search_endpoint:
            params = self._criteria_to_params(criteria)
            url = urljoin(self.endpoint, self.search_endpoint)
            data = await self._fetch_api(url, params=params)
            if data:
                items = self._extract_items(data)
                return [self._to_property_result(item) for item in items[:criteria.limit]]

        # Fallback: busca todos e filtra localmente
        all_items = await self._fetch_all()
        results = []

        for item in all_items:
            if self._matches_criteria(item, criteria):
                results.append(self._to_property_result(item))
                if len(results) >= criteria.limit:
                    break

        return results

    def _criteria_to_params(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Converte critérios para parâmetros de query."""
        params = {}

        if criteria.region:
            params["region"] = criteria.region
        if criteria.type:
            params["type"] = criteria.type
        if criteria.price_max:
            params["price_max"] = criteria.price_max
        if criteria.price_min:
            params["price_min"] = criteria.price_min
        if criteria.bedrooms_min:
            params["bedrooms_min"] = criteria.bedrooms_min
        if criteria.limit:
            params["limit"] = criteria.limit

        return params

    def _matches_criteria(self, item: Dict, criteria: SearchCriteria) -> bool:
        """Filtra item por critérios (quando API não suporta filtros)."""
        mapped = self._apply_field_mapping(item)

        # Preço máximo
        if criteria.price_max:
            price = self._safe_float(mapped.get("price", item.get("price", 0)))
            if price and price > criteria.price_max:
                return False

        # Preço mínimo
        if criteria.price_min:
            price = self._safe_float(mapped.get("price", item.get("price", 0)))
            if price and price < criteria.price_min:
                return False

        # Quartos mínimos
        if criteria.bedrooms_min:
            bedrooms = self._safe_int(mapped.get("bedrooms", item.get("bedrooms", 0)))
            if bedrooms and bedrooms < criteria.bedrooms_min:
                return False

        # Tipo
        if criteria.type:
            item_type = str(mapped.get("type", item.get("type", ""))).lower()
            if criteria.type.lower() not in item_type:
                return False

        # Região
        if criteria.region:
            item_region = str(mapped.get("region", item.get("region", ""))).lower()
            if criteria.region.lower() not in item_region:
                return False

        return True

    async def sync_all(self) -> Dict[str, Any]:
        """Sincroniza todos os itens."""
        try:
            items = await self._fetch_all()
            return {
                "success": True,
                "count": len(items),
                "errors": []
            }
        except Exception as e:
            return {
                "success": False,
                "count": 0,
                "errors": [{"error": str(e)}]
            }

    def _to_property_result(self, item: Dict) -> PropertyResult:
        """Converte item para PropertyResult usando field_mapping."""
        mapped = self._apply_field_mapping(item)

        return PropertyResult(
            code=str(mapped.get("code", item.get(self.code_field, ""))),
            title=mapped.get("title", item.get("name", item.get("title", ""))),
            type=mapped.get("type", item.get("type", "")),
            region=mapped.get("region", item.get("region", item.get("location", ""))),
            price=self._safe_float(mapped.get("price", item.get("price"))),
            price_formatted=self._format_price(mapped.get("price", item.get("price"))),
            bedrooms=self._safe_int(mapped.get("bedrooms", item.get("bedrooms"))),
            bathrooms=self._safe_int(mapped.get("bathrooms", item.get("bathrooms"))),
            parking=self._safe_int(mapped.get("parking", item.get("parking"))),
            area=self._safe_float(mapped.get("area", item.get("area"))),
            description=mapped.get("description", item.get("description", "")),
            link=mapped.get("link", item.get("url", item.get("link"))),
            images=item.get("images", []),
            attributes=mapped.get("attributes", {}),
            source_id=self.config.source_id,
            source_type=self.config.type,
            raw_data=item
        )
