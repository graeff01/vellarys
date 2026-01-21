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
    niche_template: Optional[str] = None


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
class ProductContext:
    """Contexto de produto ou serviço."""
    id: int
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    ai_instructions: Optional[str] = None
    qualification_questions: List[str] = field(default_factory=list)


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
    has_product: bool
    has_imovel_portal: bool
    has_lead_context: bool
    has_lead_profile: bool = False
    has_rag_context: bool = False
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


def extract_ai_context(tenant_name: str, settings: dict, niche_template: str = None) -> AIContext:
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
            niche_template=niche_template,
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

def build_product_context(prod: ProductContext) -> str:
    """
    Constrói o contexto do produto para adicionar ao prompt da IA.
    """
    sections = []
    
    sections.append(f"📦 PRODUTO/SERVIÇO: {prod.name.upper()}")
    
    if prod.status:
        sections.append(f"Status: {prod.status}")
    
    # Descrição
    if prod.description:
        desc = prod.description[:300] + "..." if len(prod.description) > 300 else prod.description
        sections.append(f"Sobre: {desc}")
    
    # Atributos dinâmicos
    if prod.attributes:
        sections.append("Características:")
        for key, value in prod.attributes.items():
            if value:
                # Formata a chave (ex: "faixa_preco" -> "Faixa Preco")
                label = key.replace("_", " ").title()
                sections.append(f"- {label}: {value}")
    
    # Instruções para IA
    if prod.ai_instructions:
        sections.append(f"INSTRUÇÕES: {prod.ai_instructions}")
    
    # Perguntas de qualificação
    if prod.qualification_questions:
        sections.append(f"PERGUNTE: {' | '.join(prod.qualification_questions[:3])}")
    
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


