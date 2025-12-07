"""
TEMPLATES DE PROMPTS POR NICHO (VERSÃO CORRIGIDA)
==================================================

IA VENDEDORA INTELIGENTE COM IDENTIDADE EMPRESARIAL
- Personalização por identidade da empresa
- Restrição rígida de escopo
- Mensagens proativas
- Contorno de objeções
- Condução para fechamento

CORREÇÕES:
- Template de escopo agora inclui not_offered_section
- Validação de campos vazios
- Controle de tamanho do prompt
- Melhor formatação
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Limite de caracteres para o prompt (evita estourar contexto)
MAX_PROMPT_LENGTH = 12000


@dataclass
class NicheConfig:
    """Configuração de um nicho."""
    id: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]
    qualification_rules: dict
    prompt_template: str


# ============================================
# PROMPT BASE - IA VENDEDORA COM IDENTIDADE
# ============================================

BASE_SYSTEM_PROMPT = """Você é a assistente virtual da {company_name}.

{identity_section}

{scope_restriction}

🎯 SEU OBJETIVO:
Atender e VENDER. Você é uma vendedora experiente que:
- Entende as necessidades do cliente
- Usa informações da conversa para personalizar a abordagem
- Sugere opções relevantes baseadas no perfil
- Cria senso de urgência quando apropriado
- Contorna objeções de forma natural

📋 REGRAS DE ATENDIMENTO:
- Seja {tone} e profissional
- Faça uma pergunta por vez
- LEMBRE-SE de tudo que o cliente disse e USE essas informações
- Seja proativa: sugira opções, não espere o cliente pedir
- Quando tiver informações suficientes, conduza para o fechamento

{niche_prompt}

📊 DADOS A COLETAR:
{fields_to_collect}

🧠 INTELIGÊNCIA DE VENDAS - USE SEMPRE:

1. USE O CONTEXTO DO CLIENTE:
   - Se mencionou família (filhos, casado), adapte sugestões para o perfil familiar
   - Se mencionou trabalho/região, sugira opções convenientes para a rotina
   - Se mencionou orçamento, respeite a faixa e ofereça o melhor custo-benefício
   - Se mencionou urgência, acelere o processo e priorize disponibilidade

2. SEJA PROATIVA:
   - Ofereça informações relevantes antes de ser perguntado
   - Sugira próximos passos claros ("Posso verificar disponibilidade para você?")
   - Antecipe dúvidas comuns do seu nicho

3. CONTORNE OBJEÇÕES COM INTELIGÊNCIA:
   - "TÁ CARO" → Destaque valor, ofereça parcelamento, compare custo-benefício
   - "VOU PENSAR" → Pergunte o que precisa analisar, ofereça mais informações
   - "DEPOIS EU VEJO" → Entenda o motivo, crie urgência sutil se real

4. DETECTE SINAIS DE COMPRA E ACELERE:
   - Pergunta sobre pagamento → Quer comprar!
   - Pergunta sobre disponibilidade → Está pronto!
   - Pergunta sobre prazo → Urgência real!

{custom_rules}

{faq_section}

⚠️ REGRAS CRÍTICAS:
- NUNCA invente informações sobre produtos, preços ou disponibilidade
- Se não souber algo específico, diga que vai verificar com a equipe
- Use as informações do cliente de forma NATURAL, não robótica
"""


# ============================================
# SEÇÃO DE IDENTIDADE EMPRESARIAL
# ============================================

IDENTITY_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏢 IDENTIDADE DA EMPRESA - SIGA RIGOROSAMENTE
═══════════════════════════════════════════════════════════════

QUEM SOMOS:
{description}
{products_section}
{differentials_section}
{target_audience_section}
{communication_style_section}
{business_rules_section}
"""


# ============================================
# SEÇÃO DE RESTRIÇÃO DE ESCOPO (CRÍTICA!)
# ============================================

SCOPE_RESTRICTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🚫 RESTRIÇÃO ABSOLUTA DE ESCOPO - REGRA INVIOLÁVEL
═══════════════════════════════════════════════════════════════

A {company_name} trabalha EXCLUSIVAMENTE com:
{products_services_list}

{not_offered_section}

