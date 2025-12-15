"""
SERVIÇO DE BUSCA DE IMÓVEIS - PORTAL DE INVESTIMENTO
VERSÃO ROBUSTA COM FALLBACK E LOGS EXTENSIVOS
=====================================================
Arquivo: backend/src/infrastructure/services/property_lookup_service.py
"""

import logging
import re
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


def _fazer_request_http(url: str) -> Optional[List[Dict]]:
    """Faz request HTTP com múltiplas bibliotecas como fallback."""
    
    # Tenta com httpx primeiro
    try:
        import httpx
        logger.info(f"🌐 [HTTP] Tentando httpx: {url}")
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            response = client.get(url)
            if response.status_code == 200:
                logger.info(f"✅ [HTTP] httpx OK - Status: {response.status_code}")
                return response.json()
            else:
                logger.warning(f"⚠️ [HTTP] httpx Status: {response.status_code}")
    except ImportError:
        logger.warning(f"⚠️ [HTTP] httpx não disponível")
    except Exception as e:
        logger.error(f"❌ [HTTP] httpx erro: {type(e).__name__}: {e}")
    
    # Fallback para requests
    try:
        import requests
        logger.info(f"🌐 [HTTP] Tentando requests: {url}")
        response = requests.get(url, timeout=HTTP_TIMEOUT)
        if response.status_code == 200:
            logger.info(f"✅ [HTTP] requests OK - Status: {response.status_code}")
            return response.json()
        else:
            logger.warning(f"⚠️ [HTTP] requests Status: {response.status_code}")
    except ImportError:
        logger.warning(f"⚠️ [HTTP] requests não disponível")
    except Exception as e:
        logger.error(f"❌ [HTTP] requests erro: {type(e).__name__}: {e}")
    
    # Fallback para urllib
    try:
        import urllib.request
        import json
        logger.info(f"🌐 [HTTP] Tentando urllib: {url}")
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                logger.info(f"✅ [HTTP] urllib OK")
                return data
    except Exception as e:
        logger.error(f"❌ [HTTP] urllib erro: {type(e).__name__}: {e}")
    
    return None


