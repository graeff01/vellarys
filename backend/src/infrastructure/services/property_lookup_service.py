"""
SERVIÇO DE BUSCA DE IMÓVEIS - PORTAL DE INVESTIMENTO
"""

import logging
import re
import httpx
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PORTAL_BASE_URL = "https://portalinvestimento.com"
PORTAL_REGIONS = ["poa", "sc", "canoas", "pb"]
HTTP_TIMEOUT = 5.0

# Cache simples em memória
_cache: Dict[str, tuple] = {}
_cache_ttl = 300  # 5 minutos


def _get_cache(key: str):
    if key in _cache:
        value, expires = _cache[key]
        if datetime.now() < expires:
            return value
    return None


def _set_cache(key: str, value):
    _cache[key] = (value, datetime.now() + timedelta(seconds=_cache_ttl))


class PropertyLookupService:
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=HTTP_TIMEOUT)
        return self._client
    
    def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca imóvel pelo código (ex: 722585)."""
        codigo = str(codigo).strip()
        if not codigo:
            return None
        
        # Cache
        cached = _get_cache(f"cod_{codigo}")
        if cached:
            return cached
        
        # Busca em todas as regiões
        for regiao in PORTAL_REGIONS:
            imoveis = self._carregar_regiao(regiao)
            if not imoveis:
                continue
            
            for imovel in imoveis:
                if str(imovel.get("codigo", "")) == codigo:
                    resultado = self._formatar(imovel, regiao)
                    _set_cache(f"cod_{codigo}", resultado)
                    logger.info(f"🏠 Imóvel {codigo} encontrado em {regiao}")
                    return resultado
        
        logger.info(f"❌ Imóvel {codigo} não encontrado")
        return None
    
    def _carregar_regiao(self, regiao: str) -> Optional[List[Dict]]:
        """Carrega JSON de uma região."""
        cached = _get_cache(f"reg_{regiao}")
        if cached:
            return cached
        
        url = f"{PORTAL_BASE_URL}/imoveis/{regiao}/{regiao}.json"
        
        try:
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                _set_cache(f"reg_{regiao}", data)
                logger.info(f"✅ {len(data)} imóveis carregados de {regiao}")
                return data
        except Exception as e:
            logger.warning(f"Erro ao carregar {regiao}: {e}")
        
        return None
    
    def _formatar(self, imovel: Dict, regiao: str) -> Dict:
        """Formata dados do imóvel."""
        preco = imovel.get("preco", 0)
        preco_fmt = f"R$ {preco:,.0f}".replace(",", ".") if preco else "Consulte"
        
        return {
            "codigo": imovel.get("codigo", ""),
            "titulo": imovel.get("titulo", "Imóvel"),
            "tipo": imovel.get("tipo", "Imóvel"),
            "regiao": imovel.get("regiao", regiao.upper()),
            "quartos": imovel.get("quartos", "Consulte"),
            "banheiros": imovel.get("banheiros", "Consulte"),
            "vagas": imovel.get("vagas", "Consulte"),
            "metragem": imovel.get("metragem", "Consulte"),
            "preco": preco_fmt,
            "descricao": imovel.get("descricao", ""),
            "link": f"{PORTAL_BASE_URL}/imovel.html?id={imovel.get('id', '')}",
        }


def extrair_codigo_imovel(mensagem: str) -> Optional[str]:
    """Extrai código de imóvel da mensagem."""
    if not mensagem:
        return None
    
    # Padrão: Código: [722585] ou código 722585
    match = re.search(r'[\[\(](\d{5,7})[\]\)]', mensagem)
    if match:
        return match.group(1)
    
    match = re.search(r'(?:c[oó]digo|im[oó]vel)[:\s]*(\d{5,7})', mensagem.lower())
    if match:
        return match.group(1)
    
    return None


def buscar_imovel_na_mensagem(mensagem: str) -> Optional[Dict]:
    """Função principal - extrai código e busca imóvel."""
    codigo = extrair_codigo_imovel(mensagem)
    if not codigo:
        return None
    
    logger.info(f"🔍 Código detectado: {codigo}")
    service = PropertyLookupService()
    return service.buscar_por_codigo(codigo)


def build_property_context(imovel: Dict) -> str:
    """Constrói contexto para a IA."""
    if not imovel:
        return ""
    
    return f"""
============================================================
🏠 IMÓVEL DO PORTAL DE INVESTIMENTO
============================================================
Código: {imovel['codigo']}
Título: {imovel['titulo']}
Tipo: {imovel['tipo']}
Localização: {imovel['regiao']}
Quartos: {imovel['quartos']}
Banheiros: {imovel['banheiros']}
Vagas: {imovel['vagas']}
Área: {imovel['metragem']} m²
Preço: {imovel['preco']}

Descrição: {imovel['descricao']}

Link: {imovel['link']}
============================================================
INSTRUÇÕES: Use APENAS estas informações. NÃO invente dados.
============================================================
"""