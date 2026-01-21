"""
AI TOOLS - Definição e execução de funções para Function Calling
================================================================

Define as ferramentas (tools) que a IA pode chamar durante uma conversa.
Cada tool tem:
1. Definição (schema OpenAI)
2. Executor (função que executa a ação)

Tools disponíveis:
- buscar_imovel_por_codigo: Busca imóvel específico pelo código
- buscar_imoveis_por_criterios: Busca imóveis por filtros
- calcular_financiamento: Simula parcelas de financiamento
- consultar_disponibilidade: Verifica se imóvel está disponível
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)


# =============================================================================
# DEFINIÇÕES DAS TOOLS (Schema OpenAI)
# =============================================================================

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_imovel_por_codigo",
            "description": "Busca um imóvel específico pelo código único. Use quando o cliente mencionar um código de imóvel (geralmente 5-7 dígitos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código único do imóvel (ex: '12345', 'APT-001')"
                    }
                },
                "required": ["codigo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_imoveis_por_criterios",
            "description": "Busca imóveis disponíveis com base em critérios como localização, preço e características. Use quando o cliente descrever o que está procurando.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bairro": {
                        "type": "string",
                        "description": "Nome do bairro ou região (ex: 'Centro', 'Niterói', 'Vila Nova')"
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["casa", "apartamento", "terreno", "comercial", "cobertura"],
                        "description": "Tipo de imóvel desejado"
                    },
                    "preco_maximo": {
                        "type": "integer",
                        "description": "Preço máximo em reais (ex: 500000 para R$ 500.000)"
                    },
                    "quartos_minimo": {
                        "type": "integer",
                        "description": "Número mínimo de quartos/dormitórios"
                    },
                    "metragem_minima": {
                        "type": "integer",
                        "description": "Metragem mínima em m²"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_financiamento",
            "description": "Calcula uma simulação de parcelas de financiamento imobiliário. Use quando o cliente perguntar sobre valores de parcela, financiamento ou quanto pagaria por mês.",
            "parameters": {
                "type": "object",
                "properties": {
                    "valor_imovel": {
                        "type": "integer",
                        "description": "Valor total do imóvel em reais (ex: 400000)"
                    },
                    "entrada": {
                        "type": "integer",
                        "description": "Valor da entrada em reais. Se não informado, usa 20% do valor."
                    },
                    "prazo_meses": {
                        "type": "integer",
                        "description": "Prazo em meses (ex: 360 para 30 anos). Default: 360"
                    },
                    "taxa_anual": {
                        "type": "number",
                        "description": "Taxa de juros anual em % (ex: 10.5 para 10.5% a.a.). Default: 10.5"
                    }
                },
                "required": ["valor_imovel"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_disponibilidade",
            "description": "Verifica se um imóvel específico está disponível para visita ou negociação.",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo_imovel": {
                        "type": "string",
                        "description": "Código do imóvel para verificar"
                    }
                },
                "required": ["codigo_imovel"]
            }
        }
    },
]


# =============================================================================
# EXECUTORES DAS TOOLS
# =============================================================================

async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> Dict[str, Any]:
    """
    Executa uma tool e retorna o resultado.

    Args:
        tool_name: Nome da tool a executar
        arguments: Argumentos da chamada (parseados do JSON)
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        lead_id: ID do lead

    Returns:
        Dict com o resultado da execução
    """
    logger.info(f"🔧 Executando tool: {tool_name} com args: {arguments}")

    executors = {
        "buscar_imovel_por_codigo": _exec_buscar_imovel_por_codigo,
        "buscar_imoveis_por_criterios": _exec_buscar_imoveis_por_criterios,
        "calcular_financiamento": _exec_calcular_financiamento,
        "consultar_disponibilidade": _exec_consultar_disponibilidade,
    }

    executor = executors.get(tool_name)
    if not executor:
        logger.error(f"Tool desconhecida: {tool_name}")
        return {"error": f"Tool desconhecida: {tool_name}"}

    try:
        result = await executor(arguments, db, tenant_id, lead_id)
        logger.info(f"✅ Tool {tool_name} executada com sucesso")
        return result
    except Exception as e:
        logger.error(f"❌ Erro executando tool {tool_name}: {e}")
        return {"error": str(e)}


async def _exec_buscar_imovel_por_codigo(
    args: Dict, db: AsyncSession, tenant_id: int, lead_id: int
) -> Dict:
    """Busca imóvel por código único."""
    from src.infrastructure.services.property_lookup_service import PropertyLookupService

    codigo = args.get("codigo", "").strip()
    if not codigo:
        return {"found": False, "error": "Código não informado"}

    try:
        service = PropertyLookupService(db=db, tenant_id=tenant_id)
        imovel = await service.buscar_por_codigo(codigo)

        if not imovel:
            return {
                "found": False,
                "message": f"Imóvel com código '{codigo}' não encontrado no sistema."
            }

        return {
            "found": True,
            "imovel": {
                "codigo": imovel.get("codigo", codigo),
                "titulo": imovel.get("titulo"),
                "tipo": imovel.get("tipo"),
                "regiao": imovel.get("regiao"),
                "quartos": imovel.get("quartos"),
                "banheiros": imovel.get("banheiros"),
                "vagas": imovel.get("vagas"),
                "metragem": imovel.get("metragem"),
                "preco": imovel.get("preco"),
                "descricao": imovel.get("descricao", "")[:300],
            }
        }
    except Exception as e:
        logger.error(f"Erro buscando imóvel {codigo}: {e}")
        return {"found": False, "error": str(e)}


async def _exec_buscar_imoveis_por_criterios(
    args: Dict, db: AsyncSession, tenant_id: int, lead_id: int
) -> Dict:
    """Busca imóveis por critérios de filtro."""
    from src.infrastructure.services.property_lookup_service import PropertyLookupService

    try:
        service = PropertyLookupService(db=db, tenant_id=tenant_id)

        imoveis = await service.buscar_por_criterios(
            regiao=args.get("bairro"),
            tipo=args.get("tipo"),
            preco_max=args.get("preco_maximo"),
            quartos_min=args.get("quartos_minimo"),
            metragem_min=args.get("metragem_minima"),
            limit=5
        )

        if not imoveis:
            # Tenta busca semântica se não encontrou por critérios
            from src.infrastructure.services.property_lookup_service import buscar_imoveis_semantico

            query_parts = []
            if args.get("tipo"):
                query_parts.append(args["tipo"])
            if args.get("bairro"):
                query_parts.append(args["bairro"])
            if args.get("quartos_minimo"):
                query_parts.append(f"{args['quartos_minimo']} quartos")

            if query_parts:
                query = " ".join(query_parts)
                imoveis = await buscar_imoveis_semantico(query, db=db, tenant_id=tenant_id, limit=5)

        if not imoveis:
            return {
                "found": False,
                "count": 0,
                "message": "Nenhum imóvel encontrado com esses critérios. Tente ajustar os filtros."
            }

        # Formata resultado
        imoveis_formatados = []
        for im in imoveis[:5]:
            imoveis_formatados.append({
                "codigo": im.get("codigo"),
                "titulo": im.get("titulo"),
                "tipo": im.get("tipo"),
                "regiao": im.get("regiao"),
                "quartos": im.get("quartos"),
                "preco": im.get("preco"),
            })

        return {
            "found": True,
            "count": len(imoveis_formatados),
            "imoveis": imoveis_formatados,
            "criterios_usados": {k: v for k, v in args.items() if v is not None}
        }

    except Exception as e:
        logger.error(f"Erro buscando imóveis por critérios: {e}")
        return {"found": False, "error": str(e)}


async def _exec_calcular_financiamento(
    args: Dict, db: AsyncSession, tenant_id: int, lead_id: int
) -> Dict:
    """Calcula simulação de financiamento imobiliário."""

    valor_imovel = args.get("valor_imovel", 0)

    if not valor_imovel or valor_imovel <= 0:
        return {"error": "Valor do imóvel não informado ou inválido"}

    # Valores padrão
    entrada = args.get("entrada")
    if entrada is None:
        entrada = int(valor_imovel * 0.2)  # Default 20%

    prazo_meses = args.get("prazo_meses", 360)  # Default 30 anos
    taxa_anual = args.get("taxa_anual", 10.5)  # Default 10.5% a.a.

    # Validações
    if entrada >= valor_imovel:
        return {"error": "Entrada não pode ser maior que o valor do imóvel"}

    if prazo_meses <= 0 or prazo_meses > 420:  # Max 35 anos
        prazo_meses = 360

    if taxa_anual <= 0 or taxa_anual > 30:
        taxa_anual = 10.5

    # Cálculo
    valor_financiado = valor_imovel - entrada
    taxa_mensal = (taxa_anual / 100) / 12

    # Parcela pelo sistema Price (mais comum)
    if taxa_mensal > 0:
        parcela = valor_financiado * (
            (taxa_mensal * (1 + taxa_mensal) ** prazo_meses) /
            ((1 + taxa_mensal) ** prazo_meses - 1)
        )
    else:
        parcela = valor_financiado / prazo_meses

    # Calcula também primeira parcela SAC (para comparação)
    amortizacao_sac = valor_financiado / prazo_meses
    juros_primeira_sac = valor_financiado * taxa_mensal
    primeira_parcela_sac = amortizacao_sac + juros_primeira_sac

    return {
        "valor_imovel": valor_imovel,
        "entrada": entrada,
        "percentual_entrada": round((entrada / valor_imovel) * 100, 1),
        "valor_financiado": valor_financiado,
        "prazo_meses": prazo_meses,
        "prazo_anos": prazo_meses // 12,
        "taxa_anual": taxa_anual,
        "taxa_mensal": round(taxa_anual / 12, 2),
        "parcela_price": round(parcela, 2),
        "primeira_parcela_sac": round(primeira_parcela_sac, 2),
        "total_pago_price": round(parcela * prazo_meses, 2),
        "juros_totais_price": round((parcela * prazo_meses) - valor_financiado, 2),
        "aviso": "Valores estimados. Consulte um banco para simulação oficial com análise de crédito."
    }


async def _exec_consultar_disponibilidade(
    args: Dict, db: AsyncSession, tenant_id: int, lead_id: int
) -> Dict:
    """Verifica disponibilidade de um imóvel."""
    from src.infrastructure.services.property_lookup_service import PropertyLookupService

    codigo = args.get("codigo_imovel", "").strip()
    if not codigo:
        return {"error": "Código do imóvel não informado"}

    try:
        service = PropertyLookupService(db=db, tenant_id=tenant_id)
        imovel = await service.buscar_por_codigo(codigo)

        if not imovel:
            return {
                "disponivel": False,
                "codigo": codigo,
                "message": f"Imóvel {codigo} não encontrado no sistema."
            }

        # Verifica status se disponível
        status = imovel.get("status", "disponivel")

        return {
            "disponivel": status.lower() in ["disponivel", "disponível", "ativo", "active"],
            "codigo": codigo,
            "status": status,
            "titulo": imovel.get("titulo"),
            "message": f"Imóvel {codigo} está {status}."
        }

    except Exception as e:
        logger.error(f"Erro consultando disponibilidade: {e}")
        return {"error": str(e)}


# =============================================================================
# FORMATAÇÃO DE RESULTADOS PARA CONTEXTO DA IA
# =============================================================================

def format_tool_result_for_ai(tool_name: str, result: Dict) -> str:
    """
    Formata o resultado de uma tool para ser incluído no contexto da IA.
    Retorna uma string que será adicionada às mensagens.
    """

    if result.get("error"):
        return f"[Sistema] Erro: {result['error']}"

    if tool_name == "buscar_imovel_por_codigo":
        if not result.get("found"):
            return f"[Sistema] {result.get('message', 'Imóvel não encontrado.')}"

        im = result.get("imovel", {})
        parts = [
            f"[Sistema] Imóvel encontrado:",
            f"- Código: {im.get('codigo')}",
            f"- Tipo: {im.get('tipo', 'N/A')}",
            f"- Local: {im.get('regiao', 'N/A')}",
        ]
        if im.get("quartos"):
            parts.append(f"- Quartos: {im['quartos']}")
        if im.get("banheiros"):
            parts.append(f"- Banheiros: {im['banheiros']}")
        if im.get("vagas"):
            parts.append(f"- Vagas: {im['vagas']}")
        if im.get("metragem"):
            parts.append(f"- Área: {im['metragem']}m²")
        if im.get("preco"):
            parts.append(f"- Preço: {im['preco']}")

        return "\n".join(parts)

    elif tool_name == "buscar_imoveis_por_criterios":
        if not result.get("found"):
            return f"[Sistema] {result.get('message', 'Nenhum imóvel encontrado.')}"

        imoveis = result.get("imoveis", [])
        count = result.get("count", len(imoveis))

        parts = [f"[Sistema] Encontrei {count} imóveis:"]
        for idx, im in enumerate(imoveis[:5], 1):
            line = f"{idx}. {im.get('tipo', 'Imóvel')} em {im.get('regiao', 'N/A')}"
            if im.get("quartos"):
                line += f", {im['quartos']} quartos"
            if im.get("preco"):
                line += f" - {im['preco']}"
            if im.get("codigo"):
                line += f" (cód: {im['codigo']})"
            parts.append(line)

        return "\n".join(parts)

    elif tool_name == "calcular_financiamento":
        return f"""[Sistema] Simulação de Financiamento:
