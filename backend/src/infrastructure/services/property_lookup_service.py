"""
SERVIÇO DE BUSCA DE IMÓVEIS - PORTAL DE INVESTIMENTO
COM LOGS EXTENSIVOS PARA DEBUG
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
        logger.info(f"🔎 [PORTAL] Iniciando busca por código: {codigo}")
        
        if not codigo:
            logger.warning(f"❌ [PORTAL] Código vazio!")
            return None
        
        # Cache
        cached = _get_cache(f"cod_{codigo}")
        if cached:
            logger.info(f"✅ [PORTAL] Encontrado no cache: {codigo}")
            return cached
        
        # Busca em todas as regiões
        for regiao in PORTAL_REGIONS:
            logger.info(f"🔍 [PORTAL] Buscando em {regiao}...")
            imoveis = self._carregar_regiao(regiao)
            
            if not imoveis:
                logger.warning(f"⚠️ [PORTAL] Nenhum imóvel carregado de {regiao}")
                continue
            
            logger.info(f"📦 [PORTAL] {len(imoveis)} imóveis em {regiao}")
            
            for imovel in imoveis:
                cod_imovel = str(imovel.get("codigo", ""))
                if cod_imovel == codigo:
                    resultado = self._formatar(imovel, regiao)
                    _set_cache(f"cod_{codigo}", resultado)
                    logger.info(f"✅✅✅ [PORTAL] ENCONTRADO! Imóvel {codigo} em {regiao}: {resultado}")
                    return resultado
        
        logger.warning(f"❌ [PORTAL] Imóvel {codigo} NÃO encontrado em nenhuma região")
        return None
    
    def _carregar_regiao(self, regiao: str) -> Optional[List[Dict]]:
        """Carrega JSON de uma região."""
        cached = _get_cache(f"reg_{regiao}")
        if cached:
            logger.info(f"📦 [PORTAL] Região {regiao} carregada do cache")
            return cached
        
        url = f"{PORTAL_BASE_URL}/imoveis/{regiao}/{regiao}.json"
        logger.info(f"🌐 [PORTAL] Fazendo GET em: {url}")
        
        try:
            response = self.client.get(url)
            logger.info(f"📡 [PORTAL] Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                _set_cache(f"reg_{regiao}", data)
                logger.info(f"✅ [PORTAL] {len(data)} imóveis carregados de {regiao}")
                return data
            else:
                logger.error(f"❌ [PORTAL] Erro HTTP {response.status_code} em {url}")
        except httpx.TimeoutException as e:
            logger.error(f"⏰ [PORTAL] Timeout ao carregar {regiao}: {e}")
        except httpx.RequestError as e:
            logger.error(f"🔴 [PORTAL] Erro de conexão em {regiao}: {e}")
        except Exception as e:
            logger.error(f"💥 [PORTAL] Erro inesperado em {regiao}: {type(e).__name__}: {e}")
        
        return None
    
    def _formatar(self, imovel: Dict, regiao: str) -> Dict:
        """Formata dados do imóvel."""
        preco = imovel.get("preco", 0)
        preco_fmt = f"R$ {preco:,.0f}".replace(",", ".") if preco else "Consulte"
        
        return {
            "codigo": str(imovel.get("codigo", "")),
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
    """Extrai código de imóvel da mensagem - VERSÃO ROBUSTA."""
    logger.info(f"🔎 [EXTRATOR] Analisando mensagem: '{mensagem[:100]}...'")
    
    if not mensagem:
        logger.warning(f"❌ [EXTRATOR] Mensagem vazia!")
        return None
    
    mensagem_lower = mensagem.lower()
    
    # Padrão 1: Entre colchetes ou parênteses [722585] ou (722585)
    match = re.search(r'[\[\(](\d{5,7})[\]\)]', mensagem)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão 1 (colchetes): {codigo}")
        return codigo
    
    # Padrão 2: código/imóvel seguido de número
    match = re.search(r'(?:c[oó]digo|im[oó]vel)[:\s]*(\d{5,7})', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão 2 (código:): {codigo}")
        return codigo
    
    # Padrão 3: referência contextual "esse 758582", "o 758582"
    match = re.search(r'(?:n?ess[ea]|este|o)\s+(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão 3 (esse X): {codigo}")
        return codigo
    
    # Padrão 4: "e esse 758582", "e o 758582", "e 758582"
    match = re.search(r'\be\s+(?:(?:o|ess[ea])\s+)?(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão 4 (e X): {codigo}")
        return codigo
    
    # Padrão 5: número isolado de 5-7 dígitos (última tentativa)
    match = re.search(r'\b(\d{5,7})\b', mensagem)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão 5 (número isolado): {codigo}")
        return codigo
    
    logger.warning(f"❌ [EXTRATOR] Nenhum código encontrado na mensagem")
    return None


def buscar_imovel_na_mensagem(mensagem: str) -> Optional[Dict]:
    """Função principal - extrai código e busca imóvel."""
    logger.info(f"🏠🏠🏠 [BUSCA] INICIANDO buscar_imovel_na_mensagem")
    logger.info(f"🏠 [BUSCA] Mensagem recebida: '{mensagem[:200] if mensagem else 'VAZIA'}'")
    
    codigo = extrair_codigo_imovel(mensagem)
    
    if not codigo:
        logger.info(f"❌ [BUSCA] Nenhum código extraído da mensagem")
        return None
    
    logger.info(f"🔍 [BUSCA] Código extraído: {codigo} - Iniciando busca no portal...")
    
    service = PropertyLookupService()
    resultado = service.buscar_por_codigo(codigo)
    
    if resultado:
        logger.info(f"✅✅✅ [BUSCA] SUCESSO! Imóvel encontrado: {resultado}")
    else:
        logger.warning(f"❌ [BUSCA] Imóvel {codigo} não encontrado no portal")
    
    return resultado


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