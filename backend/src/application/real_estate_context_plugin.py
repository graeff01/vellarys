import re
from infrastructure.services.property_lookup_service import PropertyLookupService


class RealEstateContextPlugin:

    def can_handle(self, tenant, message: str) -> bool:
        if getattr(tenant, "niche", None) != "real_estate":
            return False

        return bool(self._extrair_codigo(message))

    def build_context(self, tenant, message: str) -> str | None:
        codigo = self._extrair_codigo(message)
        if not codigo:
            return None

        imovel = PropertyLookupService().buscar_por_codigo(codigo)
        if not imovel:
            return None

        return f"""
IMÓVEL EM CONTEXTO (dados oficiais):
Código: {imovel['codigo']}
Tipo: {imovel['tipo']}
Localização: {imovel['regiao']}
Título: {imovel['titulo']}
Quartos: {imovel['quartos']}
Banheiros: {imovel['banheiros']}
Vagas: {imovel['vagas']}
Área: {imovel['metragem']} m²
Preço: R$ {imovel['preco']}
Descrição: {imovel['descricao']}
Link: {imovel['link']}

REGRAS:
- Use apenas as informações acima
- Não invente dados
- Se faltar algo, pergunte ao lead
""".strip()

    def _extrair_codigo(self, text: str) -> str | None:
        match = re.search(r"\b\d{5,7}\b", text)
        return match.group(0) if match else None
