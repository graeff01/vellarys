"""
ENDPOINT DE DIAGNÓSTICO - PORTAL DE INVESTIMENTO
================================================
Adicione este arquivo em: backend/src/api/routes/debug_portal.py

E registre no main.py:
    from src.api.routes.debug_portal import router as debug_portal_router
    app.include_router(debug_portal_router, prefix="/api/v1/debug", tags=["debug"])
"""

from fastapi import APIRouter
import logging
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

PORTAL_BASE_URL = "https://portalinvestimento.com"
PORTAL_REGIONS = ["poa", "sc", "canoas", "pb"]


@router.get("/portal-test")
async def test_portal():
    """
    Testa conexão com o Portal de Investimento.
    Acesse: /api/v1/debug/portal-test
    """
    results = {
        "status": "testing",
        "regions": {},
        "codigo_722585": None,
        "errors": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for regiao in PORTAL_REGIONS:
                url = f"{PORTAL_BASE_URL}/imoveis/{regiao}/{regiao}.json"
                
                try:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        results["regions"][regiao] = {
                            "status": "OK",
                            "count": len(data),
                            "first_codes": [str(i.get("codigo", "?")) for i in data[:5]]
                        }
                        
                        # Procura o 722585
                        for imovel in data:
                            if str(imovel.get("codigo", "")) == "722585":
                                results["codigo_722585"] = {
                                    "found_in": regiao,
                                    "titulo": imovel.get("titulo"),
                                    "quartos": imovel.get("quartos"),
                                    "metragem": imovel.get("metragem"),
                                    "preco": imovel.get("preco"),
                                }
                                break
                    else:
                        results["regions"][regiao] = {
                            "status": "ERROR",
                            "http_code": response.status_code
                        }
                        
                except httpx.TimeoutException:
                    results["regions"][regiao] = {"status": "TIMEOUT"}
                    results["errors"].append(f"Timeout em {regiao}")
                except Exception as e:
                    results["regions"][regiao] = {"status": "ERROR", "message": str(e)}
                    results["errors"].append(f"Erro em {regiao}: {str(e)}")
        
        results["status"] = "completed"
        
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(str(e))
    
    return results


@router.get("/portal-search/{codigo}")
async def search_portal(codigo: str):
    """
    Busca um código específico no portal.
    Acesse: /api/v1/debug/portal-search/722585
    """
    results = {
        "codigo": codigo,
        "found": False,
        "data": None,
        "searched_regions": [],
        "errors": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for regiao in PORTAL_REGIONS:
                url = f"{PORTAL_BASE_URL}/imoveis/{regiao}/{regiao}.json"
                results["searched_regions"].append(regiao)
                
                try:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for imovel in data:
                            if str(imovel.get("codigo", "")) == codigo:
                                results["found"] = True
                                results["found_in"] = regiao
                                results["data"] = {
                                    "codigo": imovel.get("codigo"),
                                    "titulo": imovel.get("titulo"),
                                    "tipo": imovel.get("tipo"),
                                    "regiao": imovel.get("regiao"),
                                    "quartos": imovel.get("quartos"),
                                    "banheiros": imovel.get("banheiros"),
                                    "vagas": imovel.get("vagas"),
                                    "metragem": imovel.get("metragem"),
                                    "preco": imovel.get("preco"),
                                    "descricao": imovel.get("descricao", "")[:200],
                                }
                                return results
                                
                except Exception as e:
                    results["errors"].append(f"{regiao}: {str(e)}")
                    
    except Exception as e:
        results["errors"].append(str(e))
    
    return results


@router.get("/test-extraction")
async def test_extraction():
    """
    Testa a extração de código de mensagens.
    """
    import re
    
    test_messages = [
        "Olá! vim do portal de investimento e tenho interesse no Código: [722585]",
        "Código: 722585",
        "imóvel 722585",
        "quero saber sobre o 722585",
        "esse 722585 ainda está disponível?",
        "quantos quartos tem?",
    ]
    
    results = []
    
    for msg in test_messages:
        codigo = None
        pattern_used = None
        
        # Padrão 1: Entre colchetes
        match = re.search(r'[\[\(](\d{5,7})[\]\)]', msg)
        if match:
            codigo = match.group(1)
            pattern_used = "colchetes"
        
        # Padrão 2: código/imóvel seguido de número
        if not codigo:
            match = re.search(r'(?:c[oó]digo|im[oó]vel)[:\s]*(\d{5,7})', msg.lower())
            if match:
                codigo = match.group(1)
                pattern_used = "codigo:"
        
        # Padrão 3: referência contextual
        if not codigo:
            match = re.search(r'(?:n?ess[ea]|este|o)\s+(\d{5,7})\b', msg.lower())
            if match:
                codigo = match.group(1)
                pattern_used = "esse X"
        
        # Padrão 4: número isolado
        if not codigo:
            match = re.search(r'\b(\d{5,7})\b', msg)
            if match:
                codigo = match.group(1)
                pattern_used = "número"
        
        results.append({
            "message": msg[:50],
            "codigo_found": codigo,
            "pattern": pattern_used
        })
    
    return {"extraction_tests": results}


@router.get("/niche-check/{tenant_slug}")
async def check_niche(tenant_slug: str):
    """
    Verifica o niche de um tenant específico.
    """
    from sqlalchemy import select
    from src.infrastructure.database import get_db
    from src.domain.entities import Tenant
    
    NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]
    
    # Isso precisa de uma sessão de DB
    return {
        "tenant_slug": tenant_slug,
        "nichos_validos": NICHOS_IMOBILIARIOS,
        "note": "Use o SQL no Railway para verificar: SELECT settings->>'niche' FROM tenants WHERE slug = '{}'".format(tenant_slug)
    }