"""
SERVIÇO DE GUARDA DA IA - VELARIS v3.0 (REFATORADO)
====================================================

🔥 MUDANÇAS CRÍTICAS:
1. ESCOPO verificado PRIMEIRO (antes de preço!)
2. Detecção de escopo baseada na IDENTIDADE do tenant
3. Palavras-chave do negócio vs palavras fora do escopo
4. Melhor logging para debug
5. Guards configuráveis por tenant

⚙️ ORDEM DOS GUARDS (CRÍTICA!):
1. Business Hours - Fora do horário?
2. FAQ - Tem resposta pronta?
3. SCOPE GUARD - Está falando do nosso negócio? ← PRIMEIRO!
4. Price Guard - Só se estiver no escopo
5. Insistence Guard - Insistindo em preço?
6. Message Limit - Muitas mensagens?

Regra de ouro: Se não é do nosso negócio, não importa se perguntou preço.
"""

from datetime import datetime
from typing import Optional, Tuple, List
import pytz
import re
import logging

logger = logging.getLogger(__name__)


# ========================================================
# CONFIGURAÇÕES PADRÃO
# ========================================================

DEFAULT_OUT_OF_SCOPE_MESSAGE = (
    "Desculpe, não posso ajudá-lo com isso. "
    "Posso te ajudar com dúvidas sobre nossos produtos e serviços! 😊"
)

DEFAULT_PRICE_MESSAGE = (
    "Para garantir informações corretas e atualizadas, "
    "quem confirma valores é sempre o especialista. "
    "Me conta qual produto/serviço você está buscando "
    "que eu já direciono certinho! 😊"
)

DEFAULT_INSISTENCE_MESSAGE = (
    "Eu entendo totalmente! Mas, para evitar qualquer informação incorreta, "
    "somente o especialista confirma valores. "
    "Me diz o que te interessa que eu agilizo o atendimento para você 😉"
)

# Palavras que SEMPRE indicam fora do escopo (genéricas)
UNIVERSAL_FORBIDDEN_TOPICS = [
    # Serviços não relacionados
    "receita", "horóscopo", "previsão do tempo",
    # Programação
    "programação", "python", "javascript", "código", "algoritmo",
    # Política
    "política", "eleição", "presidente", "deputado", "vereador",
    # Outros
    "história do brasil", "universo", "poema", "piada",
    # Jogos/apostas
    "aposta", "loteria", "mega sena", "jogo do bicho",
]

# Categorias de serviços para detecção de escopo
SERVICE_CATEGORIES = {
    "limpeza": ["limpeza", "higienização", "higienizacao", "lavagem", "faxina", "limpar", "sofa", "estofado", "carpete", "tapete"],
    "jardinagem": ["jardinagem", "poda", "árvore", "arvore", "grama", "jardim", "plantas", "paisagismo"],
    "beleza": ["cílios", "cilios", "alongamento", "manicure", "pedicure", "cabelo", "sobrancelha", "depilação", "depilacao", "botox", "preenchimento", "unha", "maquiagem", "design"],
    "construcao": ["pedreiro", "obra", "construção", "construcao", "reforma", "pintura de parede", "encanador", "eletricista", "gesso", "azulejo"],
    "tecnologia": ["site", "aplicativo", "sistema", "software", "computador", "celular", "notebook", "ti", "programador"],
    "alimentacao": ["comida", "marmita", "delivery", "restaurante", "lanche", "pizza", "hamburguer", "sushi"],
    "saude": ["médico", "medico", "consulta", "exame", "dentista", "psicólogo", "psicologo", "fisioterapia", "nutricionista"],
    "automotivo": ["carro", "moto", "mecânico", "mecanico", "funilaria", "lataria", "pneu", "óleo", "oleo", "revisão", "revisao"],
    "pet": ["cachorro", "gato", "pet", "veterinário", "veterinario", "banho e tosa", "ração", "racao"],
    "educacao": ["curso", "aula", "professor", "escola", "faculdade", "inglês", "ingles", "espanhol"],
    "moda": ["vestido", "roupa", "terno", "traje", "aluguel", "festa", "casamento", "formatura", "evento", "look", "moda"],
    "imoveis": ["apartamento", "casa", "imóvel", "imovel", "aluguel", "compra", "venda", "terreno", "condomínio", "condominio"],
}