⛔ REGRA OBRIGATÓRIA - NUNCA ESQUEÇA:
Se o cliente perguntar sobre QUALQUER COISA fora da lista acima:
1. NÃO invente que oferecemos
2. NÃO adapte a pergunta  
3. NÃO tente ser útil com isso
4. Responda: "{out_of_scope_message}"
5. Redirecione para nossos serviços reais

🚨 EXEMPLO:
- Cliente: "Vocês fazem limpeza de sofá?"
- ❌ ERRADO: "Sim, fazemos..." (NUNCA INVENTE!)
- ❌ ERRADO: "Não fazemos, mas posso recomendar..."
- ✅ CERTO: "{out_of_scope_message}"
"""


# ============================================
# TEMPLATES POR NICHO
# ============================================

NICHE_TEMPLATES: dict[str, NicheConfig] = {
    
    "fashion": NicheConfig(
        id="fashion",
        name="Moda / Roupas",
        description="Lojas de roupas, aluguel de trajes, moda festa",
        required_fields=["name", "phone", "event_type", "event_date"],
        optional_fields=["size", "color_preference", "budget", "style"],
        qualification_rules={
            "hot": ["evento próximo", "quer reservar", "preciso pra semana que vem", "qual disponibilidade", "como faço pra alugar"],
            "warm": ["pesquisando", "evento daqui 2 meses", "vendo opções", "comparando"],
            "cold": ["só olhando", "sem data definida", "só curiosidade"]
        },
        prompt_template="""
👗 CONTEXTO - MODA E EVENTOS:

PERGUNTAS PARA QUALIFICAR:
1. Qual o tipo de evento? (casamento, formatura, festa corporativa)
2. Qual a data do evento?
3. Está buscando aluguel ou compra?
4. Qual seu tamanho/manequim?
5. Tem preferência de cor ou estilo?

🔥 SINAIS DE COMPRA:
- Perguntou disponibilidade de tamanho
- Perguntou sobre reserva/locação
- Evento com data próxima
- Quer agendar prova
"""
    ),

    "events": NicheConfig(
        id="events",
        name="Eventos / Aluguel",
        description="Aluguel para eventos, festas, casamentos",
        required_fields=["name", "phone", "event_type", "event_date"],
        optional_fields=["guest_count", "location", "budget", "style"],
        qualification_rules={
            "hot": ["evento próximo", "quer reservar", "data definida", "como faço pra alugar"],
            "warm": ["pesquisando", "planejando", "vendo opções"],
            "cold": ["só orçamento", "sem data", "ano que vem"]
        },
        prompt_template="""
🎉 CONTEXTO - EVENTOS:

PERGUNTAS PARA QUALIFICAR:
1. Qual o tipo de evento?
2. Qual a data?
3. Quantos convidados?
4. Qual a localização do evento?
"""
    ),
    
    "real_estate": NicheConfig(
        id="real_estate",
        name="Imobiliária",
        description="Compra, venda e aluguel de imóveis",
        required_fields=["name", "phone", "interest_type", "city"],
        optional_fields=["property_type", "neighborhood", "bedrooms", "budget", "financing"],
        qualification_rules={
            "hot": ["quer comprar agora", "urgente", "já tem entrada", "pré-aprovado", "quer visitar"],
            "warm": ["pesquisando", "próximos 6 meses", "ainda decidindo"],
            "cold": ["só curiosidade", "sem previsão", "apenas olhando"]
        },
        prompt_template="""
🏠 CONTEXTO - IMOBILIÁRIA:

PERGUNTAS PARA QUALIFICAR:
1. Interesse: comprar, alugar ou vender?
2. Tipo de imóvel? (apartamento, casa, comercial)
3. Região/bairro de interesse?
4. Quantos quartos/tamanho?
5. Faixa de valor/orçamento?
6. Vai financiar ou à vista?
"""
    ),
    
    "healthcare": NicheConfig(
        id="healthcare",
        name="Clínica / Saúde",
        description="Clínicas médicas, odontológicas, estéticas",
        required_fields=["name", "phone", "specialty", "urgency"],
        optional_fields=["insurance", "preferred_date", "symptoms"],
        qualification_rules={
            "hot": ["urgente", "dor", "emergência", "hoje", "amanhã", "quer agendar agora"],
            "warm": ["essa semana", "consulta de rotina", "retorno"],
            "cold": ["só informação", "só preço", "sem previsão"]
        },
        prompt_template="""
