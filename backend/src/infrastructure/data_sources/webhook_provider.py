"""
WEBHOOK PROVIDER
================

Provider para dados recebidos via webhook do sistema do cliente.
Os dados são armazenados localmente e consultados depois.

Configuração:
{
    "secret_key": "webhook_secret_123",  # para validar assinatura
    "expected_format": "json"
}

O webhook recebe POSTs em /webhooks/data-source/{source_id}
e armazena os dados para consulta posterior.
"""

import logging
import hashlib
import hmac
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from .interface import (
    DataSourceProvider,
    DataSourceConfig,
    PropertyResult,
    SearchCriteria,
)

logger = logging.getLogger(__name__)


class WebhookProvider(DataSourceProvider):
    """
    Provider para dados recebidos via webhook.

    Os dados são armazenados em cache/banco quando recebidos via POST
    e depois consultados por este provider.
    """

    # Cache em memória dos dados recebidos (em produção, usar Redis ou banco)
    _data_store: Dict[int, Dict[str, Any]] = {}

    def _validate_config(self) -> None:
        """Valida configuração do webhook."""
        # Secret key é opcional mas recomendado
        pass

    @property
    def secret_key(self) -> Optional[str]:
        return self.config.config.get("secret_key")

    @property
    def expected_format(self) -> str:
        return self.config.config.get("expected_format", "json")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifica assinatura HMAC do webhook.

        O cliente deve enviar header X-Webhook-Signature com:
        sha256=<hmac_hex_digest>
        """
        if not self.secret_key:
            return True  # Sem secret, aceita qualquer request

        if not signature:
            return False

        expected_sig = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Signature vem como "sha256=<digest>"
        if signature.startswith("sha256="):
            signature = signature[7:]

        return hmac.compare_digest(expected_sig, signature)

    def receive_data(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Recebe e armazena dados do webhook.

        Args:
            items: Lista de itens recebidos

        Returns:
            Status do recebimento
        """
        source_id = self.config.source_id

        if source_id not in self._data_store:
            self._data_store[source_id] = {
                "items": [],
                "received_at": None,
                "count": 0
            }

        # Atualiza dados
        self._data_store[source_id]["items"] = items
        self._data_store[source_id]["received_at"] = datetime.now()
        self._data_store[source_id]["count"] = len(items)

        logger.info(f"[Webhook] Recebidos {len(items)} itens para source {source_id}")

        return {
            "success": True,
            "count": len(items),
            "message": f"Recebidos {len(items)} itens"
        }

    def get_stored_items(self) -> List[Dict]:
        """Retorna itens armazenados."""
        source_id = self.config.source_id
        data = self._data_store.get(source_id, {})
        return data.get("items", [])

    async def test_connection(self) -> Dict[str, Any]:
        """Verifica se há dados armazenados."""
        source_id = self.config.source_id
        data = self._data_store.get(source_id, {})

        items = data.get("items", [])
        received_at = data.get("received_at")

        if items:
            time_str = received_at.isoformat() if received_at else "desconhecido"
            return {
                "success": True,
                "message": f"{len(items)} itens armazenados. Último update: {time_str}",
                "details": {
                    "count": len(items),
                    "received_at": time_str
                }
            }
        else:
            return {
                "success": False,
                "message": "Nenhum dado recebido ainda. Aguardando webhook.",
                "details": {
                    "webhook_url": f"/webhooks/data-source/{source_id}"
                }
            }

    async def lookup_by_code(self, code: str) -> Optional[PropertyResult]:
        """Busca item por código nos dados armazenados."""
        code = str(code).strip()
        logger.info(f"[Webhook] Buscando código: {code}")

        if not code:
            return None

        items = self.get_stored_items()
        code_field = self.config.config.get("code_field", "codigo")

        for item in items:
            if str(item.get(code_field, "")) == code:
                logger.info(f"[Webhook] Encontrado: {code}")
                return self._to_property_result(item)

        logger.warning(f"[Webhook] Código {code} não encontrado")
        return None

    async def search(self, criteria: SearchCriteria) -> List[PropertyResult]:
        """Busca itens por critérios."""
        logger.info(f"[Webhook] Busca por critérios: {criteria}")

        items = self.get_stored_items()
        results = []

        for item in items:
            if self._matches_criteria(item, criteria):
                results.append(self._to_property_result(item))
                if len(results) >= criteria.limit:
                    break

        logger.info(f"[Webhook] {len(results)} resultados encontrados")
        return results

    async def sync_all(self) -> Dict[str, Any]:
        """Retorna status dos dados armazenados."""
        items = self.get_stored_items()

        return {
            "success": True,
            "count": len(items),
            "errors": [],
            "message": f"{len(items)} itens em cache. Sync via webhook."
        }

    def _matches_criteria(self, item: Dict, criteria: SearchCriteria) -> bool:
        """Filtra item por critérios."""
        mapped = self._apply_field_mapping(item)

        # Preço máximo
        if criteria.price_max:
            price = self._safe_float(mapped.get("price", item.get("preco", 0)))
            if price and price > criteria.price_max:
                return False

        # Preço mínimo
        if criteria.price_min:
            price = self._safe_float(mapped.get("price", item.get("preco", 0)))
            if price and price < criteria.price_min:
                return False

        # Quartos mínimos
        if criteria.bedrooms_min:
            bedrooms = self._safe_int(mapped.get("bedrooms", item.get("quartos", 0)))
            if bedrooms and bedrooms < criteria.bedrooms_min:
                return False

        # Tipo
        if criteria.type:
            item_type = str(mapped.get("type", item.get("tipo", ""))).lower()
            if criteria.type.lower() not in item_type:
                return False

        # Região
        if criteria.region:
            item_region = str(mapped.get("region", item.get("regiao", ""))).lower()
            if criteria.region.lower() not in item_region:
                return False

        return True

    def _to_property_result(self, item: Dict) -> PropertyResult:
        """Converte item para PropertyResult."""
        mapped = self._apply_field_mapping(item)

        code_field = self.config.config.get("code_field", "codigo")

        return PropertyResult(
            code=str(mapped.get("code", item.get(code_field, ""))),
            title=mapped.get("title", item.get("titulo", "")),
            type=mapped.get("type", item.get("tipo", "")),
            region=mapped.get("region", item.get("regiao", "")),
            price=self._safe_float(mapped.get("price", item.get("preco"))),
            price_formatted=self._format_price(mapped.get("price", item.get("preco"))),
            bedrooms=self._safe_int(mapped.get("bedrooms", item.get("quartos"))),
            bathrooms=self._safe_int(mapped.get("bathrooms", item.get("banheiros"))),
            parking=self._safe_int(mapped.get("parking", item.get("vagas"))),
            area=self._safe_float(mapped.get("area", item.get("metragem"))),
            description=mapped.get("description", item.get("descricao", "")),
            link=mapped.get("link", item.get("link")),
            agent_name=item.get("corretor_nome"),
            agent_whatsapp=item.get("corretor_whatsapp"),
            attributes=mapped.get("attributes", {}),
            source_id=self.config.source_id,
            source_type=self.config.type,
            raw_data=item
        )
