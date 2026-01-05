"""
AI CONTEXT BUILDER - FONTE ÚNICA DE VERDADE (V2)
=================================================

CORREÇÃO: Prioriza contexto do imóvel e lead sobre o prompt base.
Quando trunca, corta o prompt base (menos importante), não os contextos dinâmicos.

ÚLTIMA ATUALIZAÇÃO: 2025-01-XX
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

MAX_PROMPT_LENGTH = 15000
# Reserva espaço para contextos dinâmicos (imóvel, lead, empreendimento)
RESERVED_FOR_DYNAMIC_CONTEXT = 4000
# Máximo para o prompt base
MAX_BASE_PROMPT = MAX_PROMPT_LENGTH - RESERVED_FOR_DYNAMIC_CONTEXT  # 11000

NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AIContext:
    """Contexto completo extraído para a IA."""
    company_name: str
    niche_id: str
    tone: str = "cordial"
    identity: Optional[Dict] = None
    scope_config: Optional[Dict] = None
    faq_items: List[Dict] = field(default_factory=list)
    custom_questions: List[str] = field(default_factory=list)
    custom_rules: List[str] = field(default_factory=list)
    scope_description: str = ""
    out_of_scope_message: str = ""
    custom_prompt: Optional[str] = None


@dataclass
class LeadContext:
    """Contexto do lead para evitar perguntas repetidas."""
    lead_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    message_count: int = 0
    qualification: Optional[str] = None
    status: Optional[str] = None
    custom_data: Optional[Dict] = None


@dataclass
class EmpreendimentoContext:
    """Contexto de empreendimento imobiliário."""
    id: int
    nome: str
    descricao: Optional[str] = None
    status: Optional[str] = None
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    descricao_localizacao: Optional[str] = None
    tipologias: List[str] = field(default_factory=list)
    metragem_minima: Optional[float] = None
    metragem_maxima: Optional[float] = None
    vagas_minima: Optional[int] = None
    vagas_maxima: Optional[int] = None
    torres: Optional[int] = None
    andares: Optional[int] = None
    total_unidades: Optional[int] = None
    previsao_entrega: Optional[str] = None
    preco_minimo: Optional[float] = None
    preco_maximo: Optional[float] = None
    aceita_financiamento: bool = False
    aceita_fgts: bool = False
    aceita_permuta: bool = False
    aceita_consorcio: bool = False
    condicoes_especiais: Optional[str] = None
    itens_lazer: List[str] = field(default_factory=list)
    diferenciais: List[str] = field(default_factory=list)
    instrucoes_ia: Optional[str] = None
    perguntas_qualificacao: List[str] = field(default_factory=list)


@dataclass
class ImovelPortalContext:
    """Contexto de imóvel vindo de portal (código específico)."""
    codigo: str
    titulo: Optional[str] = None
    tipo: Optional[str] = None
    regiao: Optional[str] = None
    quartos: Optional[str] = None
    banheiros: Optional[str] = None
    vagas: Optional[str] = None
    metragem: Optional[str] = None
    preco: Optional[str] = None
    descricao: Optional[str] = None


@dataclass
class PromptBuildResult:
    """Resultado da construção do prompt."""
    system_prompt: str
    prompt_length: int
    has_identity: bool
    has_empreendimento: bool
    has_imovel_portal: bool
    has_lead_context: bool
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# FUNÇÕES DE MIGRAÇÃO E EXTRAÇÃO
# =============================================================================

def migrate_settings_if_needed(settings: dict) -> dict:
    """Migra settings do formato antigo para o novo (com identity)."""
    if not settings:
        return {}
    
    if "identity" in settings:
        return settings
    
    try:
        migrated = dict(settings)
        
        migrated["identity"] = {
            "description": settings.get("scope_description", ""),
            "products_services": [],
            "not_offered": [],
            "tone_style": {
                "tone": settings.get("tone", "cordial"),
                "personality_traits": [],
                "communication_style": "",
                "avoid_phrases": [],
                "use_phrases": [],
            },
            "target_audience": {"description": "", "segments": [], "pain_points": []},
            "business_rules": settings.get("custom_rules", []),
            "differentials": [],
            "keywords": [],
            "required_questions": settings.get("custom_questions", []),
            "required_info": [],
            "additional_context": "",
        }
        
        migrated["basic"] = {
            "niche": settings.get("niche", "services"),
            "company_name": settings.get("company_name", ""),
        }
        
        migrated["scope"] = {
            "enabled": settings.get("scope_enabled", True),
            "description": settings.get("scope_description", ""),
            "allowed_topics": [],
            "blocked_topics": [],
            "out_of_scope_message": settings.get("out_of_scope_message", 
                "Desculpe, não tenho informações sobre isso."),
        }
        
        migrated["faq"] = {
            "enabled": settings.get("faq_enabled", True),
            "items": settings.get("faq_items", []),
        }
        
        return migrated
    except Exception as e:
        logger.error(f"Erro migrando settings: {e}")
        return settings


def extract_ai_context(tenant_name: str, settings: dict) -> AIContext:
    """
    Extrai contexto completo para a IA a partir dos settings.
    """
    try:
        identity = settings.get("identity", {})
        basic = settings.get("basic", {})
        scope = settings.get("scope", {})
        faq = settings.get("faq", {})
        
        company_name = basic.get("company_name") or settings.get("company_name") or tenant_name
        niche_id = basic.get("niche") or settings.get("niche") or "services"
        tone = identity.get("tone_style", {}).get("tone") or settings.get("tone") or "cordial"
        
        faq_items = []
        if faq.get("enabled", True):
            faq_items = faq.get("items", []) or settings.get("faq_items", [])
        
        custom_questions = identity.get("required_questions", []) or settings.get("custom_questions", [])
        custom_rules = identity.get("business_rules", []) or settings.get("custom_rules", [])
        scope_description = scope.get("description") or settings.get("scope_description", "")
        
        default_out_of_scope = (
            f"Desculpe, não posso ajudá-lo com isso. "
            f"A {company_name} trabalha com {scope_description or 'nossos produtos e serviços'}. "
            f"Posso te ajudar com algo relacionado?"
        )
        
        out_of_scope_message = (
            scope.get("out_of_scope_message") or 
            settings.get("out_of_scope_message") or 
            default_out_of_scope
        )
        
        return AIContext(
            company_name=company_name,
            niche_id=niche_id,
            tone=tone,
            identity=identity if identity else None,
            scope_config=scope if scope else None,
            faq_items=faq_items,
            custom_questions=custom_questions,
            custom_rules=custom_rules,
            scope_description=scope_description,
            out_of_scope_message=out_of_scope_message,
            custom_prompt=settings.get("custom_prompt"),
        )
    except Exception as e:
        logger.error(f"Erro extraindo contexto IA: {e}")
        return AIContext(
            company_name=tenant_name,
            niche_id="services",
            tone="cordial",
            out_of_scope_message="Desculpe, não posso ajudá-lo com isso.",
        )


# =============================================================================
# FUNÇÕES DE CONSTRUÇÃO DE CONTEXTO
# =============================================================================

def build_empreendimento_context(emp: EmpreendimentoContext) -> str:
    """
    Constrói o contexto do empreendimento para adicionar ao prompt da IA.
    VERSÃO COMPACTA para economizar tokens.
    """
    sections = []
    
    sections.append(f"🏢 EMPREENDIMENTO: {emp.nome.upper()}")
    
    # Status
    status_map = {
        "lancamento": "🚀 Lançamento",
        "em_obras": "🏗️ Em Obras",
        "pronto_para_morar": "🏠 Pronto para Morar",
    }
    if emp.status:
        sections.append(f"Status: {status_map.get(emp.status, emp.status)}")
    
    # Descrição (resumida)
    if emp.descricao:
        desc = emp.descricao[:200] + "..." if len(emp.descricao) > 200 else emp.descricao
        sections.append(f"Sobre: {desc}")
    
    # Localização compacta
    loc_parts = []
    if emp.bairro:
        loc_parts.append(emp.bairro)
    if emp.cidade:
        loc_parts.append(emp.cidade)
    if loc_parts:
        sections.append(f"Local: {', '.join(loc_parts)}")
    
    # Tipologias
    if emp.tipologias:
        sections.append(f"Tipologias: {', '.join(emp.tipologias)}")
    
    # Metragem
    if emp.metragem_minima or emp.metragem_maxima:
        if emp.metragem_minima and emp.metragem_maxima:
            sections.append(f"Metragem: {emp.metragem_minima}m² a {emp.metragem_maxima}m²")
        elif emp.metragem_minima:
            sections.append(f"Metragem: a partir de {emp.metragem_minima}m²")
    
    # Preços
    if emp.preco_minimo or emp.preco_maximo:
        if emp.preco_minimo and emp.preco_maximo:
            preco = f"R$ {emp.preco_minimo:,.0f} a R$ {emp.preco_maximo:,.0f}".replace(",", ".")
        elif emp.preco_minimo:
            preco = f"A partir de R$ {emp.preco_minimo:,.0f}".replace(",", ".")
        else:
            preco = f"Até R$ {emp.preco_maximo:,.0f}".replace(",", ".")
        sections.append(f"Preço: {preco}")
    
    # Condições de pagamento
    condicoes = []
    if emp.aceita_financiamento:
        condicoes.append("Financiamento")
    if emp.aceita_fgts:
        condicoes.append("FGTS")
    if emp.aceita_permuta:
        condicoes.append("Permuta")
    if condicoes:
        sections.append(f"Aceita: {', '.join(condicoes)}")
    
    # Instruções para IA
    if emp.instrucoes_ia:
        sections.append(f"INSTRUÇÕES: {emp.instrucoes_ia}")
    
    # Perguntas de qualificação
    if emp.perguntas_qualificacao:
        sections.append(f"PERGUNTE: {' | '.join(emp.perguntas_qualificacao[:3])}")
    
    return "\n".join(sections)


def build_imovel_portal_context(imovel: ImovelPortalContext) -> str:
    """
    Constrói contexto do imóvel de portal para o prompt.
    VERSÃO COMPACTA E PRIORITÁRIA.
    """
    cod = imovel.codigo or 'N/A'
    quartos = imovel.quartos or 'N/A'
    banheiros = imovel.banheiros or 'N/A'
    vagas = imovel.vagas or 'N/A'
    metragem = imovel.metragem or 'N/A'
    preco = imovel.preco or 'Consulte'
    regiao = imovel.regiao or 'N/A'
    tipo = imovel.tipo or 'Imóvel'
    
    return f"""