🏥 CONTEXTO - CLÍNICA/SAÚDE:

PERGUNTAS PARA QUALIFICAR:
1. Qual especialidade ou procedimento?
2. Primeira consulta ou retorno?
3. Tem convênio? Qual?
4. Urgência? Está com algum sintoma?

⚠️ IMPORTANTE - NUNCA:
- Dê diagnósticos ou sugira o que pode ser
- Recomende medicamentos
"""
    ),
    
    "beauty": NicheConfig(
        id="beauty",
        name="Beleza / Estética",
        description="Salões, clínicas de estética, spas",
        required_fields=["name", "phone", "service_interest"],
        optional_fields=["preferred_date", "professional_preference"],
        qualification_rules={
            "hot": ["quer agendar", "essa semana", "disponibilidade"],
            "warm": ["pesquisando", "vendo preços"],
            "cold": ["só informação", "sem previsão"]
        },
        prompt_template="""
💇 CONTEXTO - BELEZA/ESTÉTICA:

PERGUNTAS PARA QUALIFICAR:
1. Qual serviço você procura?
2. Tem preferência de profissional?
3. Qual data/horário seria ideal?
"""
    ),
    
    "services": NicheConfig(
        id="services",
        name="Serviços Gerais",
        description="Prestadores de serviço diversos",
        required_fields=["name", "phone", "service_type", "city"],
        optional_fields=["description", "urgency", "budget"],
        qualification_rules={
            "hot": ["urgente", "preciso pra hoje", "orçamento aprovado", "quando podem fazer"],
            "warm": ["essa semana", "pegando orçamentos", "comparando"],
            "cold": ["só cotação", "sem previsão", "só pra ter ideia"]
        },
        prompt_template="""
🔧 CONTEXTO - SERVIÇOS:

PERGUNTAS PARA QUALIFICAR:
1. Qual serviço você precisa?
2. Pode descrever o que precisa ser feito?
3. Qual a localização? (cidade/bairro)
4. Qual a urgência?
"""
    ),
    
    "education": NicheConfig(
        id="education",
        name="Educação / Cursos",
        description="Escolas, cursos, treinamentos",
        required_fields=["name", "phone", "course_interest"],
        optional_fields=["current_level", "availability", "payment_preference"],
        qualification_rules={
            "hot": ["quero me matricular", "começar agora", "como faço pra matricular"],
            "warm": ["comparando escolas", "esse semestre", "pesquisando"],
            "cold": ["só informação", "ano que vem", "só preço"]
        },
        prompt_template="""
📚 CONTEXTO - EDUCAÇÃO:

PERGUNTAS PARA QUALIFICAR:
1. Qual curso ou área de interesse?
2. É para você ou outra pessoa?
3. Qual seu nível atual de conhecimento?
4. Preferência de horário?
"""
    ),
    
    "food": NicheConfig(
        id="food",
        name="Alimentação",
        description="Restaurantes, delivery, buffet",
        required_fields=["name", "phone"],
        optional_fields=["order_type", "delivery_address", "event_date"],
        qualification_rules={
            "hot": ["quero pedir", "fazer pedido", "encomenda pra hoje"],
            "warm": ["ver cardápio", "preços", "opções"],
            "cold": ["só olhando", "depois"]
        },
        prompt_template="""
🍽️ CONTEXTO - ALIMENTAÇÃO:

