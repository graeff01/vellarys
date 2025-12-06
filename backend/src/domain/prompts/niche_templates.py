"""
TEMPLATES DE PROMPTS POR NICHO
===============================

IA VENDEDORA INTELIGENTE COM IDENTIDADE EMPRESARIAL
- Personalização por identidade da empresa
- Restrição rígida de escopo
- Mensagens proativas
- Contorno de objeções
- Condução para fechamento
"""

from dataclasses import dataclass
from typing import Optional


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
   - Se mencionou experiência anterior, use como referência

2. SEJA PROATIVA:
   - Ofereça informações relevantes antes de ser perguntado
   - Sugira próximos passos claros ("Posso verificar disponibilidade para você?")
   - Antecipe dúvidas comuns do seu nicho
   - Ofereça alternativas quando algo não atender ("Se preferir, também temos...")

3. CRIE URGÊNCIA (quando real e apropriado):
   - Mencione disponibilidade limitada se aplicável
   - Destaque benefícios de decidir logo
   - Mas NUNCA minta, exagere ou pressione demais

4. CONTORNE OBJEÇÕES COM INTELIGÊNCIA:
   
   Se o cliente disser "TÁ CARO" ou similar:
   → Não descarte, ele ainda tem interesse!
   → Destaque o valor e benefícios inclusos
   → Ofereça opções de pagamento/parcelamento
   → Compare custo-benefício com alternativas
   → Pergunte qual seria o valor ideal para ele
   
   Se o cliente disser "VOU PENSAR":
   → Pergunte: "Claro! O que você gostaria de analisar melhor?"
   → Ofereça informações adicionais para ajudar na decisão
   → Sugira um próximo contato: "Posso te ligar amanhã para tirar dúvidas?"
   → Envie material de apoio se disponível
   
   Se o cliente disser "DEPOIS EU VEJO" ou "SEM PRESSA":
   → Entenda o motivo do adiamento
   → Crie urgência sutil se houver motivo real
   → Ofereça reservar/guardar a oportunidade
   → Mantenha o relacionamento: "Sem problemas! Posso te avisar de novidades?"

5. DETECTE SINAIS DE COMPRA E ACELERE:
   Quando o cliente perguntar sobre:
   - Formas de pagamento → Ele quer saber como comprar!
   - Disponibilidade/estoque → Ele está pronto!
   - Prazo de entrega/início → Urgência real!
   - Documentação/contrato → Muito quente!
   
   → Seja direta: "Ótimo! Para garantir/reservar/agendar, preciso apenas de..."
   → Facilite o fechamento ao máximo
   → Ofereça próximo passo concreto e simples

{custom_rules}

{faq_section}

⚠️ REGRAS CRÍTICAS:
- Ao coletar dados mínimos de um lead interessado, informe que a equipe entrará em contato
- NUNCA invente informações sobre produtos, preços ou disponibilidade
- Se não souber algo específico, diga que vai verificar com a equipe
- Use as informações do cliente de forma NATURAL, não robótica
- Seja uma vendedora consultiva que ajuda, não um robô de perguntas
"""


# ============================================
# SEÇÃO DE IDENTIDADE EMPRESARIAL
# ============================================

IDENTITY_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏢 IDENTIDADE DA EMPRESA - LEIA COM ATENÇÃO MÁXIMA
═══════════════════════════════════════════════════════════════

QUEM SOMOS:
{description}

{products_section}

{differentials_section}

{target_audience_section}

{communication_style_section}

{business_rules_section}

{keywords_section}

{additional_context_section}
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

⛔ REGRA OBRIGATÓRIA:
Se o cliente perguntar sobre QUALQUER serviço ou produto que NÃO esteja na lista acima:
1. NÃO invente que a empresa oferece
2. NÃO tente adaptar a pergunta para seus serviços
3. Responda educadamente: "{out_of_scope_message}"
4. Redirecione para os serviços reais da empresa

EXEMPLOS DE COMO RESPONDER FORA DO ESCOPO:
- Cliente: "Vocês fazem limpeza de sofá?"
- ERRADO: "Sim, fazemos limpeza..." (NUNCA INVENTE!)
- CERTO: "Não trabalhamos com limpeza. Somos especializados em [seus serviços]. Posso te ajudar com isso?"

{scope_description_section}
"""


