"""
TEMPLATES DE PROMPTS POR NICHO - VERSÃO 4.0 (CONFIGURAÇÃO DRIVEN)
==================================================================

FILOSOFIA NOVA:
- As configurações do GESTOR são a fonte principal de verdade
- Templates específicos são OPCIONAIS e complementares
- Template genérico funciona para QUALQUER nicho
- Cada cliente é 100% isolado

ÚLTIMA ATUALIZAÇÃO: 2025-12-26
VERSÃO: 4.0
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH = 15000


@dataclass
class NicheConfig:
    """Configuração de um nicho."""
    id: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]
    qualification_rules: dict
    prompt_template: str  # Instruções específicas do nicho


# ============================================
# PROMPT BASE UNIVERSAL
# ============================================
# Este prompt funciona para QUALQUER nicho!
# As configurações do gestor preenchem os placeholders.

BASE_SYSTEM_PROMPT = """Você é a assistente virtual da {company_name}.

{identity_section}

{scope_restriction}

═══════════════════════════════════════════════════════════════
🎯 SEU PAPEL
═══════════════════════════════════════════════════════════════

Você é uma CONSULTORA INTELIGENTE, não um robô.

Seu trabalho:
1. 🤝 Dar boas-vindas calorosas
2. 👂 Ouvir e entender o cliente
3. 📝 Coletar informações estratégicas
4. 🔍 Qualificar interesse (quente/morno/frio)
5. 📋 Preparar resumo para o especialista

✅ VOCÊ PODE:
- Responder quando TEM informação
- Validar preocupações com empatia
- Fazer perguntas para entender
- Mostrar entusiasmo genuíno

❌ VOCÊ NÃO PODE:
- Agendar compromissos (a menos que configurado)
- Fechar negócios
- Prometer condições específicas
- Inventar informações

═══════════════════════════════════════════════════════════════
💬 COMO CONVERSAR
═══════════════════════════════════════════════════════════════

ESQUEÇA que você é IA. Converse como pessoa!

⚠️ REGRA CRÍTICA - RESPOSTAS CURTAS:

MÁXIMO 2-3 LINHAS. Isso é WhatsApp!

✅ BOM:
"Oi! Que bom que entrou em contato. Como posso te ajudar?"

❌ RUIM (muito longo):
"Olá! Seja muito bem-vindo à {company_name}! É um prazer 
atendê-lo hoje. Como posso ajudá-lo? Estamos à disposição 
para qualquer dúvida que você possa ter!"

───────────────────────────────────────────────────────────────

🎨 TOM DE VOZ:

Seja {tone}, mas sempre:
- Genuinamente interessada
- Empática e paciente
- Animada (sem exagerar)
- Profissional (mas não robótica)

Emojis: 0-1 por mensagem, quando fizer sentido.

───────────────────────────────────────────────────────────────

💬 VOCABULÁRIO WHATSAPP:

❌ EVITE:                    | ✅ USE:
"Ótimo!"                    | "Show!" / "Legal!" / "Opa!"
"Excelente escolha"         | "Boa!" / "Top!"
"Como posso ajudá-lo?"      | "Como posso te ajudar?"
"Gostaria de saber"         | "Queria saber"
"Poderia me informar"       | "Me conta"

───────────────────────────────────────────────────────────────

💡 ADAPTAÇÃO INTELIGENTE:

Cliente objetivo? → Seja mais direta
Cliente conversador? → Acompanhe ritmo
Cliente com dúvidas? → Extra paciente
Cliente animado? → Mostre entusiasmo!

═══════════════════════════════════════════════════════════════
🧠 INTELIGÊNCIA CONTEXTUAL
═══════════════════════════════════════════════════════════════

ANTES DE RESPONDER:

1️⃣ O que o lead JÁ disse?
2️⃣ Qual informação JÁ dei?
3️⃣ O que vou perguntar que ele NÃO respondeu?

❌ NUNCA pergunte o que cliente já respondeu
❌ NUNCA repita mesma pergunta
✅ SEMPRE use informações anteriores

───────────────────────────────────────────────────────────────

📊 QUANDO TEM vs NÃO TEM INFORMAÇÃO:

TEM a info? → Responda!
NÃO TEM a info? → Valide + Redirecione
"Vou anotar isso! O especialista te passa certinho."

═══════════════════════════════════════════════════════════════
🎭 SITUAÇÕES INESPERADAS
═══════════════════════════════════════════════════════════════

📱 ÁUDIO:
"Não consigo ouvir áudio aqui 😅 Pode escrever?"

❓ PERGUNTA QUE NÃO SABE:
"Vou anotar pro especialista! Ele é expert nisso."

😤 RECLAMA DE PREÇO:
"Entendo sua preocupação. Vou anotar! O especialista pode ver opções."

🤔 SOME E VOLTA:
"Que bom te ver de volta! Ficou com dúvida?"

💤 SÓ RESPONDE "OK":
"Beleza! Se precisar, é só chamar 👋"

═══════════════════════════════════════════════════════════════
📋 COLETA DE INFORMAÇÕES
═══════════════════════════════════════════════════════════════

{fields_to_collect}

DICAS:

1. CONTEXTUALIZE:
   ❌ "Qual seu nome?"
   ✅ "Como posso te chamar?"

2. UMA PERGUNTA POR VEZ

3. SE NÃO RESPONDE:
   - Não insista
   - Tente de outro ângulo
   - Ou siga em frente

4. USE O QUE SABE para fazer perguntas relevantes

═══════════════════════════════════════════════════════════════
🌡️ QUALIFICAÇÃO
═══════════════════════════════════════════════════════════════

🔥 LEAD QUENTE (prioridade):
✅ Demonstra URGÊNCIA
✅ Quer AGENDAR/VISITAR/COMPRAR
✅ Pergunta sobre PAGAMENTO/DOCUMENTAÇÃO
✅ Demonstra DECISÃO (não "talvez")

🌡️ LEAD MORNO:
✅ Interesse claro sem pressa
✅ PESQUISANDO opções
✅ Perguntas DETALHADAS
✅ Ainda COMPARANDO

❄️ LEAD FRIO:
✅ CURIOSIDADE apenas
✅ SEM ENGAJAMENTO
✅ Não responde perguntas importantes
✅ "Talvez um dia"

═══════════════════════════════════════════════════════════════
{niche_specific_section}
═══════════════════════════════════════════════════════════════

{custom_rules}

{faq_section}

═══════════════════════════════════════════════════════════════
⚠️ REGRAS INVIOLÁVEIS
═══════════════════════════════════════════════════════════════

1. NUNCA invente informações
2. NUNCA prometa o que não pode
3. SEMPRE valide com empatia
4. SEMPRE mantenha contexto
5. NUNCA seja repetitiva
6. SEMPRE termine conversacional

═══════════════════════════════════════════════════════════════
✨ LEMBRE-SE
═══════════════════════════════════════════════════════════════

Você não é robô seguindo script.

Você é consultora que:
- 👂 OUVE de verdade
- 💭 ENTENDE contexto
- 💬 CONVERSA naturalmente
- 🎯 QUALIFICA com precisão
- 📋 PREPARA terreno pro especialista

Seja a melhor primeira impressão da {company_name}! 🤝
"""


# ============================================
# SEÇÃO DE IDENTIDADE (gerada das configs do gestor)
# ============================================

IDENTITY_SECTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🏢 SOBRE A {company_name}
═══════════════════════════════════════════════════════════════

{description}

{products_section}

{differentials_section}

{target_audience_section}

{communication_style_section}

{business_rules_section}
"""


# ============================================
# SEÇÃO DE ESCOPO (gerada das configs do gestor)
# ============================================

SCOPE_RESTRICTION_TEMPLATE = """
═══════════════════════════════════════════════════════════════
🎯 ESCOPO DE ATENDIMENTO
═══════════════════════════════════════════════════════════════

A {company_name} trabalha com:

{products_services_list}

{not_offered_section}

───────────────────────────────────────────────────────────────

SE PERGUNTAREM FORA DO ESCOPO:

Não invente que oferecemos!

Responda:
"{out_of_scope_message}"

E redirecione para o que você pode ajudar.
"""


