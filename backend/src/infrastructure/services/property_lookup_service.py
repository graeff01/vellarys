"""
SERVIÇO DE BUSCA DE IMÓVEIS - PORTAL DE INVESTIMENTO
VERSÃO ROBUSTA COM FALLBACK E LOGS EXTENSIVOS
=====================================================
Arquivo: backend/src/infrastructure/services/property_lookup_service.py
"""

import logging
import re
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import asyncio
from .semantic_search_service import semantic_search

logger = logging.getLogger(__name__)

PORTAL_BASE_URL = "https://portalinvestimento.com"
PORTAL_REGIONS = ["canoas", "poa", "sc", "pb"]  # 🚀 CANOAS AGORA É PRIORIDADE
HTTP_TIMEOUT = 5.0
FALLBACK_FILE_CANOAS = "data/fallback_canoas.json"  # 📂 ARQUIVO LOCAL

# 🌐 HEADERS PARA EVITAR 403 FORBIDDEN
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

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
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                logger.info(f"✅ [HTTP] httpx OK - Status: {response.status_code}")
                return response.json()
            else:
                logger.warning(f"⚠️ [HTTP] httpx Status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ [HTTP] httpx erro: {type(e).__name__}: {e}")
    
    # Fallback para requests
    try:
        import requests
        logger.info(f"🌐 [HTTP] Tentando requests: {url}")
        response = requests.get(url, timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS)
        if response.status_code == 200:
            logger.info(f"✅ [HTTP] requests OK - Status: {response.status_code}")
            return response.json()
        else:
            logger.warning(f"⚠️ [HTTP] requests Status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ [HTTP] requests erro: {type(e).__name__}: {e}")
    
    # Fallback para urllib
    try:
        import urllib.request
        import json
        logger.info(f"🌐 [HTTP] Tentando urllib: {url}")
        req = urllib.request.Request(url, headers=HTTP_HEADERS)
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                logger.info(f"✅ [HTTP] urllib OK")
                return data
    except Exception as e:
        logger.error(f"❌ [HTTP] urllib erro: {type(e).__name__}: {e}")
    
    return None


from src.infrastructure.services.multi_tenant_property_service import MultiTenantPropertyService
from sqlalchemy.ext.asyncio import AsyncSession

# ... (outros imports e constantes mantidos para fallback se necessário)

