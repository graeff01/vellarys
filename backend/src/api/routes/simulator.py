"""
ROTAS: SIMULADOR DE CONVERSA (VERSÃO CORRIGIDA)
=================================================

Endpoint para testar a IA sem criar leads reais.
Permite que gestores testem as configurações antes de ativar.

CORREÇÕES:
- Agora carrega a Identity completa (description, products, context)
- Usa as mesmas funções de contexto do process_message
- Suporta formato novo e antigo de settings
- Injeta informações da empresa no prompt
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import logging

from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user
from src.domain.entities import User, Tenant, Empreendimento
from src.infrastructure.services import (
    chat_completion,
    detect_sentiment,
    calculate_typing_delay,
)
from src.domain.prompts import get_niche_config, build_system_prompt

logger = logging.getLogger(__name__)
# Nichos que podem ter empreendimentos
NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]
router = APIRouter(prefix="/simulator", tags=["Simulador"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SimulatorMessage(BaseModel):
    role: str
    content: str


class SimulatorChatRequest(BaseModel):
    message: str
    session_id: str
    history: Optional[List[SimulatorMessage]] = []


class SimulatorChatResponse(BaseModel):
    reply: str
    typing_delay: float
    sentiment: str
    qualification_hint: str


# =============================================================================
# HELPERS - Migração e Extração de Contexto
# =============================================================================

def migrate_settings_if_needed(settings: dict) -> dict:
    """Migra settings do formato antigo para o novo (com identity)."""
    if not settings:
        return {}
    
    if "identity" in settings:
        return settings
    
    # Formato antigo - migra
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


def extract_ai_context(tenant: Tenant, settings: dict) -> dict:
    """Extrai contexto necessário para a IA."""
    identity = settings.get("identity", {})
    basic = settings.get("basic", {})
    scope = settings.get("scope", {})
    faq = settings.get("faq", {})
    
    # Valores com fallback para formato antigo
    company_name = basic.get("company_name") or settings.get("company_name") or tenant.name
    niche_id = basic.get("niche") or settings.get("niche") or "services"
    tone = identity.get("tone_style", {}).get("tone") or settings.get("tone") or "cordial"
    
    # FAQ
    faq_items = []
    if faq.get("enabled", True):
        faq_items = faq.get("items", []) or settings.get("faq_items", [])
    
    # Perguntas e regras
    custom_questions = identity.get("required_questions", []) or settings.get("custom_questions", [])
    custom_rules = identity.get("business_rules", []) or settings.get("custom_rules", [])
    
    # Escopo
    scope_description = scope.get("description") or settings.get("scope_description", "")
    out_of_scope_message = (
        scope.get("out_of_scope_message") or 
        settings.get("out_of_scope_message") or 
        "Desculpe, não posso ajudá-lo com isso."
    )
    
    return {
        "company_name": company_name,
        "niche_id": niche_id,
        "tone": tone,
        "identity": identity if identity else None,
        "scope_config": scope if scope else None,
        "faq_items": faq_items,
        "custom_questions": custom_questions,
        "custom_rules": custom_rules,
        "scope_description": scope_description,
        "out_of_scope_message": out_of_scope_message,
        "custom_prompt": settings.get("custom_prompt"),
    }


def build_identity_section(identity: dict, company_name: str) -> str:
    """Constrói a seção de identidade para o prompt."""
    if not identity:
        return ""
    
    sections = []
    
    # Descrição da empresa
    if identity.get("description"):
        sections.append(f"**Sobre a empresa:**\n{identity['description']}")
    
    # Produtos/Serviços
    if identity.get("products_services"):
        products = ", ".join(identity["products_services"])
        sections.append(f"**Produtos/Serviços oferecidos:**\n{products}")
    
    # O que NÃO oferece
    if identity.get("not_offered"):
        not_offered = ", ".join(identity["not_offered"])
        sections.append(f"**O que NÃO oferecemos (não mencione esses serviços):**\n{not_offered}")
    
    # Diferenciais
    if identity.get("differentials"):
        diffs = ", ".join(identity["differentials"])
        sections.append(f"**Nossos diferenciais:**\n{diffs}")
    
    # Público-alvo
    target = identity.get("target_audience", {})
    if target.get("description"):
        sections.append(f"**Público-alvo:**\n{target['description']}")
    
    # Tom de voz
    tone_style = identity.get("tone_style", {})
    if tone_style.get("personality_traits"):
        traits = ", ".join(tone_style["personality_traits"])
        sections.append(f"**Personalidade no atendimento:**\n{traits}")
    
    if tone_style.get("communication_style"):
        sections.append(f"**Estilo de comunicação:**\n{tone_style['communication_style']}")
    
    if tone_style.get("use_phrases"):
        phrases = ", ".join(tone_style["use_phrases"][:5])
        sections.append(f"**Expressões preferidas:**\n{phrases}")
    
    if tone_style.get("avoid_phrases"):
        avoid = ", ".join(tone_style["avoid_phrases"][:5])
        sections.append(f"**Expressões a evitar:**\n{avoid}")
    
    # Contexto adicional (IMPORTANTE!)
    if identity.get("additional_context"):
        sections.append(f"**Informações importantes:**\n{identity['additional_context']}")
    
    # Regras de negócio
    if identity.get("business_rules"):
        rules = "\n".join([f"- {r}" for r in identity["business_rules"]])
        sections.append(f"**Regras de atendimento:**\n{rules}")
    
    # Perguntas obrigatórias
    if identity.get("required_questions"):
        questions = "\n".join([f"- {q}" for q in identity["required_questions"]])
        sections.append(f"**Perguntas que você deve fazer:**\n{questions}")
    
    # Informações a coletar
    if identity.get("required_info"):
        info_map = {
            "nome": "Nome do cliente",
            "telefone": "Telefone",
            "email": "E-mail",
            "cidade": "Cidade",
            "bairro": "Bairro",
            "data_preferencia": "Data preferida",
            "horario_preferencia": "Horário preferido",
            "orcamento": "Orçamento",
            "como_conheceu": "Como conheceu a empresa",
        }
        info_list = [info_map.get(i, i) for i in identity["required_info"]]
        sections.append(f"**Informações que você deve coletar:**\n{', '.join(info_list)}")
    
    if sections:
        return "\n\n".join(sections)
    
    return ""


async def detect_empreendimento_for_simulator(
    db: AsyncSession,
    tenant_id: int,
    message: str,
    history: List[SimulatorMessage],
    niche_id: str,
) -> Optional[Empreendimento]:
    """Detecta empreendimento na mensagem atual OU no histórico."""
    from sqlalchemy import select
    
    if niche_id.lower() not in NICHOS_IMOBILIARIOS:
        return None
    
    try:
        result = await db.execute(
            select(Empreendimento)
            .where(Empreendimento.tenant_id == tenant_id)
            .where(Empreendimento.ativo == True)
            .order_by(Empreendimento.prioridade.desc())
        )
        empreendimentos = result.scalars().all()
        
        if not empreendimentos:
            return None
        
        # Verifica na mensagem atual
        message_lower = message.lower()
        for emp in empreendimentos:
            if emp.gatilhos:
                for gatilho in emp.gatilhos:
                    if gatilho.lower() in message_lower:
                        logger.info(f"🏢 Simulador - Empreendimento detectado: {emp.nome}")
                        return emp
        
        # Verifica no histórico (caso já tenha mencionado antes)
        for msg in history:
            msg_lower = msg.content.lower()
            for emp in empreendimentos:
                if emp.gatilhos:
                    for gatilho in emp.gatilhos:
                        if gatilho.lower() in msg_lower:
                            logger.info(f"🏢 Simulador - Empreendimento no histórico: {emp.nome}")
                            return emp
        
        return None
    except Exception as e:
        logger.error(f"Erro detectando empreendimento no simulador: {e}")
        return None


def build_empreendimento_context(emp: Empreendimento) -> str:
    """Constrói contexto do empreendimento para o prompt."""
    sections = []
    
    sections.append(f"\n{'=' * 50}")
    sections.append(f"🏢 EMPREENDIMENTO: {emp.nome.upper()}")
    sections.append(f"{'=' * 50}")
    
    if emp.descricao:
        sections.append(f"\n**Descrição:** {emp.descricao}")
    
    # Localização
    loc = []
    if emp.endereco:
        loc.append(f"Endereço: {emp.endereco}")
    if emp.bairro:
        loc.append(f"Bairro: {emp.bairro}")
    if emp.cidade:
        cidade_estado = emp.cidade
        if emp.estado:
            cidade_estado += f"/{emp.estado}"
        loc.append(f"Cidade: {cidade_estado}")
    if loc:
        sections.append(f"\n**Localização:**\n" + "\n".join(loc))
    
    if emp.descricao_localizacao:
        sections.append(f"\n**Sobre a região:** {emp.descricao_localizacao}")
    
    # Características
    if emp.tipologias:
        sections.append(f"\n**Tipologias:** {', '.join(emp.tipologias)}")
    
    if emp.metragem_minima or emp.metragem_maxima:
        if emp.metragem_minima and emp.metragem_maxima:
            sections.append(f"**Metragem:** {emp.metragem_minima}m² a {emp.metragem_maxima}m²")
        elif emp.metragem_minima:
            sections.append(f"**Metragem:** A partir de {emp.metragem_minima}m²")
    
    if emp.vagas_minima or emp.vagas_maxima:
        if emp.vagas_minima and emp.vagas_maxima:
            sections.append(f"**Vagas:** {emp.vagas_minima} a {emp.vagas_maxima}")
        elif emp.vagas_minima:
            sections.append(f"**Vagas:** {emp.vagas_minima}+")
    
    if emp.previsao_entrega:
        sections.append(f"**Previsão de entrega:** {emp.previsao_entrega}")
    
    # Valores
    if emp.preco_minimo or emp.preco_maximo:
        if emp.preco_minimo and emp.preco_maximo:
            preco = f"R$ {emp.preco_minimo:,.0f} a R$ {emp.preco_maximo:,.0f}".replace(",", ".")
        elif emp.preco_minimo:
            preco = f"A partir de R$ {emp.preco_minimo:,.0f}".replace(",", ".")
        else:
            preco = f"Até R$ {emp.preco_maximo:,.0f}".replace(",", ".")
        sections.append(f"\n**Investimento:** {preco}")
    
    # Condições
    condicoes = []
    if emp.aceita_financiamento:
        condicoes.append("Financiamento")
    if emp.aceita_fgts:
        condicoes.append("FGTS")
    if emp.aceita_permuta:
        condicoes.append("Permuta")
    if emp.aceita_consorcio:
        condicoes.append("Consórcio")
    if condicoes:
        sections.append(f"**Aceita:** {', '.join(condicoes)}")
    
    if emp.condicoes_especiais:
        sections.append(f"**Condições especiais:** {emp.condicoes_especiais}")
    
    # Lazer e diferenciais
    if emp.itens_lazer:
        sections.append(f"\n**Lazer:** {', '.join(emp.itens_lazer)}")
    
    if emp.diferenciais:
        sections.append(f"**Diferenciais:** {', '.join(emp.diferenciais)}")
    
    # Instruções para IA
    if emp.instrucoes_ia:
        sections.append(f"\n**Instruções especiais:** {emp.instrucoes_ia}")
    
    # Perguntas de qualificação
    if emp.perguntas_qualificacao:
        sections.append(f"\n**Perguntas que você DEVE fazer:**")
        for p in emp.perguntas_qualificacao:
            sections.append(f"- {p}")
    
    return "\n".join(sections)


# =============================================================================
# ENDPOINT PRINCIPAL
# =============================================================================

@router.post("/chat", response_model=SimulatorChatResponse)
async def simulator_chat(
    payload: SimulatorChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simula uma conversa com a IA usando as configurações do tenant.
    
    Não cria leads nem salva mensagens - apenas para teste.
    
    CORREÇÃO: Agora carrega a Identity completa!
    """
    
    # Buscar tenant do usuário
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # =========================================================================
    # CARREGA SETTINGS COM MIGRAÇÃO
    # =========================================================================
    raw_settings = tenant.settings or {}
    settings = migrate_settings_if_needed(raw_settings)
    ai_context = extract_ai_context(tenant, settings)
    

    logger.info(f"Simulador - Tenant: {tenant.slug}, Company: {ai_context['company_name']}")
    logger.info(f"Identity loaded: {bool(ai_context.get('identity'))}")
    
    # =========================================================================
    # DETECTA EMPREENDIMENTO
    # =========================================================================
    empreendimento = await detect_empreendimento_for_simulator(
        db=db,
        tenant_id=tenant.id,
        message=payload.message,
        history=payload.history or [],
        niche_id=ai_context["niche_id"],
    )
    
    empreendimento_context = ""
    if empreendimento:
        logger.info(f"🏢 Empreendimento ativo no simulador: {empreendimento.nome}")
        empreendimento_context = build_empreendimento_context(empreendimento)

    # =========================================================================
    # DETECTA SENTIMENTO
    # =========================================================================
    sentiment = "neutral"
    try:
        sentiment_result = await detect_sentiment(payload.message)
        sentiment = sentiment_result.get("sentiment", "neutral")
    except Exception as e:
        logger.error(f"Erro detectando sentimento: {e}")

    # =========================================================================
    # BUSCA CONFIG DO NICHO
    # =========================================================================
    niche_config = get_niche_config(ai_context["niche_id"])
    
    # =========================================================================
    # MONTA HISTÓRICO
    # =========================================================================
    messages_for_ai = []
    for msg in payload.history:
        messages_for_ai.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Adiciona mensagem atual
    messages_for_ai.append({
        "role": "user",
        "content": payload.message
    })
    
    # =========================================================================
    # CONSTRÓI PROMPT COMPLETO COM IDENTITY
    # =========================================================================
    company_name = ai_context["company_name"]
    tone = ai_context["tone"]
    identity = ai_context.get("identity", {})
    
    # Seção de identidade
    identity_section = build_identity_section(identity, company_name)
    
    # Template do nicho
    niche_prompt = ""
    if niche_config:
        niche_prompt = niche_config.prompt_template
    else:
        niche_prompt = "Atenda o cliente de forma profissional e ajude-o com suas dúvidas."
    
    # FAQ
    faq_text = ""
    faq_items = ai_context.get("faq_items", [])
    if faq_items:
        faq_text = "\n\n**Perguntas Frequentes (FAQ) - Use estas respostas quando aplicável:**\n"
        for item in faq_items:
            faq_text += f"P: {item.get('question', '')}\nR: {item.get('answer', '')}\n\n"
    
    # Escopo
    scope_text = ""
    if ai_context.get("scope_description"):
        scope_text = f"\n\n**Escopo do atendimento:**\n{ai_context['scope_description']}"
        if ai_context.get("out_of_scope_message"):
            scope_text += f"\n\nSe perguntarem sobre assuntos fora do escopo, responda:\n\"{ai_context['out_of_scope_message']}\""
    
    # Perguntas personalizadas (se não estiver na identity)
    questions_text = ""
    custom_questions = ai_context.get("custom_questions", [])
    if custom_questions and not identity.get("required_questions"):
        questions_text = "\n\n**Perguntas que você deve fazer durante a conversa:**\n"
        for q in custom_questions:
            questions_text += f"- {q}\n"
    
    # Regras personalizadas (se não estiver na identity)
    rules_text = ""
    custom_rules = ai_context.get("custom_rules", [])
    if custom_rules and not identity.get("business_rules"):
        rules_text = "\n\n**Regras importantes:**\n"
        for r in custom_rules:
            rules_text += f"- {r}\n"
    
    # Ajuste de tom baseado em sentimento
    sentiment_instruction = ""
    if sentiment == "frustrated":
        sentiment_instruction = "\n\n⚠️ O cliente parece frustrado. Seja empático, peça desculpas se necessário e tente resolver rapidamente."
    elif sentiment == "urgent":
        sentiment_instruction = "\n\n⚡ O cliente parece com urgência. Seja direto e objetivo."
    elif sentiment == "excited":
        sentiment_instruction = "\n\n🎉 O cliente parece animado/interessado. Aproveite o momento para avançar na qualificação."
    
    # =========================================================================
    # MONTA SYSTEM PROMPT FINAL
    # =========================================================================
    system_prompt = f"""Você é um assistente de atendimento da empresa **{company_name}**.

{niche_prompt}

Tom de voz: {tone}

{'=' * 50}
IDENTIDADE DA EMPRESA
{'=' * 50}

{identity_section if identity_section else 'Atenda de forma profissional e prestativa.'}

{faq_text}
{scope_text}
{questions_text}
{rules_text}
{sentiment_instruction}

{'=' * 50}
INSTRUÇÕES IMPORTANTES
{'=' * 50}

- Esta é uma simulação de teste. Responda como faria com um cliente real.
- Use emojis moderadamente se o tom for cordial ou informal.
- Seja natural e humano na conversa.
- Faça perguntas para qualificar o lead.
- NUNCA invente informações que não foram fornecidas acima.
- Se não souber algo específico (como endereço, preço), diga que vai verificar ou encaminhar para um especialista.
- Responda APENAS sobre o que a empresa oferece.
"""

    # Adiciona contexto do empreendimento se detectado
    if empreendimento_context:
        system_prompt += f"""

{empreendimento_context}

⚠️ IMPORTANTE: O cliente demonstrou interesse no empreendimento **{empreendimento.nome}**.
- USE as informações acima para responder (endereço, preço, características)
- NÃO diga "não tenho essa informação" se ela estiver acima
- Faça as perguntas de qualificação listadas
- Seja especialista neste empreendimento
"""

    logger.info(f"Prompt construído - Tamanho: {len(system_prompt)} chars")
    
    try:
        # =====================================================================
        # CHAMA A IA
        # =====================================================================
        ai_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages_for_ai
        
        result = await chat_completion(
            messages=ai_messages,
            max_tokens=500,
        )
        
        ai_response = result["content"]
        
        # Calcular delay de digitação
        typing_delay = calculate_typing_delay(len(ai_response))
        
        # Determinar hint de qualificação
        qualification_hint = analyze_qualification(payload.message, ai_response, payload.history)
        
        return SimulatorChatResponse(
            reply=ai_response,
            typing_delay=typing_delay,
            sentiment=sentiment,
            qualification_hint=qualification_hint,
        )
        
    except Exception as e:
        logger.error(f"Erro no simulador: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao gerar resposta: {str(e)}"
        )