- Valor do imóvel: R$ {result['valor_imovel']:,.2f}
- Entrada ({result['percentual_entrada']}%): R$ {result['entrada']:,.2f}
- Valor financiado: R$ {result['valor_financiado']:,.2f}
- Prazo: {result['prazo_anos']} anos ({result['prazo_meses']} meses)
- Taxa: {result['taxa_anual']}% ao ano
- Parcela estimada (Price): R$ {result['parcela_price']:,.2f}
- Primeira parcela (SAC): R$ {result['primeira_parcela_sac']:,.2f}
⚠️ {result['aviso']}"""

    elif tool_name == "consultar_disponibilidade":
        return f"[Sistema] {result.get('message', 'Informação de disponibilidade não encontrada.')}"

    # Fallback genérico
    return f"[Sistema] Resultado: {json.dumps(result, ensure_ascii=False)}"


# =============================================================================
# HELPERS
# =============================================================================

def get_tools_for_niche(niche_slug: str) -> List[Dict]:
    """
    Retorna as tools disponíveis para um nicho específico.

    Args:
        niche_slug: Slug do nicho (realestate, healthcare, services, etc)

    Returns:
        Lista de tools disponíveis
    """
    # Por enquanto, todas as tools são para imobiliário
    # Futuramente, podemos ter tools específicas por nicho

    if niche_slug in ["realestate", "imobiliaria", "real_estate", "imobiliario"]:
        return AVAILABLE_TOOLS

    # Para outros nichos, retorna lista vazia (sem function calling)
    return []


def should_use_tools(niche_slug: str, has_product: bool, has_imovel: bool) -> bool:
    """
    Determina se deve usar function calling na conversa.

    Args:
        niche_slug: Slug do nicho
        has_product: Se já tem produto detectado
        has_imovel: Se já tem imóvel de portal detectado

    Returns:
        True se deve usar tools
    """
    # Só usa tools para nicho imobiliário
    if niche_slug not in ["realestate", "imobiliaria", "real_estate", "imobiliario"]:
        return False

    # Se já tem imóvel específico, não precisa de tools (já tem contexto)
    # if has_imovel:
    #     return False

    return True
