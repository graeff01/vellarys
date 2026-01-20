"""
DATA SOURCE PROVIDER INTERFACE
==============================

Interface abstrata para todos os providers de data source.
Cada provider concreto deve implementar estes métodos.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class DataSourceConfig:
    """Configuração para um provider de data source."""

    source_id: int
    tenant_id: int
    type: str
    config: Dict[str, Any]
    credentials: Dict[str, Any]
    field_mapping: Dict[str, str]
    cache_ttl: int = 300


@dataclass
class PropertyResult:
    """Resultado padronizado de busca de imóvel/produto."""

    code: str
    title: str
    type: str
    region: str
    price: Optional[float] = None
    price_formatted: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking: Optional[int] = None
    area: Optional[float] = None
    description: Optional[str] = None
    link: Optional[str] = None
    images: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_id: Optional[int] = None
    source_type: Optional[str] = None
    raw_data: Optional[Dict] = None

    # Campos extras para contexto de IA
    agent_name: Optional[str] = None
    agent_whatsapp: Optional[str] = None


@dataclass
class SearchCriteria:
    """Critérios de busca para imóveis/produtos."""

    code: Optional[str] = None
    region: Optional[str] = None
    type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    keywords: Optional[List[str]] = None
    limit: int = 10


class DataSourceProvider(ABC):
    """
    Classe abstrata base para providers de data source.

    Todos os providers concretos devem implementar estes métodos:
    - test_connection(): Testa se a conexão está funcionando
    - lookup_by_code(): Busca item por código
    - search(): Busca por critérios
    - sync_all(): Sincroniza todos os dados (opcional)
    """

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Valida a configuração específica do provider.
        Deve lançar ValueError se configuração inválida.
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão com a fonte de dados.

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "details": dict
            }
        """
        pass

    @abstractmethod
    async def lookup_by_code(self, code: str) -> Optional[PropertyResult]:
        """
        Busca um item pelo código/ID.

        Args:
            code: Código do item (ex: "722585")

        Returns:
            PropertyResult ou None se não encontrado
        """
        pass

    @abstractmethod
    async def search(self, criteria: SearchCriteria) -> List[PropertyResult]:
        """
        Busca itens por critérios.

        Args:
            criteria: Critérios de busca

        Returns:
            Lista de PropertyResult
        """
        pass

    async def sync_all(self) -> Dict[str, Any]:
        """
        Sincroniza todos os dados da fonte (opcional).

        Returns:
            dict: {
                "success": bool,
                "count": int,
                "errors": list
            }
        """
        return {
            "success": True,
            "count": 0,
            "errors": [],
            "message": "Sync not implemented for this provider"
        }

    def _apply_field_mapping(self, raw: Dict) -> Dict:
        """
        Aplica mapeamento de campos do schema externo para interno.

        Args:
            raw: Dados brutos da fonte externa

        Returns:
            Dados com campos mapeados
        """
        if not self.config.field_mapping:
            return raw

        mapped = {}
        mapped_externals = set()

        for external_key, internal_key in self.config.field_mapping.items():
            if external_key in raw:
                mapped[internal_key] = raw[external_key]
                mapped_externals.add(external_key)

        # Campos não mapeados vão para attributes
        for key, value in raw.items():
            if key not in mapped_externals:
                if "attributes" not in mapped:
                    mapped["attributes"] = {}
                mapped["attributes"][key] = value

        return mapped

    def _format_price(self, price: Any) -> str:
        """
        Formata preço em Real brasileiro.

        Args:
            price: Valor do preço (int, float, str)

        Returns:
            Preço formatado (ex: "R$ 500.000")
        """
        if not price:
            return "Consulte"

        try:
            # Remove caracteres não numéricos exceto ponto e vírgula
            if isinstance(price, str):
                cleaned = price.replace(".", "").replace(",", ".").strip()
                cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")
                valor = float(cleaned) if cleaned else 0
            else:
                valor = float(price)

            if valor <= 0:
                return "Consulte"

            # Formata como moeda brasileira
            return f"R$ {valor:,.0f}".replace(",", ".")

        except (ValueError, TypeError):
            return "Consulte"

    def _safe_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        """Converte valor para int de forma segura."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Converte valor para float de forma segura."""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.replace(",", ".")
            return float(value)
        except (ValueError, TypeError):
            return default