def analyze_qualification(user_message: str, ai_response: str, history: List[SimulatorMessage]) -> str:
    """
    Analisa a conversa e dá uma dica de como o lead seria qualificado.
    """
    message_lower = user_message.lower()
    
    # Sinais de lead quente
    hot_signals = [
        "quero comprar", "quero fechar", "como faço para", "qual o valor",
        "aceita cartão", "posso pagar", "tem disponível", "quando posso",
        "vou querer", "pode reservar", "fecha negócio", "quero agendar",
        "visitar", "conhecer pessoalmente", "quero alugar", "quero ver",
        "posso ir hoje", "agenda pra mim"
    ]
    
    # Sinais de lead morno
    warm_signals = [
        "quanto custa", "qual o preço", "tem financiamento", "como funciona",
        "quais as opções", "me interessei", "gostaria de saber", "pode me explicar",
        "estou pesquisando", "estou procurando", "qual o endereço", "onde fica",
        "horário de funcionamento", "vocês trabalham com"
    ]
    
    # Verificar sinais
    for signal in hot_signals:
        if signal in message_lower:
            return "🔥 Lead QUENTE - Cliente demonstra intenção de compra/ação"
    
    for signal in warm_signals:
        if signal in message_lower:
            return "🟡 Lead MORNO - Cliente demonstra interesse"
    
    # Verificar histórico
    total_messages = len(history) + 1
    if total_messages >= 5:
        return "🟡 Lead MORNO - Conversa em andamento"
    
    return "🔵 Lead FRIO - Início da conversa"