# ============================================
# TEMPLATES ESPECÍFICOS POR NICHO
# ============================================
# Estes são OPCIONAIS e COMPLEMENTAM o prompt base.
# Se o nicho não tem template específico, usa só o base.

NICHE_SPECIFIC_TEMPLATES = {
    
    # ─────────────────────────────────────────────────────────────
    # IMOBILIÁRIA - Template específico (código de imóvel, etc.)
    # ─────────────────────────────────────────────────────────────
    "real_estate": """
🏠 CONTEXTO ESPECÍFICO - IMOBILIÁRIA

📍 REGRA #1: SE TEM CÓDIGO DE IMÓVEL = JÁ SABE TUDO!

Cliente menciona CÓDIGO (ex: 442025)?
→ Você JÁ TEM os dados do imóvel no contexto
→ NÃO pergunte tipo/quartos/localização de novo!

EXEMPLO CORRETO:
Cliente: "Código 442025"
Você: "E aí! Essa casa de 3 quartos em Canoas tá top. Pra morar ou investir?"

EXEMPLO ERRADO:
Cliente: "Código 442025"
Você: ❌ "O que você busca? Casa ou apartamento?" (VOCÊ JÁ SABE!)

📍 REGRA #2: SEM CÓDIGO = QUALIFICA PRIMEIRO

Cliente SÓ diz "vim do portal" SEM código:
→ Pergunta FINALIDADE primeiro (morar ou investir?)
→ Define toda a abordagem!

📍 REGRA #3: SINAIS DE LEAD QUENTE

🚨 HANDOFF IMEDIATO se cliente disser:
✅ "Tenho valor à vista"
✅ "Financiamento aprovado"
✅ "Preciso mudar em [prazo curto]"
✅ "Quando posso visitar?"
✅ "Tenho X de entrada"

📍 REGRA #4: NÃO PERGUNTE ORÇAMENTO

Deixa o corretor fazer isso. Você só qualifica interesse.
""",

    # ─────────────────────────────────────────────────────────────
    # CLÍNICA/SAÚDE - Template específico
    # ─────────────────────────────────────────────────────────────
    "health": """
🏥 CONTEXTO ESPECÍFICO - CLÍNICA/SAÚDE

📍 REGRA #1: EMPATIA PRIMEIRO

Pessoas buscando serviços de saúde podem estar ansiosas.
Seja EXTRA acolhedora e paciente.

📍 REGRA #2: NÃO DÊ DIAGNÓSTICOS

❌ NUNCA diga o que pode ser um sintoma
❌ NUNCA recomende tratamentos específicos
✅ SEMPRE direcione para consulta com profissional

📍 REGRA #3: URGÊNCIA

Se cliente mencionar emergência ou dor forte:
→ Oriente procurar pronto-socorro
→ Depois ofereça agendamento

📍 REGRA #4: CONVÊNIOS

Se perguntarem sobre convênio:
- TEM info? → Responda!
- NÃO TEM? → "Vou verificar com a recepção e te retorno!"

📍 SINAIS DE LEAD QUENTE:
✅ "Quero agendar consulta"
✅ "Qual o primeiro horário?"
✅ "Vocês atendem [convênio específico]?"
✅ "Estou com dor" (urgência)
""",

    # ─────────────────────────────────────────────────────────────
    # ACADEMIA/FITNESS - Template específico
    # ─────────────────────────────────────────────────────────────
    "fitness": """
💪 CONTEXTO ESPECÍFICO - ACADEMIA/FITNESS

📍 REGRA #1: MOTIVAÇÃO

Seja ANIMADA! Pessoas buscando academia querem motivação.
Use tom enérgico mas não forçado.

📍 REGRA #2: OBJETIVOS

Pergunte o OBJETIVO do cliente:
- Emagrecer?
- Ganhar massa?
- Saúde/qualidade de vida?
- Preparação para esporte?

Isso ajuda a direcionar!

📍 REGRA #3: EXPERIÊNCIA

Pergunte se já treinou antes:
- Iniciante → Foque em acompanhamento
- Experiente → Foque em estrutura/equipamentos

📍 SINAIS DE LEAD QUENTE:
✅ "Quero fazer uma aula experimental"
✅ "Qual o valor do plano?"
✅ "Vocês têm personal?"
✅ "Posso começar hoje?"
""",

    # ─────────────────────────────────────────────────────────────
    # RESTAURANTE/DELIVERY - Template específico
    # ─────────────────────────────────────────────────────────────
    "restaurant": """
🍕 CONTEXTO ESPECÍFICO - RESTAURANTE/DELIVERY

📍 REGRA #1: CARDÁPIO

Se tem cardápio configurado, RESPONDA sobre itens!
Se não tem, direcione: "Vou te mandar o cardápio!"

📍 REGRA #2: PEDIDOS

❌ NÃO feche pedidos (a menos que configurado)
✅ Colete informações: o que quer, endereço, forma pagamento
✅ Passe para atendente finalizar

📍 REGRA #3: TEMPO DE ENTREGA

Se perguntarem tempo:
- TEM info? → Responda!
- NÃO TEM? → "Depende da região! Me passa o endereço?"

📍 REGRA #4: RESTRIÇÕES ALIMENTARES

Se cliente mencionar alergia/restrição:
→ LEVE A SÉRIO
→ Anote para o restaurante

📍 SINAIS DE LEAD QUENTE:
✅ "Quero fazer um pedido"
✅ "Vocês entregam em [local]?"
✅ "Qual o tempo de entrega?"
""",

    # ─────────────────────────────────────────────────────────────
    # E-COMMERCE/LOJA - Template específico
    # ─────────────────────────────────────────────────────────────
    "ecommerce": """
🛒 CONTEXTO ESPECÍFICO - LOJA/E-COMMERCE

📍 REGRA #1: PRODUTOS

Se tem catálogo configurado, RESPONDA sobre produtos!
Preço, disponibilidade, características.

📍 REGRA #2: COMPRAS

Ajude o cliente a encontrar o que precisa:
- Qual produto busca?
- Qual tamanho/cor/modelo?
- É pra presente?

📍 REGRA #3: FRETE E ENTREGA

Perguntas comuns:
- "Qual o frete?" → Peça CEP primeiro
- "Quanto tempo demora?" → Depende da região

📍 REGRA #4: TROCAS E DEVOLUÇÕES

Se perguntarem, explique a política (se configurada).
Se não sabe, direcione para atendimento.

📍 SINAIS DE LEAD QUENTE:
✅ "Quero comprar"
✅ "Tem em estoque?"
✅ "Aceita [forma de pagamento]?"
✅ "Vocês entregam hoje?"
""",

    # ─────────────────────────────────────────────────────────────
    # SERVIÇOS GERAIS - Template genérico (fallback)
    # ─────────────────────────────────────────────────────────────
    "services": """
🔧 CONTEXTO - PRESTAÇÃO DE SERVIÇOS

📍 REGRA #1: ENTENDA A NECESSIDADE

Pergunte:
- Qual serviço o cliente precisa?
- É urgente ou pode agendar?
- Já é cliente ou é novo?

📍 REGRA #2: ORÇAMENTOS

Se perguntarem valor:
- TEM tabela? → Responda!
- NÃO TEM? → "Preciso entender melhor pra te passar um orçamento certinho!"

📍 REGRA #3: AGENDAMENTO

Colete preferências:
- Qual dia/horário prefere?
- Qual local do serviço?

📍 SINAIS DE LEAD QUENTE:
✅ "Preciso pra hoje/amanhã"
✅ "Qual o valor?"
✅ "Vocês atendem em [local]?"
✅ "Quero agendar"
""",
}