PERGUNTAS PARA QUALIFICAR:
1. Gostaria de fazer um pedido?
2. É para entrega ou retirada?
3. Qual o endereço de entrega?
"""
    ),
}


def get_niche_config(niche_id: str) -> Optional[NicheConfig]:
    """Retorna configuração do nicho ou None se não existir."""
    return NICHE_TEMPLATES.get(niche_id)


def get_available_niches() -> list[dict]:
    """Lista todos os nichos disponíveis."""
    return [
        {"id": n.id, "name": n.name, "description": n.description}
        for n in NICHE_TEMPLATES.values()
    ]


def _truncate_list(items: list, max_items: int = 10) -> list:
    """Trunca lista para evitar prompts muito longos."""
    if len(items) <= max_items:
        return items
    return items[:max_items]


def _safe_join(items: list, separator: str = ", ", default: str = "") -> str:
    """Junta lista de forma segura."""
    if not items:
        return default
    return separator.join(str(item) for item in items if item)


def build_identity_section(identity: dict, company_name: str) -> str:
    """
    Constrói a seção de identidade empresarial para o prompt.
    
    Args:
        identity: Dicionário com dados de identidade da empresa
        company_name: Nome da empresa
    
    Returns:
        String formatada com a seção de identidade
    """
    if not identity:
        return ""
    
    # Descrição
    description = identity.get("description", "").strip()
    if not description:
        description = f"Somos a {company_name}, uma empresa focada em oferecer as melhores soluções para nossos clientes."
    
    # Produtos/Serviços
    products_section = ""
    products = identity.get("products_services", [])
    if products:
        products = _truncate_list(products, 15)
        products_section = "\nO QUE OFERECEMOS:\n" + "\n".join(f"  • {p}" for p in products)
    
    # Diferenciais
    differentials_section = ""
    differentials = identity.get("differentials", [])
    if differentials:
        differentials = _truncate_list(differentials, 8)
        differentials_section = "\nNOSSOS DIFERENCIAIS:\n" + "\n".join(f"  ✓ {d}" for d in differentials)
    
    # Público-alvo
    target_audience_section = ""
    target = identity.get("target_audience", {})
    if target and any(target.values()):
        parts = []
        if target.get("description"):
            parts.append(f"Público: {target['description']}")
        if target.get("segments"):
            segments = _truncate_list(target['segments'], 5)
            parts.append(f"Segmentos: {_safe_join(segments)}")
        if target.get("pain_points"):
            pains = _truncate_list(target['pain_points'], 5)
            parts.append(f"Dores que resolvemos: {_safe_join(pains)}")
        if parts:
            target_audience_section = "\nNOSSO PÚBLICO:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Estilo de comunicação
    communication_style_section = ""
    tone_style = identity.get("tone_style", {})
    if tone_style and any(tone_style.values()):
        parts = []
        if tone_style.get("personality_traits"):
            traits = _truncate_list(tone_style['personality_traits'], 4)
            parts.append(f"Personalidade: {_safe_join(traits)}")
        if tone_style.get("communication_style"):
            parts.append(f"Estilo: {tone_style['communication_style']}")
        if tone_style.get("use_phrases"):
            phrases = _truncate_list(tone_style['use_phrases'], 5)
            parts.append(f"Use expressões como: {_safe_join(phrases)}")
        if tone_style.get("avoid_phrases"):
            avoid = _truncate_list(tone_style['avoid_phrases'], 5)
            parts.append(f"EVITE: {_safe_join(avoid)}")
        if parts:
            communication_style_section = "\nCOMO COMUNICAR:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Regras de negócio
    business_rules_section = ""
    rules = identity.get("business_rules", [])
    if rules:
        rules = _truncate_list(rules, 10)
        business_rules_section = "\n⚠️ REGRAS OBRIGATÓRIAS:\n" + "\n".join(f"  ❗ {r}" for r in rules)
    
    result = IDENTITY_SECTION_TEMPLATE.format(
        description=description,
        products_section=products_section,
        differentials_section=differentials_section,
        target_audience_section=target_audience_section,
        communication_style_section=communication_style_section,
        business_rules_section=business_rules_section,
    )
    
    # Remove linhas vazias extras
    lines = [line for line in result.split('\n') if line.strip() or line == '']
    return '\n'.join(lines)


def build_scope_restriction(
    identity: dict,
    company_name: str,
    scope_config: dict = None,
) -> str:
    """
    Constrói a seção de restrição de escopo.
    CRÍTICA para evitar IA inventando serviços.
    
    Args:
        identity: Dicionário com dados de identidade
        company_name: Nome da empresa
        scope_config: Configuração de escopo do tenant
    
    Returns:
        String formatada com restrição de escopo
    """
    
    # Lista de produtos/serviços
    products = identity.get("products_services", []) if identity else []
    if products:
        products = _truncate_list(products, 15)
        products_list = "\n".join(f"  ✅ {p}" for p in products)
    else:
        # Se não tem produtos cadastrados, usa descrição genérica
        products_list = "  ✅ (Configure os produtos/serviços no painel para melhor precisão)"
    
    # O que NÃO oferecemos - CORREÇÃO: Agora é incluído no template
    not_offered = identity.get("not_offered", []) if identity else []
    not_offered_section = ""
    if not_offered:
        not_offered = _truncate_list(not_offered, 10)
        not_offered_section = "\n❌ NÃO TRABALHAMOS COM (responda que não oferecemos):\n" + "\n".join(f"  ✖ {n}" for n in not_offered)
    
    # Mensagem padrão fora do escopo
    default_message = f"Não trabalhamos com isso. A {company_name} é especializada em outros serviços. Posso te ajudar com algo dentro da nossa área?"
    out_of_scope_message = default_message
    
    if scope_config and scope_config.get("out_of_scope_message"):
        out_of_scope_message = scope_config["out_of_scope_message"]
    
    return SCOPE_RESTRICTION_TEMPLATE.format(
        company_name=company_name,
        products_services_list=products_list,
        not_offered_section=not_offered_section,
        out_of_scope_message=out_of_scope_message,
    )


def build_system_prompt(
    niche_id: str,
    company_name: str,
    tone: str = "cordial",
    custom_questions: list[str] = None,
    custom_rules: list[str] = None,
    custom_prompt: str = None,
    faq_items: list[dict] = None,
    scope_description: str = None,
    lead_context: dict = None,
    # NOVOS PARÂMETROS - IDENTIDADE EMPRESARIAL
    identity: dict = None,
    scope_config: dict = None,
) -> str:
    """
    Monta o prompt completo para um tenant COM IDENTIDADE EMPRESARIAL.
    
    Args:
        niche_id: ID do nicho (real_estate, healthcare, etc)
        company_name: Nome da empresa
        tone: Tom de voz (formal, informal, cordial)
        custom_questions: Perguntas extras do tenant
        custom_rules: Regras extras do tenant
        custom_prompt: Prompt livre (só Pro) - substitui tudo
        faq_items: Lista de FAQs [{"question": "...", "answer": "..."}]
        scope_description: Descrição do escopo da IA (legado)
        lead_context: Contexto extraído do lead para personalização
        identity: Dicionário de identidade empresarial (NOVO!)
        scope_config: Configuração de escopo (NOVO!)
    
    Returns:
        Prompt completo formatado
    """
    
    # Se tem prompt customizado (Pro), usa ele
    if custom_prompt and custom_prompt.strip():
        logger.info(f"Usando prompt customizado para {company_name}")
        return custom_prompt
    
    # Busca template do nicho
    niche = get_niche_config(niche_id)
    if not niche:
        logger.warning(f"Nicho '{niche_id}' não encontrado, usando 'services'")
        niche = NICHE_TEMPLATES.get("services")
    
    # ==========================================
    # SEÇÃO DE IDENTIDADE
    # ==========================================
    identity_section = ""
    if identity and any(identity.values()):
        identity_section = build_identity_section(identity, company_name)
        logger.debug(f"Identity section gerada: {len(identity_section)} chars")
    
    # ==========================================
    # SEÇÃO DE RESTRIÇÃO DE ESCOPO
    # ==========================================
    scope_restriction = ""
    if identity and identity.get("products_services"):
        scope_restriction = build_scope_restriction(identity, company_name, scope_config)
    elif scope_description:
        # Fallback para formato legado
        scope_restriction = f"""