def build_lead_profile_context(profile: Dict[str, Any]) -> str:
    """
    Constrói contexto do perfil progressivo do lead para o prompt.
    Baseado em informações extraídas de conversas anteriores.

    Args:
        profile: Dicionário com perfil do lead (de custom_data["lead_profile"])

    Returns:
        String formatada para adicionar ao prompt da IA
    """
    if not profile:
        return ""

    parts = ["🧠 MEMÓRIA DO CLIENTE (conversas anteriores):"]

    # Preferências de imóvel
    prefs = profile.get("preferences", {})
    if prefs:
        pref_items = []
        if prefs.get("tipo_imovel"):
            pref_items.append(f"Tipo: {prefs['tipo_imovel']}")
        if prefs.get("quartos_minimo"):
            pref_items.append(f"Mín. {prefs['quartos_minimo']} quartos")
        if prefs.get("banheiros_minimo"):
            pref_items.append(f"Mín. {prefs['banheiros_minimo']} banheiros")
        if prefs.get("vagas_minimo"):
            pref_items.append(f"Mín. {prefs['vagas_minimo']} vagas")
        if prefs.get("metragem_minima"):
            pref_items.append(f"Mín. {prefs['metragem_minima']}m²")
        if prefs.get("bairros_interesse"):
            bairros = prefs['bairros_interesse'][:5]  # Limita a 5
            pref_items.append(f"Bairros: {', '.join(bairros)}")
        if prefs.get("caracteristicas"):
            caracts = prefs['caracteristicas'][:5]  # Limita a 5
            pref_items.append(f"Quer: {', '.join(caracts)}")

        if pref_items:
            parts.append("📍 Preferências: " + " | ".join(pref_items))

    # Orçamento
    budget = profile.get("budget_info", {})
    if budget:
        budget_items = []
        if budget.get("faixa_max"):
            budget_items.append(f"Máx R$ {budget['faixa_max']:,.0f}".replace(",", "."))
        if budget.get("faixa_min"):
            budget_items.append(f"Mín R$ {budget['faixa_min']:,.0f}".replace(",", "."))
        if budget.get("tem_entrada"):
            if budget.get("valor_entrada"):
                budget_items.append(f"Entrada R$ {budget['valor_entrada']:,.0f}".replace(",", "."))
            else:
                budget_items.append("Tem entrada")

        if budget_items:
            parts.append("💰 Orçamento: " + " | ".join(budget_items))

    # Timeline/Urgência
    timeline = profile.get("timeline_info", {})
    if timeline:
        timeline_items = []
        if timeline.get("urgencia"):
            urgencia_map = {"alta": "🔴 ALTA", "media": "🟡 MÉDIA", "baixa": "🟢 BAIXA"}
            timeline_items.append(f"Urgência: {urgencia_map.get(timeline['urgencia'], timeline['urgencia'])}")
        if timeline.get("prazo_descricao"):
            timeline_items.append(f"Prazo: {timeline['prazo_descricao']}")
        if timeline.get("motivo_mudanca"):
            motivo_map = {
                "casamento": "Casamento",
                "familia_crescendo": "Família crescendo",
                "trabalho": "Trabalho",
                "investimento": "Investimento",
                "upgrade": "Quer maior/melhor",
                "downsizing": "Quer menor",
                "primeiro_imovel": "1º imóvel",
            }
            timeline_items.append(f"Motivo: {motivo_map.get(timeline['motivo_mudanca'], timeline['motivo_mudanca'])}")

        if timeline_items:
            parts.append("⏰ " + " | ".join(timeline_items))

    # Família
    family = profile.get("family_info", {})
    if family:
        family_items = []
        if family.get("filhos"):
            family_items.append(f"{family['filhos']} filhos")
        elif family.get("tem_filhos"):
            family_items.append("Tem filhos")
        if family.get("estado_civil"):
            family_items.append(family['estado_civil'].title())
        if family.get("tem_pet"):
            pet_tipo = family.get("tipo_pet", "pet")
            family_items.append(f"Tem {pet_tipo}")
        if family.get("mora_com_idoso"):
            family_items.append("Mora com idoso")

        if family_items:
            parts.append("👨‍👩‍👧‍👦 Família: " + " | ".join(family_items))

    # Financeiro
    financial = profile.get("financial_info", {})
    if financial:
        fin_items = []
        if financial.get("usa_fgts"):
            if financial.get("valor_fgts"):
                fin_items.append(f"FGTS R$ {financial['valor_fgts']:,.0f}".replace(",", "."))
            else:
                fin_items.append("Vai usar FGTS")
        if financial.get("financiamento_aprovado"):
            fin_items.append("✅ Financiamento APROVADO")
        if financial.get("credito_aprovado"):
            fin_items.append("✅ Crédito APROVADO")
        if financial.get("pagamento_vista"):
            fin_items.append("💵 PAGA À VISTA!")
        if financial.get("programa_habitacional"):
            fin_items.append("Programa habitacional")
        if financial.get("banco_preferencia"):
            fin_items.append(f"Banco: {financial['banco_preferencia'].title()}")

        if fin_items:
            parts.append("🏦 Financeiro: " + " | ".join(fin_items))

    # Objeções
    objections = profile.get("objections", [])
    if objections:
        obj_map = {
            "preco": "💰 Preço",
            "localizacao": "📍 Localização",
            "decisao": "🤔 Indeciso",
            "consultar_familia": "👥 Consultar família",
            "documentacao": "📄 Burocracia",
            "reforma": "🔧 Reforma",
            "tamanho": "📐 Tamanho",
            "seguranca": "🔒 Segurança",
        }
        obj_labels = [obj_map.get(o, o) for o in objections[:4]]
        parts.append("⚠️ Objeções: " + " | ".join(obj_labels))

    # Preferências de contato
    contact = profile.get("contact_preferences", {})
    if contact:
        contact_items = []
        if contact.get("horario_preferido"):
            contact_items.append(f"Prefere: {contact['horario_preferido']}")
        if contact.get("canal_preferido"):
            contact_items.append(f"Via: {contact['canal_preferido']}")

        if contact_items:
            parts.append("📞 Contato: " + " | ".join(contact_items))

    # Instruções finais
    if len(parts) > 1:  # Se tem alguma informação além do header
        parts.append("")
        parts.append("⚠️ USE estas informações! NÃO pergunte o que já sabe!")

    return "\n".join(parts) if len(parts) > 1 else ""


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
    product: Optional[ProductContext] = None,
    imovel_portal: Optional[ImovelPortalContext] = None,
    lead_profile: Optional[Dict[str, Any]] = None,
    rag_context: Optional[str] = None,
    include_security: bool = True,
    is_simulation: bool = False,
) -> PromptBuildResult:
    """
    Constrói o prompt completo para a IA.
    
    V2: PRIORIZA CONTEXTOS DINÂMICOS!
    
    Ordem de prioridade (do mais importante para menos):
    1. Contexto do imóvel de portal (CRÍTICO - cliente perguntou sobre isso!)
    2. Contexto do lead (evita perguntas burras)
    3. Contexto do produto/serviço
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
    
    # Contexto do produto
    if product:
        prod_context = build_product_context(product)
        dynamic_parts.append(prod_context)
        dynamic_parts.append(f"⚠️ Cliente interessado em {product.name}. Use as informações acima!")
        logger.info(f"✅ Contexto produto adicionado: {product.name}")
    
    # Contexto do lead
    if lead_context:
        lead_info = build_lead_info_context(lead_context)
        dynamic_parts.append(lead_info)
        logger.info(f"✅ Contexto lead adicionado: {lead_context.lead_id}")

    # Perfil progressivo do lead (memória de longo prazo)
    if lead_profile:
        profile_context = build_lead_profile_context(lead_profile)
        if profile_context:
            dynamic_parts.append(profile_context)
            logger.info("✅ Perfil progressivo do lead adicionado")

    # Contexto RAG (base de conhecimento)
    if rag_context:
        dynamic_parts.append(rag_context)
        logger.info("✅ Contexto RAG adicionado")
    
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
        niche_template=ai_context.niche_template,
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
        if not product and not imovel_portal:
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
                f"Imóvel: {bool(imovel_portal)} | Prod: {bool(product)} | "
                f"Lead: {bool(lead_context)} | Sim: {is_simulation}")
    
    return PromptBuildResult(
        system_prompt=final_prompt,
        prompt_length=len(final_prompt),
        has_identity=bool(ai_context.identity),
        has_product=bool(product),
        has_imovel_portal=bool(imovel_portal),
        has_lead_context=bool(lead_context),
        has_lead_profile=bool(lead_profile),
        has_rag_context=bool(rag_context),
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
        (r"quanto.*parcela", "interesse em valores"),
        (r"valor.*parcela", "interesse em valores"),
        (r"simula[çc][ãa]o", "interesse em simulação"),
        (r"aceita.*fgts", "uso de FGTS"),
        (r"tem.*fgts", "uso de FGTS"),
        (r"usar.*fgts", "uso de FGTS"),
        (r"tenho.*entrada", "tem entrada"),
        (r"valor.*entrada", "tem entrada"),
        (r"quando.*posso.*visitar", "quer visitar"),
        (r"quero.*visitar", "quer visitar"),
        (r"posso.*ir.*hoje", "quer ir hoje"),
        (r"quero.*ver.*im[oó]vel", "quer visitar"),
        (r"agendar.*visita", "quer visitar"),
        (r"quero.*fechar", "quer fechar"),
        (r"vamos.*fechar", "quer fechar"),
        (r"manda.*localiza[çc][ãa]o", "pediu localização"),
        (r"manda.*fotos", "pediu fotos"),
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

def product_to_context(prod) -> ProductContext:
    """Converte uma entidade Product do banco para ProductContext."""
    return ProductContext(
        id=prod.id,
        name=prod.name,
        description=prod.description,
        status=prod.status,
        attributes=prod.attributes or {},
        ai_instructions=prod.ai_instructions,
        qualification_questions=prod.qualification_questions or [],
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