🏠 IMÓVEL CÓDIGO {cod} - USE ESTES DADOS!
Tipo: {tipo} | Local: {regiao}
Quartos: {quartos} | Banheiros: {banheiros} | Vagas: {vagas}
Área: {metragem}m² | Preço: {preco}

⚠️ RESPONDA SOBRE ESTE IMÓVEL:
- Mencione os dados acima (quartos, preço, região)
- Pergunte: "Pra morar ou investir?" ou "Quando pensa em se mudar?"
- Máximo 3 linhas, tom casual de WhatsApp
- NÃO peça WhatsApp (já está no WhatsApp!)

EXEMPLO: "Show! Essa casa de {quartos} quartos em {regiao} tá {preco}. Quando você pensa em se mudar?"
"""


def build_lead_info_context(lead: LeadContext) -> str:
    """
    Constrói contexto do lead para evitar perguntas repetidas.
    VERSÃO COMPACTA.
    """
    return f"""
🧠 INFORMAÇÕES DO LEAD:
- Nome: {lead.name or "NÃO INFORMADO"}
- Telefone: {lead.phone} (JÁ ESTÁ NO WHATSAPP!)
- Mensagens trocadas: {lead.message_count}
- Qualificação: {lead.qualification or "novo"}

❌ NÃO PERGUNTE: WhatsApp/telefone, nome se já tem
✅ PERGUNTE: finalidade, prazo, orçamento, preferências