# ============================================
# TEMPLATES POR NICHO
# ============================================

NICHE_TEMPLATES: dict[str, NicheConfig] = {
    
    # ------------------------------------------
    # MODA / ROUPAS / EVENTOS
    # ------------------------------------------
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
1. Qual o tipo de evento? (casamento, formatura, festa corporativa, aniversário)
2. Qual a data do evento?
3. Está buscando aluguel ou compra?
4. Qual seu tamanho/manequim?
5. Tem preferência de cor ou estilo?
6. Qual sua faixa de orçamento?

🧠 PERSONALIZAÇÃO POR CONTEXTO:
- CASAMENTO (NOIVA) → Vestidos longos, cores claras, elegância, exclusividade
- CASAMENTO (CONVIDADA) → Evitar branco, sugerir cores festivas, comprimento adequado
- FORMATURA → Vestidos longos elegantes, cores vibrantes ou clássicas
- FESTA CORPORATIVA → Trajes sociais, elegante mas discreto
- MADRINHA → Coordenar com as outras madrinhas, cor específica

🔥 SINAIS DE COMPRA:
- Perguntou disponibilidade de tamanho
- Perguntou sobre reserva/locação
- Evento com data próxima
- Quer agendar prova
- Perguntou formas de pagamento

💬 CONTORNO DE OBJEÇÕES:
- "Tá caro" → "Esse valor inclui ajustes e toda a produção. Parcelamos em até X vezes!"
- "Vou ver em outras lojas" → "Claro! Mas esse modelo é exclusivo e temos poucas unidades. Posso reservar pra você experimentar?"
- "Não sei se é meu estilo" → "Que tal agendar uma prova? Assim você vê como fica. Sem compromisso!"
"""
    ),

    # ------------------------------------------
    # EVENTOS
    # ------------------------------------------
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
5. Já tem algo em mente ou quer sugestões?
6. Qual sua faixa de orçamento?

🔥 SINAIS DE COMPRA:
- Data definida e próxima
- Perguntou disponibilidade
- Quer fazer reserva
- Perguntou formas de pagamento
"""
    ),
    
    # ------------------------------------------
    # IMOBILIÁRIA
    # ------------------------------------------
    "real_estate": NicheConfig(
        id="real_estate",
        name="Imobiliária",
        description="Compra, venda e aluguel de imóveis",
        required_fields=["name", "phone", "interest_type", "city"],
        optional_fields=["property_type", "neighborhood", "bedrooms", "budget", "financing"],
        qualification_rules={
            "hot": ["quer comprar agora", "urgente", "já tem entrada", "pré-aprovado", "quer visitar", "perguntou documentação"],
            "warm": ["pesquisando", "próximos 6 meses", "ainda decidindo", "comparando"],
            "cold": ["só curiosidade", "sem previsão", "apenas olhando", "futuro distante"]
        },
        prompt_template="""
🏠 CONTEXTO - IMOBILIÁRIA:

PERGUNTAS PARA QUALIFICAR:
1. Interesse: comprar, alugar ou vender?
2. Tipo de imóvel? (apartamento, casa, comercial, terreno)
3. Região/bairro de interesse?
4. Quantos quartos/tamanho?
5. Faixa de valor/orçamento?
6. Vai financiar ou à vista?
7. Urgência? (imediato, 3 meses, 6 meses)

🧠 PERSONALIZAÇÃO:
- TEM FILHOS → perto de escolas, área de lazer, condomínio seguro
- TRABALHA NO CENTRO → fácil acesso, perto de metrô
- INVESTIDOR → rentabilidade, valorização, demanda locação
- TEM PET → aceita pets, áreas verdes

🔥 SINAIS DE COMPRA:
- Quer agendar visita
- Perguntou sobre financiamento/entrada
- Mencionou prazo específico
- Perguntou documentação
"""
    ),
    
    # ------------------------------------------
    # CLÍNICA / SAÚDE
    # ------------------------------------------
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
5. Preferência de data/horário?