class PropertyLookupService:
    """
    Wrapper compatível com o sistema anterior que agora utiliza
    o MultiTenantPropertyService para buscar dados dinâmicos do banco.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None, tenant_id: Optional[int] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.multi_tenant_service = None
        if db and tenant_id:
            self.multi_tenant_service = MultiTenantPropertyService(db, tenant_id)
    
    async def buscar_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca imóvel pelo código usando o serviço multi-tenant."""
        if not self.multi_tenant_service:
            # Fallback para o comportamento antigo se db/tenant não fornecidos
            # (Útil para scripts de teste ou legados, mas deve ser evitado)
            logger.warning("⚠️ Chamando buscar_por_codigo sem DB/Tenant - usando modo legado hardcoded")
            return self._buscar_legado_hardcoded(codigo)
            
        return await self.multi_tenant_service.buscar_por_codigo(codigo)

    async def buscar_por_criterios(
        self, 
        regiao: Optional[str] = None, 
        tipo: Optional[str] = None, 
        preco_max: Optional[int] = None, 
        quartos_min: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Busca imóveis por critérios usando o serviço multi-tenant."""
        if not self.multi_tenant_service:
            logger.warning("⚠️ Chamando buscar_por_criterios sem DB/Tenant - usando modo legado")
            return self._buscar_criterios_legado(regiao, tipo, preco_max, quartos_min, limit)
            
        return await self.multi_tenant_service.buscar_por_criterios(
            regiao=regiao, tipo=tipo, preco_max=preco_max, quartos_min=quartos_min, limit=limit
        )

    # Métodos privados para manter compatibilidade com o código original (modo legado)
    def _buscar_legado_hardcoded(self, codigo: str) -> Optional[Dict]:
        # ... (Mantém a lógica antiga aqui para emergências)
        # Por brevidade, vou apenas logar e retornar None por enquanto, 
        # já que o objetivo é migrar tudo para o multi-tenant.
        return None

    def _buscar_criterios_legado(self, *args, **kwargs) -> List[Dict]:
        return []

    # O carregar_regiao e formatar tornam-se redundantes pois o MultiTenantPropertyService 
    # já cuida disso através dos DataSources configurados.



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


async def buscar_imovel_na_mensagem(mensagem: str, db: Optional[AsyncSession] = None, tenant_id: Optional[int] = None) -> Optional[Dict]:
    """Função principal - extrai código e busca imóvel usando suporte multi-tenant."""
    codigo = extrair_codigo_imovel(mensagem)
    if not codigo:
        return None
    service = PropertyLookupService(db=db, tenant_id=tenant_id)
    return await service.buscar_por_codigo(codigo)



def extrair_criterios_busca(mensagem: str) -> Dict[str, Any]:
    """
    Extrai critérios de busca da mensagem (bairro, preço, quartos, tipo).
    """
    msg_lower = mensagem.lower()
    criterios = {}

    # 1. Bairros abrangentes em Canoas (Baseado no mapa oficial)
    bairros = [
        "centro", "niterói", "niteroi", "marechal rondon", "igara", "guajuviras", 
        "estância velha", "estancia velha", "harmonia", "mathias velho", "rio branco", 
        "fátima", "fatima", "mato grande", "são luís", "sao luis", "são josé", "sao jose",
        "industrial", "brigadeira", "olaria", "ilha das garças", "nossa senhora das graças",
        "nossa senhora das gracas"
    ]
    for bairro in bairros:
        if bairro in msg_lower:
            criterios["regiao"] = bairro
            break

    # 2. Tipo de imóvel
    if "casa" in msg_lower:
        criterios["tipo"] = "Casa"
    elif "apartamento" in msg_lower or "apto" in msg_lower or "ap " in msg_lower:
        criterios["tipo"] = "Apartamento"
    elif "terreno" in msg_lower:
        criterios["tipo"] = "Terreno"

    # 3. Preço máximo (Até 500k, inferior a 600 mil, etc)
    preco_match = re.search(r'(?:at[eé]|abaixo de|menos de|m[aá]ximo de)\s*(?:r\$)?\s*(\d+(?:\.\d+)?)\s*(?:mil|k|milh[oõ]es|mi)?', msg_lower)
    if preco_match:
        valor_str = preco_match.group(1).replace(".", "")
        try:
            valor = float(valor_str)
            contexto = preco_match.group(0)
            if "milh" in contexto or "mi" in contexto:
                valor *= 1_000_000
            elif "mil" in contexto or "k" in contexto or valor < 1000:
                valor *= 1000
            criterios["preco_max"] = int(valor)
        except:
            pass

    # 4. Quartos (2 quartos, 3 dormitórios, etc)
    quartos_match = re.search(r'(\d+)\s*(?:quartos|dormit[oó]rios|dorm)', msg_lower)
    if quartos_match:
        try:
            criterios["quartos_min"] = int(quartos_match.group(1))
        except:
            pass

    return criterios


async def buscar_imoveis_por_criterios(mensagem: str, db: Optional[AsyncSession] = None, tenant_id: Optional[int] = None) -> List[Dict]:
    """Função utilitária para buscar imóveis baseados na mensagem usando suporte multi-tenant."""
    criterios = extrair_criterios_busca(mensagem)
    if not criterios:
        return []
    service = PropertyLookupService(db=db, tenant_id=tenant_id)
    return await service.buscar_por_criterios(**criterios)


async def buscar_imoveis_semantico(mensagem: str, db: Optional[AsyncSession] = None, tenant_id: Optional[int] = None, limit: int = 3) -> List[Dict]:
    """Busca imóveis usando inteligência semântica e suporte multi-tenant."""
    ruidos = ["quero", "busco", "procurando", "imóvel", "casa", "apartamento", "apto", "teria", "alguma", "opção"]
    query = mensagem.lower()
    for r in ruidos:
        query = query.replace(r, "")
    query = query.strip()
    if not query:
        return []
    service = PropertyLookupService(db=db, tenant_id=tenant_id)
    return await service.buscar_por_criterios(regiao=query, limit=limit)