⚠️ SE CLIENTE DISSER "TENHO DINHEIRO À VISTA" → É LEAD QUENTE! Passe pro corretor!
"""


def build_security_instructions(
    company_name: str,
    scope_description: str,
    out_of_scope_message: str
) -> str:
    """
    Constrói instruções de segurança (versão compacta).
    """
    return f"""
🔒 SEGURANÇA: Você é assistente da {company_name}.
Escopo: {scope_description or "produtos e serviços da empresa"}
Fora do escopo: "{out_of_scope_message}"
"""


# =============================================================================
# FUNÇÃO PRINCIPAL DE CONSTRUÇÃO DO PROMPT (V2 - PRIORIZA CONTEXTOS DINÂMICOS)
# =============================================================================

def build_complete_prompt(
    ai_context: AIContext,
    lead_context: Optional[LeadContext] = None,
    empreendimento: Optional[EmpreendimentoContext] = None,
    imovel_portal: Optional[ImovelPortalContext] = None,
    include_security: bool = True,
    is_simulation: bool = False,
) -> PromptBuildResult:
    """
    Constrói o prompt completo para a IA.
    
    V2: PRIORIZA CONTEXTOS DINÂMICOS!
    
    Ordem de prioridade (do mais importante para menos):
    1. Contexto do imóvel de portal (CRÍTICO - cliente perguntou sobre isso!)
    2. Contexto do lead (evita perguntas burras)
    3. Contexto do empreendimento
    4. Prompt base do nicho (TRUNCÁVEL se necessário)
    5. Instruções de segurança
    """
    from src.domain.prompts import build_system_prompt
    
    warnings = []
    
    # =========================================================================
    # PASSO 1: Constrói contextos dinâmicos PRIMEIRO (são prioritários!)
    # =========================================================================
    dynamic_parts = []
    
    # Contexto do imóvel de portal (MAIS IMPORTANTE!)
    if imovel_portal:
        imovel_context = build_imovel_portal_context(imovel_portal)
        dynamic_parts.append(imovel_context)
        logger.info(f"✅ Contexto imóvel portal adicionado: {imovel_portal.codigo}")
    
    # Contexto do empreendimento
    if empreendimento:
        emp_context = build_empreendimento_context(empreendimento)
        dynamic_parts.append(emp_context)
        dynamic_parts.append(f"⚠️ Cliente interessado em {empreendimento.nome}. Use as informações acima!")
        logger.info(f"✅ Contexto empreendimento adicionado: {empreendimento.nome}")
    
    # Contexto do lead
    if lead_context:
        lead_info = build_lead_info_context(lead_context)
        dynamic_parts.append(lead_info)
        logger.info(f"✅ Contexto lead adicionado: {lead_context.lead_id}")
    
    # Calcula espaço usado pelos contextos dinâmicos
    dynamic_context = "\n".join(dynamic_parts)
    dynamic_length = len(dynamic_context)
    
    logger.info(f"📊 Contextos dinâmicos: {dynamic_length} chars")
    
    # =========================================================================
    # PASSO 2: Calcula espaço disponível para prompt base
    # =========================================================================
    available_for_base = MAX_PROMPT_LENGTH - dynamic_length - 500  # 500 de margem
    
    if available_for_base < 5000:
        available_for_base = 5000  # Mínimo para o prompt base funcionar
        warnings.append(f"Espaço limitado para prompt base: {available_for_base} chars")
    
    logger.info(f"📊 Espaço disponível para prompt base: {available_for_base} chars")
    
    # =========================================================================
    # PASSO 3: Constrói prompt base (TRUNCA SE NECESSÁRIO)
    # =========================================================================
    base_prompt = build_system_prompt(
        niche_id=ai_context.niche_id,
        company_name=ai_context.company_name,
        tone=ai_context.tone,
        custom_questions=ai_context.custom_questions,
        custom_rules=ai_context.custom_rules,
        custom_prompt=ai_context.custom_prompt,
        faq_items=ai_context.faq_items,
        scope_description=ai_context.scope_description,
        lead_context=None,  # Já adicionamos separadamente
        identity=ai_context.identity,
        scope_config=ai_context.scope_config,
    )
    
    original_base_length = len(base_prompt)
    
    # Trunca o prompt base se necessário (NÃO os contextos dinâmicos!)
    if len(base_prompt) > available_for_base:
        logger.warning(f"⚠️ Truncando prompt BASE de {len(base_prompt)} para {available_for_base} chars")
        warnings.append(f"Prompt base truncado de {len(base_prompt)} para {available_for_base} chars")
        
        # Trunca preservando a estrutura
        base_prompt = base_prompt[:available_for_base]
        
        # Tenta cortar em um ponto lógico (última quebra de linha)
        last_newline = base_prompt.rfind('\n')
        if last_newline > available_for_base - 500:
            base_prompt = base_prompt[:last_newline]
    
    # PASSO 4: Monta prompt final (CONTEXTOS DINÂMICOS VÊM PRIMEIRO!)
    # =========================================================================
    # CORREÇÃO CRÍTICA: Contextos dinâmicos ANTES do prompt base!
    # GPT models dão mais peso ao INÍCIO do prompt.
    # Ordem: Dinâmicos → Base → Segurança

    prompt_parts = []

    # 1. CONTEXTOS DINÂMICOS PRIMEIRO (maior prioridade na atenção da IA)
    if dynamic_context:
        prompt_parts.append("=" * 80)
        prompt_parts.append("🔥 CONTEXTO ESPECÍFICO DESTA CONVERSA - LEIA PRIMEIRO!")
        prompt_parts.append("=" * 80)
        prompt_parts.append(dynamic_context)
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("⚠️ USE AS INFORMAÇÕES ACIMA PARA RESPONDER!")
        prompt_parts.append("=" * 80)
        prompt_parts.append("\n")

    # 2. PROMPT BASE (regras gerais)
    prompt_parts.append(base_prompt)
    
    # Instruções de segurança (compactas)
    if include_security and ai_context.scope_description:
        if not empreendimento and not imovel_portal:
            security = build_security_instructions(
                company_name=ai_context.company_name,
                scope_description=ai_context.scope_description,
                out_of_scope_message=ai_context.out_of_scope_message,
            )
            prompt_parts.append(security)
    
    # Aviso de simulação
    if is_simulation:
        prompt_parts.append("\n🧪 MODO SIMULAÇÃO - Responda como faria com cliente real.")
    
    # Junta tudo
    final_prompt = "\n".join(prompt_parts)
    
    # Verificação final
    if len(final_prompt) > MAX_PROMPT_LENGTH:
        logger.error(f"❌ ERRO: Prompt ainda muito longo ({len(final_prompt)} chars)!")
        warnings.append(f"Prompt final excede limite: {len(final_prompt)} > {MAX_PROMPT_LENGTH}")
        # Trunca forçado (último recurso)
        final_prompt = final_prompt[:MAX_PROMPT_LENGTH]
    
    logger.info(f"📝 Prompt FINAL: {len(final_prompt)} chars | "
                f"Base: {original_base_length}→{len(base_prompt)} | "
                f"Dinâmico: {dynamic_length} | "
                f"Imóvel: {bool(imovel_portal)} | Emp: {bool(empreendimento)} | "
                f"Lead: {bool(lead_context)} | Sim: {is_simulation}")
    
    return PromptBuildResult(
        system_prompt=final_prompt,
        prompt_length=len(final_prompt),
        has_identity=bool(ai_context.identity),
        has_empreendimento=bool(empreendimento),
        has_imovel_portal=bool(imovel_portal),
        has_lead_context=bool(lead_context),
        warnings=warnings,
    )


# =============================================================================
# FUNÇÕES DE DETECÇÃO DE LEAD QUENTE
# =============================================================================

def detect_hot_lead_signals(content: str) -> tuple[bool, Optional[str]]:
    """
    Detecta sinais de lead quente na mensagem.
    
    Returns:
        Tuple (is_hot, matched_signal)
    """
    content_lower = content.lower()
    
    hot_patterns = [
        (r"tenho.*dinheiro.*vista", "dinheiro à vista"),
        (r"tenho.*valor.*vista", "valor à vista"),
        (r"dinheiro.*vista", "dinheiro à vista"),
        (r"pagamento.*vista", "pagamento à vista"),
        (r"pagar.*vista", "pagar à vista"),
        (r"tenho.*\d+.*mil.*vista", "valor específico à vista"),
        (r"tenho.*aprovado", "crédito aprovado"),
        (r"financiamento.*aprovado", "financiamento aprovado"),
        (r"credito.*aprovado", "crédito aprovado"),
        (r"preciso.*urgente", "urgência"),
        (r"urgente.*mudar", "urgência para mudar"),
        (r"mudar.*urgente", "urgência para mudar"),
        (r"tenho.*entrada", "tem entrada"),
        (r"quando.*posso.*visitar", "quer visitar"),
        (r"quero.*visitar", "quer visitar"),
        (r"posso.*ir.*hoje", "quer ir hoje"),
        (r"quero.*fechar", "quer fechar"),
        (r"vamos.*fechar", "quer fechar"),
    ]
    
    for pattern, signal_name in hot_patterns:
        if re.search(pattern, content_lower):
            return True, signal_name
    
    return False, None


def analyze_qualification_from_message(
    user_message: str,
    ai_response: str = "",
    history: List[dict] = None
) -> str:
    """
    Analisa a conversa e retorna uma dica de qualificação.
    """
    message_lower = user_message.lower()
    history = history or []
    
    is_hot, _ = detect_hot_lead_signals(user_message)
    if is_hot:
        return "🔥 Lead QUENTE - Cliente demonstra intenção de compra/ação"
    
    warm_signals = [
        "quanto custa", "qual o preço", "tem financiamento", "como funciona",
        "quais as opções", "me interessei", "gostaria de saber", "pode me explicar",
        "estou pesquisando", "estou procurando", "qual o endereço", "onde fica",
        "horário de funcionamento", "vocês trabalham com"
    ]
    
    for signal in warm_signals:
        if signal in message_lower:
            return "🟡 Lead MORNO - Cliente demonstra interesse"
    
    total_messages = len(history) + 1
    if total_messages >= 5:
        return "🟡 Lead MORNO - Conversa em andamento"
    
    return "🔵 Lead FRIO - Início da conversa"


# =============================================================================
# HELPERS PARA CONVERSÃO DE ENTIDADES
# =============================================================================

def empreendimento_to_context(emp) -> EmpreendimentoContext:
    """Converte uma entidade Empreendimento do banco para EmpreendimentoContext."""
    return EmpreendimentoContext(
        id=emp.id,
        nome=emp.nome,
        descricao=emp.descricao,
        status=emp.status,
        endereco=emp.endereco,
        bairro=emp.bairro,
        cidade=emp.cidade,
        estado=emp.estado,
        descricao_localizacao=emp.descricao_localizacao,
        tipologias=emp.tipologias or [],
        metragem_minima=emp.metragem_minima,
        metragem_maxima=emp.metragem_maxima,
        vagas_minima=emp.vagas_minima,
        vagas_maxima=emp.vagas_maxima,
        torres=emp.torres,
        andares=emp.andares,
        total_unidades=emp.total_unidades,
        previsao_entrega=emp.previsao_entrega,
        preco_minimo=emp.preco_minimo,
        preco_maximo=emp.preco_maximo,
        aceita_financiamento=emp.aceita_financiamento or False,
        aceita_fgts=emp.aceita_fgts or False,
        aceita_permuta=emp.aceita_permuta or False,
        aceita_consorcio=emp.aceita_consorcio or False,
        condicoes_especiais=emp.condicoes_especiais,
        itens_lazer=emp.itens_lazer or [],
        diferenciais=emp.diferenciais or [],
        instrucoes_ia=emp.instrucoes_ia,
        perguntas_qualificacao=emp.perguntas_qualificacao or [],
    )


def lead_to_context(lead, message_count: int = 0) -> LeadContext:
    """Converte uma entidade Lead do banco para LeadContext."""
    return LeadContext(
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
        created_at=lead.created_at,
        message_count=message_count,
        qualification=lead.qualification,
        status=lead.status,
        custom_data=lead.custom_data,
    )


def imovel_dict_to_context(imovel: dict) -> ImovelPortalContext:
    """Converte um dicionário de imóvel para ImovelPortalContext."""
    return ImovelPortalContext(
        codigo=imovel.get("codigo", ""),
        titulo=imovel.get("titulo"),
        tipo=imovel.get("tipo"),
        regiao=imovel.get("regiao"),
        quartos=imovel.get("quartos"),
        banheiros=imovel.get("banheiros"),
        vagas=imovel.get("vagas"),
        metragem=imovel.get("metragem"),
        preco=imovel.get("preco"),
        descricao=imovel.get("descricao"),
    )