# =============================================================================
# SUGESTÕES DE TESTE
# =============================================================================

@router.get("/suggestions")
async def get_simulator_suggestions():
    """
    Retorna sugestões de mensagens para testar o simulador.
    """
    return {
        "suggestions": [
            {
                "category": "Primeira mensagem",
                "messages": [
                    "Oi, vi o anúncio de vocês",
                    "Olá, gostaria de informações",
                    "Boa tarde! Vocês trabalham com o quê?",
                ]
            },
            {
                "category": "Informações básicas",
                "messages": [
                    "Qual o endereço de vocês?",
                    "Qual o horário de funcionamento?",
                    "Qual o telefone para contato?",
                ]
            },
            {
                "category": "Interesse",
                "messages": [
                    "Quanto custa?",
                    "Quais as formas de pagamento?",
                    "Vocês fazem financiamento?",
                    "Tem disponibilidade para essa semana?",
                ]
            },
            {
                "category": "Objeções",
                "messages": [
                    "Tá muito caro",
                    "Vou pensar e depois te falo",
                    "Preciso falar com meu marido/esposa primeiro",
                    "Achei o concorrente de vocês mais barato",
                ]
            },
            {
                "category": "Lead Quente",
                "messages": [
                    "Quero fechar! Como faço?",
                    "Aceita cartão de crédito?",
                    "Posso visitar hoje?",
                    "Pode reservar pra mim?",
                ]
            },
            {
                "category": "Fora do escopo",
                "messages": [
                    "Qual a capital da França?",
                    "Me ajuda com meu dever de casa",
                    "Conta uma piada",
                    "Vocês fazem limpeza de sofá?",
                ]
            },
        ]
    }


# =============================================================================
# DEBUG ENDPOINT
# =============================================================================

@router.get("/debug-settings")
async def debug_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de debug para verificar se as configurações estão sendo carregadas.
    """
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    raw_settings = tenant.settings or {}
    settings = migrate_settings_if_needed(raw_settings)
    ai_context = extract_ai_context(tenant, settings)
    
    identity = ai_context.get("identity", {})
    
    return {
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "company_name": ai_context.get("company_name"),
        "niche": ai_context.get("niche_id"),
        "tone": ai_context.get("tone"),
        "has_identity": bool(identity),
        "identity_fields": {
            "description": bool(identity.get("description")),
            "products_services": len(identity.get("products_services", [])),
            "not_offered": len(identity.get("not_offered", [])),
            "additional_context": bool(identity.get("additional_context")),
            "business_rules": len(identity.get("business_rules", [])),
            "differentials": len(identity.get("differentials", [])),
            "personality_traits": len(identity.get("tone_style", {}).get("personality_traits", [])),
        },
        "faq_count": len(ai_context.get("faq_items", [])),
        "scope_description": bool(ai_context.get("scope_description")),
    }