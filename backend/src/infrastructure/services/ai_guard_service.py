"""
SERVIÇO DE GUARDA DA IA - VELARIS ULTRA-ROBUST EDITION
======================================================

🔥 Objetivo:
Evitar qualquer resposta indevida da IA antes de chegar ao modelo,
garantindo ZERO erros 500 e ZERO respostas sobre preços.

⚙️ Recursos:
- Business Hours
- FAQ
- Price Guard (ultracompleto)
- Insistence Guard (reforçado)
- Price Semantics Detect (NOVIDADE)
- Message Limit
- Scope Guard
"""

from datetime import datetime
from typing import Optional, Tuple
import pytz
import re


# ========================================================
# Utils
# ========================================================

def get_current_day_name() -> str:
    days = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]
    return days[datetime.now().weekday()]


# ========================================================
# BUSINESS HOURS
# ========================================================

def check_business_hours(settings: dict, timezone: str = "America/Sao_Paulo") -> Tuple[bool, Optional[str]]:
    if not settings.get("business_hours_enabled", False):
        return True, None

    business_hours = settings.get("business_hours", {})

    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except:
        now = datetime.now()

    day_name = get_current_day_name()
    config = business_hours.get(day_name, {})

    if not config.get("enabled", False):
        return False, settings.get("out_of_hours_message",
                                   "Estamos fora do horário de atendimento.")

    open_time = config.get("open", "")
    close_time = config.get("close", "")

    current = now.strftime("%H:%M")

    if open_time <= current <= close_time:
        return True, None

    return False, settings.get("out_of_hours_message",
                               "Estamos fora do horário de atendimento.")


# ========================================================
# FAQ
# ========================================================

def check_faq(message: str, settings: dict) -> Optional[str]:
    if not settings.get("faq_enabled", True):
        return None

    faq = settings.get("faq_items", [])
    if not faq:
        return None

    msg = message.lower().strip()

    for item in faq:
        question = item.get("question", "").lower().strip()
        answer = item.get("answer", "")
        keywords = item.get("keywords", [])

        if question and question in msg:
            return answer

        if keywords:
            matches = sum(1 for kw in keywords if kw.lower() in msg)
            if matches >= 2 or (len(keywords) == 1 and matches == 1):
                return answer

    return None


# ========================================================
# PRICE SEMANTIC DETECTOR (NOVIDADE MUITO ROBUSTA)
# ========================================================

def detect_price_semantics(message: str) -> bool:
    """
    Identifica tentativas de perguntar preço MESMO disfarçadas.
    Inclui variações, abreviações, números com R$, emojis etc.
    """

    msg = message.lower()

    patterns = [
        r"\br\$ ?\d+",          # R$ 200
        r"\$\$+",               # $$?
        r"pre[cç]o",            # preco / preço
        r"valor",               # valor?
        r"quanto",              # quanto fica / quanto é
        r"custa",               # custa quanto
        r"caro|barato",         # mais barato
        r"faixa.*pre[cç]o",     # faixa de preço
        r"m[eé]dia.*pre[cç]o",  # média de preço
        r"aproximad[oa]",       # valor aproximado
        r"tabela.*pre[cç]os",
        r"acima.*\d+",
        r"abaixo.*\d+",
        r"pre[cç]o.*aproximado",
        r"pre[cç]o.*m[ée]dio",
        r"\d+ ?reais",
    ]

    return any(re.search(p, msg) for p in patterns)


# ========================================================
# PRICE GUARD
# ========================================================

def check_price_questions(message: str, settings: dict) -> Optional[str]:

    if detect_price_semantics(message):

        return settings.get(
            "price_guard_message",
            "Para garantir informações corretas e atualizadas, "
            "quem confirma valores é sempre o especialista. "
            "Me conta qual peça você está buscando e para qual data "
            "que eu já direciono certinho! 😊"
        )

    return None


# ========================================================
# INSISTÊNCIA GUARD
# ========================================================

def check_insistence(message: str) -> Optional[str]:

    triggers = [
        "só uma média",
        "não precisa ser exato",
        "só para eu ter uma noção",
        "aproximado",
        "mais barato ou mais caro",
        "não quero perder tempo",
        "só me diz",
        "só confirma",
        "me passa só",
        "pelo menos uma ideia",
        "uma faixa",
    ]

    msg = message.lower()

    if any(t in msg for t in triggers):

        return (
            "Eu entendo totalmente! Mas, para evitar qualquer informação incorreta, "
            "somente o especialista confirma valores. "
            "Me diz qual peça te interessa e a data do evento "
            "que eu agilizo o atendimento para você 😉"
        )

    return None


# ========================================================
# MESSAGE LIMIT
# ========================================================

def check_message_limit(message_count: int, settings: dict) -> Tuple[bool, Optional[str]]:
    max_msg = settings.get("max_messages_before_handoff", 15)
    if message_count >= max_msg:
        return True, "message_limit"
    return False, None


# ========================================================
# OUT OF SCOPE
# ========================================================

async def check_scope(message: str, settings: dict) -> Tuple[bool, Optional[str]]:
    if not settings.get("scope_enabled", True):
        return True, None

    msg = message.lower()

    forbidden = [
        "receita", "horóscopo", "programação", "python",
        "javascript", "código", "previsão do tempo",
        "política", "eleição", "presidente",
        "história do brasil", "universo", "poema",
    ]

    if any(t in msg for t in forbidden):
        return False, settings.get(
            "out_of_scope_message",
            "Posso te ajudar melhor com dúvidas sobre nossos produtos e serviços 😊"
        )

    return True, None


# ========================================================
# MASTER RUNNER
# ========================================================

def run_ai_guards(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
) -> dict:

    result = {
        "can_respond": True,
        "response": None,
        "reason": None,
        "force_handoff": False,
    }

    # 1 — Business Hours
    is_open, msg = check_business_hours(settings)
    if not is_open:
        return {"can_respond": False, "response": msg, "reason": "out_of_hours", "force_handoff": False}

    # 2 — FAQ
    faq = check_faq(message, settings)
    if faq:
        return {"can_respond": False, "response": faq, "reason": "faq", "force_handoff": False}

    # 3 — PRICE GUARD (prioridade absoluta)
    price = check_price_questions(message, settings)
    if price:
        return {"can_respond": False, "response": price, "reason": "price_block", "force_handoff": False}

    # 4 — INSISTENCE GUARD
    insist = check_insistence(message)
    if insist:
        return {"can_respond": False, "response": insist, "reason": "insistence_block", "force_handoff": False}

    # 5 — Limite de mensagens
    if lead_qualification != "quente":
        limit, reason = check_message_limit(message_count, settings)
        if limit:
            return {"can_respond": False, "response": None, "reason": "message_limit", "force_handoff": True}

    return result


async def run_ai_guards_async(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
):
    result = run_ai_guards(message, message_count, settings, lead_qualification)

    if not result["can_respond"] or result.get("force_handoff"):
        return result

    # 6 — Scope Guard
    in_scope, msg = await check_scope(message, settings)
    if not in_scope:
        result["response"] = msg
        result["reason"] = "out_of_scope"

    return result