🚫 ESCOPO DO ATENDIMENTO:
Você só deve responder sobre: {scope_description}

Se perguntarem sobre algo fora deste escopo, responda educadamente que não tem informações sobre isso.
"""
    
    # Monta lista de campos a coletar
    fields = []
    
    # Campos obrigatórios da identidade
    if identity and identity.get("required_info"):
        fields.append("INFORMAÇÕES OBRIGATÓRIAS:")
        for field in _truncate_list(identity["required_info"], 8):
            fields.append(f"  • {field} (OBRIGATÓRIO)")
    
    # Perguntas obrigatórias da identidade
    if identity and identity.get("required_questions"):
        fields.append("\nPERGUNTAS OBRIGATÓRIAS:")
        for q in _truncate_list(identity["required_questions"], 8):
            fields.append(f"  • {q}")
    
    # Campos do nicho
    if niche:
        fields.append("\nCAMPOS DO NICHO:")
        for field in niche.required_fields[:6]:
            fields.append(f"  • {field} (obrigatório)")
        for field in niche.optional_fields[:4]:
            fields.append(f"  • {field} (se possível)")
    
    # Perguntas customizadas (legado)
    if custom_questions:
        fields.append("\nPERGUNTAS EXTRAS:")
        for q in _truncate_list(custom_questions, 5):
            fields.append(f"  • {q}")
    
    # Monta regras customizadas
    rules_text = ""
    
    # Regras customizadas (legado)
    if custom_rules:
        rules_text += "\n📌 REGRAS ADICIONAIS:\n"
        for rule in _truncate_list(custom_rules, 8):
            rules_text += f"  • {rule}\n"
    
    # Contexto do lead (se disponível)
    if lead_context and any(lead_context.values()):
        rules_text += "\n📋 CONTEXTO DO CLIENTE (use para personalizar):\n"
        
        context_items = [
            ("name", "Nome"),
            ("family_situation", "Situação familiar"),
            ("work_info", "Trabalho"),
            ("budget_range", "Orçamento"),
            ("urgency_level", "Urgência"),
            ("preferences", "Preferências"),
            ("pain_points", "Dores/Problemas"),
            ("objections", "⚠️ OBJEÇÕES (CONTORNE!)"),
            ("buying_signals", "🔥 SINAIS DE COMPRA (ACELERE!)"),
        ]
        
        for key, label in context_items:
            value = lead_context.get(key)
            if value:
                if isinstance(value, list):
                    value = _safe_join(value)
                rules_text += f"  • {label}: {value}\n"
    
    # Monta seção de FAQ
    faq_section = ""
    if faq_items:
        faq_items = _truncate_list(faq_items, 10)
        faq_section = "\n📚 PERGUNTAS FREQUENTES (FAQ):\n"
        for item in faq_items:
            question = item.get("question", "")
            answer = item.get("answer", "")
            if question and answer:
                # Trunca respostas muito longas
                if len(answer) > 300:
                    answer = answer[:297] + "..."
                faq_section += f"\nP: {question}\nR: {answer}\n"
    
    # Determina tom de voz
    tone_display = tone
    if identity and identity.get("tone_style", {}).get("tone"):
        tone_display = identity["tone_style"]["tone"]
    
    # Monta prompt final
    final_prompt = BASE_SYSTEM_PROMPT.format(
        company_name=company_name,
        identity_section=identity_section,
        scope_restriction=scope_restriction,
        tone=tone_display,
        niche_prompt=niche.prompt_template if niche else "",
        fields_to_collect="\n".join(fields),
        custom_rules=rules_text,
        faq_section=faq_section,
    )
    
    # Verifica tamanho e trunca se necessário
    if len(final_prompt) > MAX_PROMPT_LENGTH:
        logger.warning(f"Prompt muito longo ({len(final_prompt)} chars), truncando...")
        # Remove seções menos críticas primeiro
        final_prompt = final_prompt[:MAX_PROMPT_LENGTH]
        # Garante que termina em um ponto lógico
        last_newline = final_prompt.rfind('\n')
        if last_newline > MAX_PROMPT_LENGTH - 500:
            final_prompt = final_prompt[:last_newline]
    
    logger.info(f"Prompt gerado para {company_name}: {len(final_prompt)} chars, identity={'sim' if identity else 'não'}")
    
    return final_prompt


def get_identity_completeness(identity: dict) -> dict:
    """
    Calcula o percentual de completude da identidade.
    
    Returns:
        Dict com score (0-100) e campos faltantes
    """
    if not identity:
        return {"score": 0, "missing": ["identity não configurada"], "status": "não configurado"}
    
    checks = {
        "description": bool(identity.get("description")),
        "products_services": bool(identity.get("products_services")),
        "not_offered": bool(identity.get("not_offered")),
        "tone": bool(identity.get("tone_style", {}).get("tone")),
        "business_rules": bool(identity.get("business_rules")),
        "differentials": bool(identity.get("differentials")),
    }
    
    completed = sum(checks.values())
    total = len(checks)
    score = int((completed / total) * 100)
    
    missing = [field for field, done in checks.items() if not done]
    
    if score >= 80:
        status = "completo"
    elif score >= 50:
        status = "parcial"
    else:
        status = "básico"
    
    return {
        "score": score,
        "missing": missing,
        "status": status,
        "completed": completed,
        "total": total,
    }