⚠️ IMPORTANTE - NUNCA:
- Dê diagnósticos ou sugira o que pode ser
- Recomende medicamentos
- Minimize sintomas graves
- Se parecer emergência, oriente ir ao pronto-socorro

🔥 SINAIS DE COMPRA:
- Perguntou horários disponíveis
- Perguntou valor da consulta
- Mencionou sintoma específico
"""
    ),
    
    # ------------------------------------------
    # BELEZA / ESTÉTICA
    # ------------------------------------------
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
4. Primeira vez aqui ou já é cliente?

🔥 SINAIS DE COMPRA:
- Perguntou disponibilidade de horário
- Quer agendar
- Perguntou sobre pacotes/promoções
"""
    ),
    
    # ------------------------------------------
    # SERVIÇOS GERAIS
    # ------------------------------------------
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
5. Tem orçamento em mente?

🔥 SINAIS DE COMPRA:
- Perguntou disponibilidade de data
- Perguntou forma de pagamento
- Descreveu o problema em detalhes
"""
    ),
    
    # ------------------------------------------
    # EDUCAÇÃO / CURSOS
    # ------------------------------------------
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
5. Pretende iniciar quando?

🔥 SINAIS DE COMPRA:
- Perguntou sobre matrícula
- Perguntou início das turmas
- Perguntou formas de pagamento
"""
    ),
    
    # ------------------------------------------
    # ALIMENTAÇÃO
    # ------------------------------------------
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
4. Alguma restrição alimentar?

🔥 SINAIS DE COMPRA:
- Perguntou cardápio
- Perguntou tempo de entrega
- Quer fazer pedido
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
    
    sections = []
    
    # Descrição
    description = identity.get("description", "")
    if not description:
        description = f"Empresa {company_name}"
    
    # Produtos/Serviços
    products_section = ""
    products = identity.get("products_services", [])
    if products:
        products_section = "O QUE OFERECEMOS:\n" + "\n".join(f"  • {p}" for p in products)
    
    # Diferenciais
    differentials_section = ""
    differentials = identity.get("differentials", [])
    if differentials:
        differentials_section = "NOSSOS DIFERENCIAIS:\n" + "\n".join(f"  ✓ {d}" for d in differentials)
    
    # Público-alvo
    target_audience_section = ""
    target = identity.get("target_audience", {})
    if target:
        parts = []
        if target.get("description"):
            parts.append(f"Público: {target['description']}")
        if target.get("segments"):
            parts.append(f"Segmentos: {', '.join(target['segments'])}")
        if target.get("pain_points"):
            parts.append(f"Dores que resolvemos: {', '.join(target['pain_points'])}")
        if parts:
            target_audience_section = "NOSSO PÚBLICO:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Estilo de comunicação
    communication_style_section = ""
    tone_style = identity.get("tone_style", {})
    if tone_style:
        parts = []
        if tone_style.get("personality_traits"):
            parts.append(f"Personalidade: {', '.join(tone_style['personality_traits'])}")
        if tone_style.get("communication_style"):
            parts.append(f"Estilo: {tone_style['communication_style']}")
        if tone_style.get("use_phrases"):
            parts.append(f"Use expressões como: {', '.join(tone_style['use_phrases'][:5])}")
        if tone_style.get("avoid_phrases"):
            parts.append(f"EVITE expressões como: {', '.join(tone_style['avoid_phrases'][:5])}")
        if parts:
            communication_style_section = "COMO COMUNICAR:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Regras de negócio
    business_rules_section = ""
    rules = identity.get("business_rules", [])
    if rules:
        business_rules_section = "⚠️ REGRAS OBRIGATÓRIAS:\n" + "\n".join(f"  ❗ {r}" for r in rules)
    
    # Palavras-chave
    keywords_section = ""
    keywords = identity.get("keywords", [])
    if keywords:
        keywords_section = f"TERMOS DO NOSSO NEGÓCIO: {', '.join(keywords)}"
    
    # Contexto adicional
    additional_context_section = ""
    additional = identity.get("additional_context", "")
    if additional:
        additional_context_section = f"INFORMAÇÕES ADICIONAIS:\n{additional}"
    
    return IDENTITY_SECTION_TEMPLATE.format(
        description=description,
        products_section=products_section,
        differentials_section=differentials_section,
        target_audience_section=target_audience_section,
        communication_style_section=communication_style_section,
        business_rules_section=business_rules_section,
        keywords_section=keywords_section,
        additional_context_section=additional_context_section,
    )