class PropertyLookupService:
    
    def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca imóvel pelo código (ex: 722585)."""
        codigo = str(codigo).strip()
        logger.info(f"🔎 [PORTAL] ========== INICIANDO BUSCA ==========")
        logger.info(f"🔎 [PORTAL] Código: {codigo}")
        
        if not codigo:
            logger.warning(f"❌ [PORTAL] Código vazio!")
            return None
        
        # Cache
        cached = _get_cache(f"cod_{codigo}")
        if cached:
            logger.info(f"✅ [PORTAL] Encontrado no CACHE: {codigo}")
            return cached
        
        # Busca em todas as regiões
        for regiao in PORTAL_REGIONS:
            logger.info(f"🔍 [PORTAL] Buscando em região: {regiao}")
            imoveis = self._carregar_regiao(regiao)
            
            if not imoveis:
                logger.warning(f"⚠️ [PORTAL] Região {regiao}: sem dados")
                continue
            
            logger.info(f"📦 [PORTAL] Região {regiao}: {len(imoveis)} imóveis carregados")
            
            for imovel in imoveis:
                cod_imovel = str(imovel.get("codigo", ""))
                if cod_imovel == codigo:
                    resultado = self._formatar(imovel, regiao)
                    _set_cache(f"cod_{codigo}", resultado)
                    logger.info(f"✅✅✅ [PORTAL] ENCONTRADO! Código {codigo} em {regiao}")
                    logger.info(f"✅✅✅ [PORTAL] Dados: {resultado}")
                    return resultado
            
            logger.info(f"❌ [PORTAL] Código {codigo} não encontrado em {regiao}")
        
        logger.warning(f"❌❌❌ [PORTAL] Código {codigo} NÃO ENCONTRADO em nenhuma região!")
        return None
    
    def _carregar_regiao(self, regiao: str) -> Optional[List[Dict]]:
        """Carrega JSON de uma região."""
        cached = _get_cache(f"reg_{regiao}")
        if cached:
            logger.info(f"📦 [PORTAL] Região {regiao} carregada do CACHE")
            return cached
        
        url = f"{PORTAL_BASE_URL}/imoveis/{regiao}/{regiao}.json"
        logger.info(f"🌐 [PORTAL] URL: {url}")
        
        data = _fazer_request_http(url)
        
        if data:
            _set_cache(f"reg_{regiao}", data)
            logger.info(f"✅ [PORTAL] {len(data)} imóveis carregados de {regiao}")
            return data
        
        logger.error(f"❌ [PORTAL] Falha ao carregar {regiao}")
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
    """
    Extrai código de imóvel da mensagem.
    
    Detecta padrões como:
    - [722585] ou (722585)
    - Código: 722585 / código 722585
    - imóvel 722585
    - esse 722585 / e esse 722585
    - e o 722585 / o 722585
    - sobre o 722585
    - quero ver 722585
    - 722585 (número isolado)
    """
    logger.info(f"🔎 [EXTRATOR] Analisando: '{mensagem[:80] if mensagem else 'VAZIA'}'")
    
    if not mensagem:
        return None
    
    mensagem_lower = mensagem.lower()
    
    # Padrão 1: Entre colchetes ou parênteses [722585] ou (722585)
    match = re.search(r'[\[\(](\d{5,7})[\]\)]', mensagem)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão COLCHETES: {codigo}")
        return codigo
    
    # Padrão 2: código/imóvel seguido de número
    match = re.search(r'(?:c[oó]digo|im[oó]vel)[:\s]*(\d{5,7})', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão CÓDIGO/IMÓVEL: {codigo}")
        return codigo
    
    # Padrão 3: "e" + "esse/o" + número (e esse 442025, e o 442025)
    # IMPORTANTE: Este padrão deve vir ANTES do padrão 4 para capturar "e esse X"
    match = re.search(r'\be\s+(?:ess[ea]|o|este|aquele)\s+(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão E ESSE/O: {codigo}")
        return codigo
    
    # Padrão 4: "esse/este/o/aquele" + número (esse 722585, o 722585)
    match = re.search(r'(?:n?ess[ea]|este|aquele|o)\s+(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão ESSE/O: {codigo}")
        return codigo
    
    # Padrão 5: "sobre" + opcional "o/esse" + número
    match = re.search(r'sobre\s+(?:o|ess[ea]|este)?\s*(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão SOBRE: {codigo}")
        return codigo
    
    # Padrão 6: "e" + número direto (e 722585)
    match = re.search(r'\be\s+(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão E + NÚMERO: {codigo}")
        return codigo
    
    # Padrão 7: verbos de interesse + número (quero 722585, ver 722585)
    match = re.search(r'(?:quero|gostei|interesse|ver|saber|conhecer)\s+(?:do|o|sobre|esse|este)?\s*(\d{5,7})\b', mensagem_lower)
    if match:
        codigo = match.group(1)
        logger.info(f"✅ [EXTRATOR] Padrão INTERESSE: {codigo}")
        return codigo
    
    # Padrão 8: Número isolado de 5-7 dígitos (última tentativa)
    matches = re.findall(r'\b(\d{5,7})\b', mensagem)
    if len(matches) >= 1:
        # Pega o primeiro número encontrado
        codigo = matches[0]
        logger.info(f"✅ [EXTRATOR] Padrão NÚMERO ISOLADO: {codigo}")
        return codigo
    
    logger.info(f"❌ [EXTRATOR] Nenhum código encontrado")
    return None


def buscar_imovel_na_mensagem(mensagem: str) -> Optional[Dict]:
    """Função principal - extrai código e busca imóvel."""
    logger.info(f"")
    logger.info(f"🏠🏠🏠 ========================================== 🏠🏠🏠")
    logger.info(f"🏠 [BUSCA] INICIANDO buscar_imovel_na_mensagem")
    logger.info(f"🏠 [BUSCA] Mensagem: '{mensagem[:100] if mensagem else 'VAZIA'}'")
    logger.info(f"🏠🏠🏠 ========================================== 🏠🏠🏠")
    
    codigo = extrair_codigo_imovel(mensagem)
    
    if not codigo:
        logger.info(f"❌ [BUSCA] Nenhum código na mensagem")
        return None
    
    logger.info(f"🔍 [BUSCA] Código extraído: {codigo}")
    logger.info(f"🔍 [BUSCA] Iniciando busca no portal...")
    
    service = PropertyLookupService()
    resultado = service.buscar_por_codigo(codigo)
    
    if resultado:
        logger.info(f"✅✅✅ [BUSCA] SUCESSO!")
        logger.info(f"✅ [BUSCA] Imóvel: {resultado.get('codigo')} - {resultado.get('titulo')}")
        logger.info(f"✅ [BUSCA] Quartos: {resultado.get('quartos')} | Preço: {resultado.get('preco')}")
    else:
        logger.warning(f"❌ [BUSCA] Imóvel {codigo} NÃO encontrado")
    
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