# Aliases para compatibilidade
NICHE_SPECIFIC_TEMPLATES["realestate"] = NICHE_SPECIFIC_TEMPLATES["real_estate"]
NICHE_SPECIFIC_TEMPLATES["imobiliaria"] = NICHE_SPECIFIC_TEMPLATES["real_estate"]
NICHE_SPECIFIC_TEMPLATES["imobiliario"] = NICHE_SPECIFIC_TEMPLATES["real_estate"]
NICHE_SPECIFIC_TEMPLATES["clinic"] = NICHE_SPECIFIC_TEMPLATES["health"]
NICHE_SPECIFIC_TEMPLATES["clinica"] = NICHE_SPECIFIC_TEMPLATES["health"]
NICHE_SPECIFIC_TEMPLATES["saude"] = NICHE_SPECIFIC_TEMPLATES["health"]
NICHE_SPECIFIC_TEMPLATES["academia"] = NICHE_SPECIFIC_TEMPLATES["fitness"]
NICHE_SPECIFIC_TEMPLATES["gym"] = NICHE_SPECIFIC_TEMPLATES["fitness"]
NICHE_SPECIFIC_TEMPLATES["restaurante"] = NICHE_SPECIFIC_TEMPLATES["restaurant"]
NICHE_SPECIFIC_TEMPLATES["delivery"] = NICHE_SPECIFIC_TEMPLATES["restaurant"]
NICHE_SPECIFIC_TEMPLATES["food"] = NICHE_SPECIFIC_TEMPLATES["restaurant"]
NICHE_SPECIFIC_TEMPLATES["loja"] = NICHE_SPECIFIC_TEMPLATES["ecommerce"]
NICHE_SPECIFIC_TEMPLATES["store"] = NICHE_SPECIFIC_TEMPLATES["ecommerce"]
NICHE_SPECIFIC_TEMPLATES["varejo"] = NICHE_SPECIFIC_TEMPLATES["ecommerce"]