def build_scope_restriction(
    identity: dict,
    company_name: str,
    scope_config: dict = None,
) -> str:
    """
    Constrói a seção de restrição de escopo (CRÍTICA para evitar IA maluca).
    
    Args:
        identity: Dicionário com dados de identidade
        company_name: Nome da empresa
        scope_config: Configuração de escopo do tenant
    
    Returns:
        String formatada com restrição de escopo
    """
    
    # Lista de produtos/serviços
    products = identity.get("products_services", [])
    if products:
        products_list = "\n".join(f"  ✅ {p}" for p in products)
    else:
        products_list = "  (Nenhum produto/serviço cadastrado - configure a identidade da empresa)"
    
    # O que NÃO oferecemos
    not_offered = identity.get("not_offered", [])
    not_offered_section = ""
    if not_offered:
        not_offered_section = "❌ NÃO TRABALHAMOS COM:\n" + "\n".join(f"  ✖ {n}" for n in not_offered)
        not_offered_section += "\n\nSe perguntarem sobre esses itens, diga que não oferecemos."
    
    # Mensagem padrão fora do escopo
    out_of_scope_message = "Não trabalhamos com isso. Somos especializados em [nossos serviços]. Posso te ajudar com algo nessa área?"
    if scope_config and scope_config.get("out_of_scope_message"):
        out_of_scope_message = scope_config["out_of_scope_message"]
    
    # Descrição do escopo
    scope_description_section = ""
    if scope_config and scope_config.get("description"):
        scope_description_section = f"ESCOPO DETALHADO:\n{scope_config['description']}"
    
    return SCOPE_RESTRICTION_TEMPLATE.format(
        company_name=company_name,
        products_services_list=products_list,
        not_offered_section=not_offered_section,
        out_of_scope_message=out_of_scope_message,
        scope_description_section=scope_description_section,
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
    if custom_prompt:
        return custom_prompt
    
    # Busca template do nicho
    niche = get_niche_config(niche_id)
    if not niche:
        niche = NICHE_TEMPLATES.get("services", NICHE_TEMPLATES["services"])
    
    # ==========================================
    # SEÇÃO DE IDENTIDADE (NOVO!)
    # ==========================================
    identity_section = ""
    if identity:
        identity_section = build_identity_section(identity, company_name)
    
    # ==========================================
    # SEÇÃO DE RESTRIÇÃO DE ESCOPO (NOVO!)
    # ==========================================
    scope_restriction = ""
    if identity:
        scope_restriction = build_scope_restriction(identity, company_name, scope_config)
    elif scope_description:
        # Fallback para formato legado
        scope_restriction = f"""
ESCOPO DO ATENDIMENTO:
Você só deve responder sobre os seguintes assuntos:
{scope_description}

Se o cliente perguntar sobre algo fora deste escopo, responda educadamente que você não tem informações sobre isso.
"""
    
    # Monta lista de campos a coletar
    fields = []
    
    # Campos obrigatórios da identidade
    if identity and identity.get("required_info"):
        fields.append("INFORMAÇÕES OBRIGATÓRIAS:")
        for field in identity["required_info"]:
            fields.append(f"  • {field} (OBRIGATÓRIO)")
    
    # Perguntas obrigatórias da identidade
    if identity and identity.get("required_questions"):
        fields.append("\nPERGUNTAS OBRIGATÓRIAS:")
        for q in identity["required_questions"]:
            fields.append(f"  • {q}")
    
    # Campos do nicho
    fields.append("\nCAMPOS DO NICHO:")
    for field in niche.required_fields:
        fields.append(f"  • {field} (obrigatório)")
    for field in niche.optional_fields:
        fields.append(f"  • {field} (se possível)")
    
    # Perguntas customizadas (legado)
    if custom_questions:
        fields.append("\nPERGUNTAS EXTRAS:")
        for q in custom_questions:
            fields.append(f"  • {q}")
    
    # Monta regras customizadas
    rules_text = ""
    
    # Regras da identidade (já estão na identity_section, mas reforça)
    if identity and identity.get("business_rules"):
        rules_text += "\n⚠️ REGRAS DE NEGÓCIO (SIGA RIGOROSAMENTE):\n"
        for rule in identity["business_rules"]:
            rules_text += f"  ❗ {rule}\n"
    
    # Regras customizadas (legado)
    if custom_rules:
        rules_text += "\nREGRAS ADICIONAIS:\n"
        for rule in custom_rules:
            rules_text += f"  • {rule}\n"
    
    # Contexto do lead
    if lead_context:
        rules_text += "\n📋 CONTEXTO ATUAL DO CLIENTE (use para personalizar):\n"
        
        if lead_context.get("name"):
            rules_text += f"  • Nome: {lead_context['name']}\n"
        if lead_context.get("family_situation"):
            rules_text += f"  • Situação familiar: {lead_context['family_situation']}\n"
        if lead_context.get("work_info"):
            rules_text += f"  • Trabalho: {lead_context['work_info']}\n"
        if lead_context.get("budget_range"):
            rules_text += f"  • Orçamento: {lead_context['budget_range']}\n"
        if lead_context.get("urgency_level"):
            rules_text += f"  • Urgência: {lead_context['urgency_level']}\n"
        if lead_context.get("preferences"):
            prefs = lead_context['preferences']
            if isinstance(prefs, list):
                prefs = ', '.join(prefs)
            rules_text += f"  • Preferências: {prefs}\n"
        if lead_context.get("pain_points"):
            pains = lead_context['pain_points']
            if isinstance(pains, list):
                pains = ', '.join(pains)
            rules_text += f"  • Dores/Problemas: {pains}\n"
        if lead_context.get("objections"):
            objs = lead_context['objections']
            if isinstance(objs, list):
                objs = ', '.join(objs)
            rules_text += f"  • ⚠️ OBJEÇÕES: {objs} (CONTORNE!)\n"
        if lead_context.get("buying_signals"):
            signals = lead_context['buying_signals']
            if isinstance(signals, list):
                signals = ', '.join(signals)
            rules_text += f"  • 🔥 SINAIS DE COMPRA: {signals} (ACELERE!)\n"
    
    # Monta seção de FAQ
    faq_section = ""
    if faq_items:
        faq_section = "\n📚 PERGUNTAS FREQUENTES (FAQ):\nUse estas respostas quando o cliente perguntar sobre estes assuntos:\n"
        for item in faq_items:
            question = item.get("question", "")
            answer = item.get("answer", "")
            if question and answer:
                faq_section += f"\nP: {question}\nR: {answer}\n"
    
    # Determina tom de voz
    tone_display = tone
    if identity and identity.get("tone_style", {}).get("tone"):
        tone_display = identity["tone_style"]["tone"]
    
    # Monta prompt final
    return BASE_SYSTEM_PROMPT.format(
        company_name=company_name,
        identity_section=identity_section,
        scope_restriction=scope_restriction,
        tone=tone_display,
        niche_prompt=niche.prompt_template,
        fields_to_collect="\n".join(fields),
        custom_rules=rules_text,
        faq_section=faq_section,
    )