# ========================================================
# UTILS
# ========================================================

def get_current_day_name() -> str:
    days = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]
    return days[datetime.now().weekday()]


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação (lowercase, sem acentos básicos)."""
    if not text:
        return ""
    text = text.lower().strip()
    # Normalização básica de acentos
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'ê': 'e',
        'í': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u', 'ü': 'u',
        'ç': 'c',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


# ========================================================
# BUSINESS HOURS
# ========================================================

def check_business_hours(settings: dict, timezone: str = "America/Sao_Paulo") -> Tuple[bool, Optional[str]]:
    """Verifica se está dentro do horário de atendimento."""
    
    # Verifica no novo formato primeiro
    business_hours_config = settings.get("business_hours", {})
    is_enabled = business_hours_config.get("enabled", False) or settings.get("business_hours_enabled", False)
    
    if not is_enabled:
        return True, None

    # Pega schedule do novo formato ou antigo
    schedule = business_hours_config.get("schedule", {}) or settings.get("business_hours", {})
    
    if not schedule:
        return True, None

    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()

    day_name = get_current_day_name()
    config = schedule.get(day_name, {})

    if not config.get("enabled", False):
        msg = (
            business_hours_config.get("out_of_hours_message") or
            settings.get("out_of_hours_message") or
            "Estamos fora do horário de atendimento. Retornaremos em breve!"
        )
        return False, msg

    open_time = config.get("open", "")
    close_time = config.get("close", "")
    
    if not open_time or not close_time:
        return True, None

    current = now.strftime("%H:%M")

    if open_time <= current <= close_time:
        return True, None

    msg = (
        business_hours_config.get("out_of_hours_message") or
        settings.get("out_of_hours_message") or
        "Estamos fora do horário de atendimento. Retornaremos em breve!"
    )
    return False, msg


# ========================================================
# FAQ
# ========================================================

def check_faq(message: str, settings: dict) -> Optional[str]:
    """Verifica se a mensagem corresponde a uma FAQ."""
    
    # Verifica no novo formato primeiro
    faq_config = settings.get("faq", {})
    is_enabled = faq_config.get("enabled", True) if faq_config else settings.get("faq_enabled", True)
    
    if not is_enabled:
        return None

    faq_items = faq_config.get("items", []) if faq_config else settings.get("faq_items", [])
    
    if not faq_items:
        return None

    msg = normalize_text(message)

    for item in faq_items:
        question = normalize_text(item.get("question", ""))
        answer = item.get("answer", "")
        keywords = item.get("keywords", [])

        # Match direto na pergunta
        if question and question in msg:
            return answer

        # Match por keywords
        if keywords:
            normalized_keywords = [normalize_text(kw) for kw in keywords]
            matches = sum(1 for kw in normalized_keywords if kw in msg)
            if matches >= 2 or (len(keywords) == 1 and matches == 1):
                return answer

    return None


# ========================================================
# 🎯 SCOPE GUARD (CRÍTICO - DEVE VIR PRIMEIRO!)
# ========================================================

def extract_scope_keywords(settings: dict) -> Tuple[List[str], List[str], str]:
    """
    Extrai palavras-chave do escopo da identidade do tenant.
    
    Returns:
        Tuple[in_scope_keywords, out_of_scope_keywords, out_of_scope_message]
    """
    in_scope = []
    out_of_scope = []
    
    # Novo formato (identity)
    identity = settings.get("identity", {})
    scope_config = settings.get("scope", {})
    
    # Produtos/serviços que oferecemos = IN SCOPE
    products = identity.get("products_services", [])
    if products:
        for product in products:
            # Adiciona cada palavra do produto
            words = normalize_text(product).split()
            in_scope.extend(words)
            # Adiciona o produto completo também
            in_scope.append(normalize_text(product))
    
    # Keywords do negócio = IN SCOPE
    keywords = identity.get("keywords", [])
    if keywords:
        in_scope.extend([normalize_text(k) for k in keywords])
    
    # O que NÃO oferecemos = OUT OF SCOPE
    not_offered = identity.get("not_offered", [])
    if not_offered:
        for item in not_offered:
            words = normalize_text(item).split()
            out_of_scope.extend(words)
            out_of_scope.append(normalize_text(item))
    
    # Tópicos bloqueados (do scope config)
    blocked = scope_config.get("blocked_topics", [])
    if blocked:
        out_of_scope.extend([normalize_text(t) for t in blocked])
    
    # Mensagem de fora do escopo
    out_of_scope_message = (
        scope_config.get("out_of_scope_message") or
        settings.get("out_of_scope_message") or
        DEFAULT_OUT_OF_SCOPE_MESSAGE
    )
    
    # Remove duplicatas e strings vazias
    in_scope = list(set([w for w in in_scope if w and len(w) > 2]))
    out_of_scope = list(set([w for w in out_of_scope if w and len(w) > 2]))
    
    return in_scope, out_of_scope, out_of_scope_message


def detect_service_category(message: str) -> List[str]:
    """
    Detecta a(s) categoria(s) de serviço mencionadas na mensagem.
    Retorna lista de categorias detectadas.
    """
    msg = normalize_text(message)
    detected = []
    
    for category, keywords in SERVICE_CATEGORIES.items():
        for keyword in keywords:
            if keyword in msg:
                if category not in detected:
                    detected.append(category)
                break  # Não precisa checar mais keywords dessa categoria
    
    return detected


def get_allowed_categories_for_niche(niche: str) -> List[str]:
    """Retorna categorias permitidas para um nicho."""
    niche_allowed = {
        "fashion": ["moda"],
        "events": ["moda"],  # Eventos também permite moda
        "real_estate": ["imoveis"],
        "healthcare": ["saude"],
        "beauty": ["beleza"],
        "services": [],  # Genérico, tratamento especial
        "education": ["educacao"],
        "food": ["alimentacao"],
        "automotive": ["automotivo"],
        "pet": ["pet"],
        "tech": ["tecnologia"],
    }
    return niche_allowed.get(niche, [])


def check_scope(message: str, settings: dict) -> Tuple[bool, Optional[str]]:
    """
    Verifica se a mensagem está dentro do escopo do negócio.
    
    LÓGICA:
    1. Se menciona algo que oferecemos → IN SCOPE
    2. Se menciona algo que NÃO oferecemos → OUT OF SCOPE
    3. Se menciona categoria de serviço não relacionada → OUT OF SCOPE
    4. Se menciona tópico universalmente proibido → OUT OF SCOPE
    5. Caso contrário → IN SCOPE (benefício da dúvida)
    """
    
    # Verifica se scope está habilitado
    scope_config = settings.get("scope", {})
    is_enabled = scope_config.get("enabled", True) if scope_config else settings.get("scope_enabled", True)
    
    if not is_enabled:
        return True, None
    
    msg = normalize_text(message)
    
    # Extrai keywords do tenant
    in_scope_keywords, out_of_scope_keywords, out_of_scope_message = extract_scope_keywords(settings)
    
    logger.debug(f"Scope check - In: {in_scope_keywords[:5]}... Out: {out_of_scope_keywords[:5]}...")
    
    # 1. Verifica tópicos universalmente proibidos
    for forbidden in UNIVERSAL_FORBIDDEN_TOPICS:
        if forbidden in msg:
            logger.info(f"Scope: Tópico proibido detectado: {forbidden}")
            return False, out_of_scope_message
    
    # 2. Verifica se menciona algo que NÃO oferecemos (OUT OF SCOPE) - PRIORIDADE!
    for keyword in out_of_scope_keywords:
        if keyword in msg:
            logger.info(f"Scope: Keyword fora do escopo detectada: {keyword}")
            return False, out_of_scope_message
    
    # 3. Verifica se menciona algo que oferecemos (IN SCOPE)
    for keyword in in_scope_keywords:
        if keyword in msg:
            logger.debug(f"Scope: Keyword do negócio detectada: {keyword}")
            return True, None
    
    # 4. Detecta categoria de serviço
    detected_categories = detect_service_category(message)
    
    if detected_categories:
        # Verifica se a categoria detectada está no nicho do tenant
        niche = settings.get("basic", {}).get("niche") or settings.get("niche", "services")
        allowed_categories = get_allowed_categories_for_niche(niche)
        
        # Se o nicho é "services", é genérico - permite mais coisas
        if niche == "services":
            # Mas ainda bloqueia categorias claramente não relacionadas
            # se o tenant tiver configurado produtos específicos
            if in_scope_keywords:
                # Tem produtos configurados, então devemos ser mais restritivos
                # Verifica se alguma categoria detectada é permitida
                for cat in detected_categories:
                    if cat in ["limpeza", "jardinagem", "beleza", "construcao", "automotivo", "pet"]:
                        # Categorias que normalmente não são "serviços genéricos"
                        # Se não tem keyword do negócio que match, bloqueia
                        logger.info(f"Scope: Categoria '{cat}' detectada, verificando se é do negócio...")
                        # Se chegou aqui é porque não achou keyword do negócio
                        return False, out_of_scope_message
        else:
            # Nicho específico
            for cat in detected_categories:
                if cat not in allowed_categories:
                    logger.info(f"Scope: Categoria '{cat}' não permitida para nicho '{niche}'")
                    return False, out_of_scope_message
    
    # 5. Se chegou aqui, dá o benefício da dúvida
    return True, None


# ========================================================
# PRICE SEMANTIC DETECTOR
# ========================================================

def detect_price_semantics(message: str) -> bool:
    """
    Identifica tentativas de perguntar preço MESMO disfarçadas.
    Inclui variações, abreviações, números com R$, etc.
    """
    msg = normalize_text(message)

    patterns = [
        r"\br\$\s?\d+",           # R$ 200
        r"\$\$+",                 # $$?
        r"preco",                 # preço (normalizado)
        r"valor",                 # valor?
        r"quanto",                # quanto fica / quanto é
        r"custa",                 # custa quanto
        r"caro|barato",           # mais barato
        r"faixa.{0,10}preco",     # faixa de preço
        r"media.{0,10}preco",     # média de preço
        r"aproximad[oa]",         # valor aproximado
        r"tabela.{0,10}precos?",  # tabela de preços
        r"orcamento",             # orçamento
        r"\d+\s?reais",           # 100 reais
        r"investimento",          # investimento (eufemismo para preço)
        r"condicoes.{0,10}pagamento",  # condições de pagamento
        r"parcela",               # parcela
        r"a vista",               # à vista
    ]

    return any(re.search(p, msg) for p in patterns)


def check_price_questions(message: str, settings: dict) -> Optional[str]:
    """
    Verifica se é uma pergunta sobre preço.
    IMPORTANTE: Só deve ser chamado DEPOIS do scope check!
    """
    if detect_price_semantics(message):
        # Pega mensagem customizada ou usa default
        guardrails = settings.get("guardrails", {})
        price_guard = guardrails.get("price_guard", {})
        
        if price_guard.get("enabled", True) == False:
            return None
        
        return (
            price_guard.get("message") or
            settings.get("price_guard_message") or
            DEFAULT_PRICE_MESSAGE
        )

    return None


# ========================================================
# INSISTENCE GUARD
# ========================================================

def check_insistence(message: str, settings: dict) -> Optional[str]:
    """Detecta insistência em obter preço."""
    
    # Verifica se está habilitado
    guardrails = settings.get("guardrails", {})
    insist_guard = guardrails.get("insist_guard", {})
    
    if insist_guard.get("enabled", True) == False:
        return None

    triggers = [
        "só uma média",
        "não precisa ser exato",
        "só para eu ter uma noção",
        "só para ter uma ideia",
        "aproximado",
        "mais barato ou mais caro",
        "não quero perder tempo",
        "só me diz",
        "só confirma",
        "me passa só",
        "pelo menos uma ideia",
        "uma faixa",
        "por cima",
        "por baixo",
        "mais ou menos",
        "na faixa de",
        "em torno de",
        "me dá uma base",
        "me dá um norte",
    ]

    msg = normalize_text(message)

    if any(normalize_text(t) in msg for t in triggers):
        return (
            insist_guard.get("message") or
            settings.get("insistence_guard_message") or
            DEFAULT_INSISTENCE_MESSAGE
        )

    return None


# ========================================================
# MESSAGE LIMIT
# ========================================================

def check_message_limit(message_count: int, settings: dict) -> Tuple[bool, Optional[str]]:
    """Verifica se atingiu limite de mensagens."""
    
    # Novo formato
    handoff_config = settings.get("handoff", {})
    max_msg = handoff_config.get("max_messages_before_handoff") or settings.get("max_messages_before_handoff", 15)
    
    if message_count >= max_msg:
        return True, "message_limit"
    
    return False, None


# ========================================================
# MASTER RUNNER (ORDEM CORRIGIDA!)
# ========================================================

def run_ai_guards(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
) -> dict:
    """
    Executa todos os guards na ORDEM CORRETA.
    
    ORDEM CRÍTICA:
    1. Business Hours
    2. FAQ
    3. SCOPE (antes de preço!)
    4. Price Guard
    5. Insistence Guard
    6. Message Limit
    """

    result = {
        "can_respond": True,
        "response": None,
        "reason": None,
        "force_handoff": False,
    }
    
    logger.debug(f"Running guards for message: {message[:50]}...")

    # 1 — Business Hours
    is_open, msg = check_business_hours(settings)
    if not is_open:
        logger.info("Guard triggered: out_of_hours")
        return {
            "can_respond": False,
            "response": msg,
            "reason": "out_of_hours",
            "force_handoff": False
        }

    # 2 — FAQ (resposta rápida se tiver)
    faq = check_faq(message, settings)
    if faq:
        logger.info("Guard triggered: faq")
        return {
            "can_respond": True,  # FAQ permite responder, só injeta contexto
            "response": faq,
            "reason": "faq",
            "force_handoff": False
        }

    # 3 — SCOPE GUARD (CRÍTICO - ANTES DO PREÇO!)
    in_scope, scope_msg = check_scope(message, settings)
    if not in_scope:
        logger.info("Guard triggered: out_of_scope")
        return {
            "can_respond": False,
            "response": scope_msg,
            "reason": "out_of_scope",
            "force_handoff": False
        }

    # 4 — PRICE GUARD (só se estiver no escopo)
    price = check_price_questions(message, settings)
    if price:
        logger.info("Guard triggered: price_block")
        return {
            "can_respond": False,
            "response": price,
            "reason": "price_block",
            "force_handoff": False
        }

    # 5 — INSISTENCE GUARD
    insist = check_insistence(message, settings)
    if insist:
        logger.info("Guard triggered: insistence_block")
        return {
            "can_respond": False,
            "response": insist,
            "reason": "insistence_block",
            "force_handoff": False
        }

    # 6 — Limite de mensagens (não para leads quentes)
    if lead_qualification not in ["quente", "hot"]:
        limit_reached, reason = check_message_limit(message_count, settings)
        if limit_reached:
            logger.info("Guard triggered: message_limit")
            return {
                "can_respond": False,
                "response": None,
                "reason": "message_limit",
                "force_handoff": True
            }

    logger.debug("All guards passed")
    return result


async def run_ai_guards_async(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
    previous_messages: list = None,  # Para contexto futuro
) -> dict:
    """
    Versão assíncrona do runner de guards.
    Mantida para compatibilidade.
    """
    return run_ai_guards(
        message=message,
        message_count=message_count,
        settings=settings,
        lead_qualification=lead_qualification,
    )


# ========================================================
# HELPERS PARA DEBUG
# ========================================================

def analyze_message_scope(message: str, settings: dict) -> dict:
    """
    Analisa uma mensagem e retorna informações detalhadas sobre escopo.
    Útil para debug.
    """
    in_scope_keywords, out_of_scope_keywords, out_of_scope_message = extract_scope_keywords(settings)
    detected_categories = detect_service_category(message)
    msg = normalize_text(message)
    
    matched_in_scope = [kw for kw in in_scope_keywords if kw in msg]
    matched_out_scope = [kw for kw in out_of_scope_keywords if kw in msg]
    matched_forbidden = [t for t in UNIVERSAL_FORBIDDEN_TOPICS if t in msg]
    
    is_price_question = detect_price_semantics(message)
    
    niche = settings.get("basic", {}).get("niche") or settings.get("niche", "services")
    allowed_categories = get_allowed_categories_for_niche(niche)
    
    return {
        "normalized_message": msg,
        "niche": niche,
        "detected_categories": detected_categories,
        "allowed_categories": allowed_categories,
        "matched_in_scope": matched_in_scope,
        "matched_out_scope": matched_out_scope,
        "matched_forbidden": matched_forbidden,
        "is_price_question": is_price_question,
        "total_in_scope_keywords": len(in_scope_keywords),
        "total_out_scope_keywords": len(out_of_scope_keywords),
        "would_block_scope": bool(matched_out_scope) or bool(matched_forbidden) or any(c not in allowed_categories for c in detected_categories),
    }