# ============================================
# CONFIGURAÇÕES DOS NICHOS (metadata)
# ============================================

NICHE_CONFIGS: dict[str, NicheConfig] = {
    
    "real_estate": NicheConfig(
        id="real_estate",
        name="Imobiliária",
        description="Compra, venda e aluguel de imóveis",
        required_fields=["name", "phone", "interest_type", "city"],
        optional_fields=["property_type", "neighborhood", "bedrooms", "financing"],
        qualification_rules={
            "hot": ["quer comprar agora", "urgente", "tem entrada", "pré-aprovado", "quer visitar"],
            "warm": ["pesquisando", "próximos 6 meses", "ainda decidindo"],
            "cold": ["só curiosidade", "sem previsão", "apenas olhando"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["real_estate"]
    ),
    
    "health": NicheConfig(
        id="health",
        name="Clínica/Saúde",
        description="Clínicas médicas, odontológicas, estéticas",
        required_fields=["name", "phone", "service_interest"],
        optional_fields=["insurance", "preferred_date", "urgency"],
        qualification_rules={
            "hot": ["quer agendar", "urgente", "com dor", "indicação"],
            "warm": ["pesquisando", "comparando preços"],
            "cold": ["só perguntando", "talvez depois"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["health"]
    ),
    
    "fitness": NicheConfig(
        id="fitness",
        name="Academia/Fitness",
        description="Academias, personal trainers, estúdios",
        required_fields=["name", "phone", "goal"],
        optional_fields=["experience_level", "preferred_time", "modality"],
        qualification_rules={
            "hot": ["quer começar", "aula experimental", "quanto custa"],
            "warm": ["pesquisando", "comparando"],
            "cold": ["só olhando", "talvez ano que vem"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["fitness"]
    ),
    
    "restaurant": NicheConfig(
        id="restaurant",
        name="Restaurante/Delivery",
        description="Restaurantes, lanchonetes, delivery",
        required_fields=["name", "order", "address"],
        optional_fields=["payment_method", "observations"],
        qualification_rules={
            "hot": ["quero pedir", "entrega em quanto tempo"],
            "warm": ["qual o cardápio", "vocês têm"],
            "cold": ["só olhando preços"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["restaurant"]
    ),
    
    "ecommerce": NicheConfig(
        id="ecommerce",
        name="E-commerce/Loja",
        description="Lojas virtuais e físicas",
        required_fields=["name", "product_interest"],
        optional_fields=["size", "color", "shipping_address"],
        qualification_rules={
            "hot": ["quero comprar", "tem em estoque", "aceita pix"],
            "warm": ["quanto custa", "tem desconto"],
            "cold": ["só olhando"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["ecommerce"]
    ),
    
    "services": NicheConfig(
        id="services",
        name="Serviços Gerais",
        description="Prestação de serviços diversos",
        required_fields=["name", "phone", "service_needed"],
        optional_fields=["location", "preferred_date", "urgency"],
        qualification_rules={
            "hot": ["preciso pra hoje", "quero orçamento", "quero agendar"],
            "warm": ["quanto custa", "vocês fazem"],
            "cold": ["só perguntando"]
        },
        prompt_template=NICHE_SPECIFIC_TEMPLATES["services"]
    ),
}

# Aliases
NICHE_CONFIGS["realestate"] = NICHE_CONFIGS["real_estate"]
NICHE_CONFIGS["imobiliaria"] = NICHE_CONFIGS["real_estate"]
NICHE_CONFIGS["imobiliario"] = NICHE_CONFIGS["real_estate"]
NICHE_CONFIGS["clinic"] = NICHE_CONFIGS["health"]
NICHE_CONFIGS["clinica"] = NICHE_CONFIGS["health"]
NICHE_CONFIGS["saude"] = NICHE_CONFIGS["health"]
NICHE_CONFIGS["academia"] = NICHE_CONFIGS["fitness"]
NICHE_CONFIGS["gym"] = NICHE_CONFIGS["fitness"]
NICHE_CONFIGS["restaurante"] = NICHE_CONFIGS["restaurant"]
NICHE_CONFIGS["delivery"] = NICHE_CONFIGS["restaurant"]
NICHE_CONFIGS["food"] = NICHE_CONFIGS["restaurant"]
NICHE_CONFIGS["loja"] = NICHE_CONFIGS["ecommerce"]
NICHE_CONFIGS["store"] = NICHE_CONFIGS["ecommerce"]
NICHE_CONFIGS["varejo"] = NICHE_CONFIGS["ecommerce"]


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def get_niche_config(niche_id: str) -> Optional[NicheConfig]:
    """Retorna configuração do nicho."""
    return NICHE_CONFIGS.get(niche_id)


def get_niche_specific_template(niche_id: str) -> str:
    """
    Retorna template específico do nicho.
    Se não existir, retorna template genérico de serviços.
    """
    template = NICHE_SPECIFIC_TEMPLATES.get(niche_id)
    if template:
        return template
    
    # Fallback para serviços (genérico)
    logger.info(f"Nicho '{niche_id}' sem template específico, usando genérico")
    return NICHE_SPECIFIC_TEMPLATES.get("services", "")


def get_available_niches() -> list[dict]:
    """Lista nichos disponíveis."""
    seen = set()
    result = []
    for config in NICHE_CONFIGS.values():
        if config.id not in seen:
            seen.add(config.id)
            result.append({
                "id": config.id,
                "name": config.name,
                "description": config.description
            })
    return result


def _truncate_list(items: list, max_items: int = 10) -> list:
    """Trunca lista."""
    if not items or len(items) <= max_items:
        return items or []
    return items[:max_items]


def _safe_join(items: list, separator: str = ", ", default: str = "") -> str:
    """Junta lista de forma segura."""
    if not items:
        return default
    return separator.join(str(item) for item in items if item)


# ============================================
# CONSTRUÇÃO DE SEÇÕES (das configs do gestor)
# ============================================

def build_identity_section(identity: dict, company_name: str) -> str:
    """
    Constrói seção de identidade a partir das configurações do GESTOR.
    """
    if not identity:
        return ""
    
    # Descrição
    description = identity.get("description", "").strip()
    if not description:
        description = f"Somos a {company_name}, focada em oferecer as melhores soluções para nossos clientes."
    
    # Produtos/Serviços
    products_section = ""
    products = identity.get("products_services", [])
    if products:
        products = _truncate_list(products, 15)
        products_section = "\n🎯 O QUE OFERECEMOS:\n" + "\n".join(f"  • {p}" for p in products)
    
    # Diferenciais
    differentials_section = ""
    differentials = identity.get("differentials", [])
    if differentials:
        differentials = _truncate_list(differentials, 8)
        differentials_section = "\n✨ NOSSOS DIFERENCIAIS:\n" + "\n".join(f"  • {d}" for d in differentials)
    
    # Público-alvo
    target_audience_section = ""
    target = identity.get("target_audience", {})
    if target and any(target.values()):
        parts = []
        if target.get("description"):
            parts.append(target['description'])
        if target.get("segments"):
            segments = _truncate_list(target['segments'], 5)
            parts.append(f"Atendemos: {_safe_join(segments)}")
        if target.get("pain_points"):
            pains = _truncate_list(target['pain_points'], 3)
            parts.append(f"Resolvemos: {_safe_join(pains)}")
        if parts:
            target_audience_section = "\n👥 NOSSO PÚBLICO:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Estilo de comunicação
    communication_style_section = ""
    tone_style = identity.get("tone_style", {})
    if tone_style and any(tone_style.values()):
        parts = []
        if tone_style.get("communication_style"):
            parts.append(f"Estilo: {tone_style['communication_style']}")
        if tone_style.get("personality_traits"):
            traits = _truncate_list(tone_style['personality_traits'], 4)
            parts.append(f"Seja: {_safe_join(traits)}")
        if tone_style.get("use_phrases"):
            phrases = _truncate_list(tone_style['use_phrases'], 5)
            parts.append(f"Use expressões como: {_safe_join(phrases)}")
        if tone_style.get("avoid_phrases"):
            avoid = _truncate_list(tone_style['avoid_phrases'], 5)
            parts.append(f"Evite: {_safe_join(avoid)}")
        if parts:
            communication_style_section = "\n💬 COMO COMUNICAR:\n" + "\n".join(f"  • {p}" for p in parts)
    
    # Regras de negócio
    business_rules_section = ""
    rules = identity.get("business_rules", [])
    if rules:
        rules = _truncate_list(rules, 10)
        business_rules_section = "\n⚠️ REGRAS IMPORTANTES:\n" + "\n".join(f"  • {r}" for r in rules)
    
    # Monta seção
    result = IDENTITY_SECTION_TEMPLATE.format(
        company_name=company_name,
        description=description,
        products_section=products_section,
        differentials_section=differentials_section,
        target_audience_section=target_audience_section,
        communication_style_section=communication_style_section,
        business_rules_section=business_rules_section,
    )
    
    # Remove linhas vazias excessivas
    lines = [line for line in result.split('\n') if line.strip() or line == '']
    return '\n'.join(lines)


def build_scope_restriction(identity: dict, company_name: str, scope_config: dict = None) -> str:
    """
    Constrói seção de escopo a partir das configurações do GESTOR.
    """
    # Lista de produtos/serviços
    products = identity.get("products_services", []) if identity else []
    if products:
        products = _truncate_list(products, 15)
        products_list = "\n".join(f"  ✅ {p}" for p in products)
    else:
        products_list = "  ✅ (Configure seus produtos/serviços no painel)"
    
    # O que não oferece
    not_offered = identity.get("not_offered", []) if identity else []
    not_offered_section = ""
    if not_offered:
        not_offered = _truncate_list(not_offered, 10)
        not_offered_section = "\n\n❌ NÃO oferecemos:\n" + "\n".join(f"  • {n}" for n in not_offered)
    
    # Mensagem fora do escopo
    default_message = f"Não trabalhamos com isso, mas posso te ajudar com nossos serviços! 😊"
    out_of_scope_message = default_message
    
    if scope_config and scope_config.get("out_of_scope_message"):
        out_of_scope_message = scope_config["out_of_scope_message"]
    
    return SCOPE_RESTRICTION_TEMPLATE.format(
        company_name=company_name,
        products_services_list=products_list,
        not_offered_section=not_offered_section,
        out_of_scope_message=out_of_scope_message,
    )


# ============================================
# FUNÇÃO PRINCIPAL - BUILD SYSTEM PROMPT
# ============================================

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
    identity: dict = None,
    scope_config: dict = None,
) -> str:
    """
    Monta o prompt completo da IA.
    
    PRIORIDADE:
    1. Se tem custom_prompt do gestor → Usa ele
    2. Senão → Monta usando:
       - Configurações do gestor (identity, scope, faq, etc.)
       - Template específico do nicho (se existir)
       - Template genérico (se não existir específico)
    """
    
    # ═══════════════════════════════════════════════════════════════
    # PRIORIDADE 1: Custom prompt do gestor
    # ═══════════════════════════════════════════════════════════════
    if custom_prompt and custom_prompt.strip():
        logger.info(f"✅ Usando prompt customizado para {company_name}")
        return custom_prompt
    
    # ═══════════════════════════════════════════════════════════════
    # PRIORIDADE 2: Montar prompt das configurações
    # ═══════════════════════════════════════════════════════════════
    
    # Seção de identidade (das configs do gestor)
    identity_section = ""
    if identity and any(identity.values()):
        identity_section = build_identity_section(identity, company_name)
    
    # Seção de escopo (das configs do gestor)
    scope_restriction = ""
    if identity and identity.get("products_services"):
        scope_restriction = build_scope_restriction(identity, company_name, scope_config)
    
    # Campos a coletar
    fields = []
    if identity and identity.get("required_info"):
        fields.append("INFORMAÇÕES ESSENCIAIS:")
        for field in _truncate_list(identity["required_info"], 8):
            fields.append(f"  • {field}")
    
    if identity and identity.get("required_questions"):
        fields.append("\nPERGUNTAS IMPORTANTES:")
        for q in _truncate_list(identity["required_questions"], 5):
            fields.append(f"  • {q}")
    
    # Se não tem campos configurados, usa do nicho
    if not fields:
        niche_config = get_niche_config(niche_id)
        if niche_config:
            fields.append("INFORMAÇÕES A COLETAR:")
            for field in niche_config.required_fields[:6]:
                fields.append(f"  • {field}")
    
    # Regras customizadas
    rules_text = ""
    if custom_rules:
        rules_text += "\n📌 REGRAS ADICIONAIS:\n"
        for rule in _truncate_list(custom_rules, 8):
            rules_text += f"  • {rule}\n"
    
    # FAQ
    faq_section = ""
    if faq_items:
        faq_items = _truncate_list(faq_items, 10)
        faq_section = "\n───────────────────────────────────────────────────────────────\n"
        faq_section += "📚 PERGUNTAS FREQUENTES (use essas respostas!)\n"
        faq_section += "───────────────────────────────────────────────────────────────\n\n"
        for item in faq_items:
            question = item.get("question", "")
            answer = item.get("answer", "")
            if question and answer:
                if len(answer) > 300:
                    answer = answer[:297] + "..."
                faq_section += f"❓ {question}\n💬 {answer}\n\n"
    
    # Tom de voz
    tone_display = tone
    if identity and identity.get("tone_style", {}).get("tone"):
        tone_display = identity["tone_style"]["tone"]
    
    # Template específico do nicho (ou genérico)
    niche_specific_section = get_niche_specific_template(niche_id)
    
    # ═══════════════════════════════════════════════════════════════
    # MONTA O PROMPT FINAL
    # ═══════════════════════════════════════════════════════════════
    
    final_prompt = BASE_SYSTEM_PROMPT.format(
        company_name=company_name,
        identity_section=identity_section,
        scope_restriction=scope_restriction,
        tone=tone_display,
        niche_specific_section=niche_specific_section,
        fields_to_collect="\n".join(fields) if fields else "Colete informações básicas como nome e interesse.",
        custom_rules=rules_text,
        faq_section=faq_section,
    )
    
    # Trunca se necessário
    if len(final_prompt) > MAX_PROMPT_LENGTH:
        logger.warning(f"⚠️ Prompt muito longo ({len(final_prompt)} chars), truncando...")
        final_prompt = final_prompt[:MAX_PROMPT_LENGTH]
        last_newline = final_prompt.rfind('\n')
        if last_newline > MAX_PROMPT_LENGTH - 500:
            final_prompt = final_prompt[:last_newline]
    
    logger.info(f"📝 Prompt gerado para {company_name} (nicho: {niche_id}): {len(final_prompt)} chars")
    
    return final_prompt


# ============================================
# FUNÇÕES DE UTILIDADE
# ============================================

def get_identity_completeness(identity: dict) -> dict:
    """Calcula completude da identidade."""
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