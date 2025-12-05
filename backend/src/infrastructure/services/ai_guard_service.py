"""
SERVIÇO DE GUARDA DA IA - VELARIS EDITION
==========================================

Guards aprimorados para evitar:
- respostas indevidas
- erros do modelo ao lidar com preços
- conversas fora de escopo
- loops de insistência
- excesso de mensagens sem qualificação
"""

from datetime import datetime
from typing import Optional, Tuple
import pytz


# ========================================================
# Helper
# ========================================================

def get_current_day_name() -> str:
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
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
    day_config = business_hours.get(day_name, {})

    if not day_config.get("enabled", False):
        return False, settings.get("out_of_hours_message", "Estamos fora do horário de atendimento.")

    open_time = day_config.get("open", "")
    close_time = day_config.get("close", "")

    current_time = now.strftime("%H:%M")

    if open_time <= current_time <= close_time:
        return True, None

    return False, settings.get("out_of_hours_message", "Estamos fora do horário de atendimento.")


# ========================================================
# FAQ
# ========================================================

def check_faq(message: str, settings: dict) -> Optional[str]:
    if not settings.get("faq_enabled", True):
        return None

    faq_items = settings.get("faq_items", [])
    if not faq_items:
        return None

    message_lower = message.lower().strip()

    for item in faq_items:
        question = item.get("question", "").lower().strip()
        answer = item.get("answer", "")
        keywords = item.get("keywords", [])

        if question and question in message_lower:
            return answer

        if keywords:
            matches = sum(1 for kw in keywords if kw.lower() in message_lower)
            if matches >= 2 or (len(keywords) == 1 and matches == 1):
                return answer

    return None


# ========================================================
# OUT OF SCOPE
# ========================================================

async def check_scope(message: str, settings: dict, openai_check: bool = True) -> Tuple[bool, Optional[str]]:
    if not settings.get("scope_enabled", True):
        return True, None

    message_lower = message.lower()

    out_of_scope_topics = [
        "receita", "como fazer bolo", "piada", "história",
        "qual a capital", "horóscopo", "previsão do tempo",
        "código", "programação", "javascript", "python",
        "política", "eleição", "presidente",
    ]

    for topic in out_of_scope_topics:
        if topic in message_lower:
            return False, settings.get(
                "out_of_scope_message",
                "Consigo te ajudar melhor com informações sobre nossos produtos e serviços 😊"
            )

    return True, None


# ========================================================
# MESSAGE LIMIT
# ========================================================

def check_message_limit(message_count: int, settings: dict) -> Tuple[bool, Optional[str]]:
    max_messages = settings.get("max_messages_before_handoff", 15)

    if message_count >= max_messages:
        return True, "message_limit"

    return False, None


# ========================================================
# PRICE GUARD (NOVIDADE!)
# ========================================================

def check_price_questions(message: str, settings: dict) -> Optional[str]:
    """
    Impede que a IA tente responder valores.
    """
    gatilhos = [
        "preço", "valor", "quanto custa", "quanto é",
        "faixa de preço", "média de preço", "barato", "caro",
        "aproximado", "valores", "tabela de preços", "custo",
        "quanto fica", "quanto está", "qual o preço"
    ]

    texto = message.lower()

    if any(g in texto for g in gatilhos):

        resposta = (
            settings.get(
                "price_guard_message",
                "Para garantir que os valores estejam corretos e atualizados, "
                "quem informa preços é sempre nosso especialista. "
                "Me conta qual peça você está buscando e para qual data, "
                "que eu já encaminho o atendimento certinho! 😊"
            )
        )

        return resposta

    return None


# ========================================================
# INSISTÊNCIA GUARD (NOVIDADE!)
# ========================================================

def check_insistence(message: str) -> Optional[str]:
    """
    Quando o lead tenta driblar o preço ou pressiona demais.
    """
    triggers = [
        "me passa só uma média",
        "só para eu ter uma noção",
        "pode ser aproximado",
        "não precisa ser exato",
        "mais barato ou mais caro",
        "não quero perder tempo",
        "só me diz",
        "só confirma"
    ]

    msg = message.lower()

    if any(t in msg for t in triggers):
        return (
            "Eu entendo totalmente! Mas para evitar qualquer informação imprecisa, "
            "somente o especialista pode confirmar valores. "
            "Me diz qual peça chamou sua atenção e para qual data, que eu agilizo isso para você! 😉"
        )

    return None


# ========================================================
# EXECUÇÃO FINAL DOS GUARDS
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

    # 1. Horário
    is_open, closed_message = check_business_hours(settings)
    if not is_open:
        result["can_respond"] = False
        result["response"] = closed_message
        result["reason"] = "out_of_hours"
        return result

    # 2. FAQ
    faq_response = check_faq(message, settings)
    if faq_response:
        result["response"] = faq_response
        result["reason"] = "faq"
        return result

    # 3. PRICE GUARD (🔥 ESSENCIAL)
    price_block = check_price_questions(message, settings)
    if price_block:
        result["can_respond"] = False
        result["response"] = price_block
        result["reason"] = "price_guard"
        return result

    # 4. INSISTÊNCIA GUARD
    insist_block = check_insistence(message)
    if insist_block:
        result["can_respond"] = False
        result["response"] = insist_block
        result["reason"] = "insistence_guard"
        return result

    # 5. Limite de mensagens
    if lead_qualification != "quente":
        should_handoff, handoff_reason = check_message_limit(message_count, settings)
        if should_handoff:
            result["force_handoff"] = True
            result["reason"] = "message_limit"
            return result

    return result


async def run_ai_guards_async(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
) -> dict:

    result = run_ai_guards(message, message_count, settings, lead_qualification)

    if not result["can_respond"] or result["force_handoff"]:
        return result

    # Escopo
    is_in_scope, scope_message = await check_scope(message, settings)
    if not is_in_scope:
        result["response"] = scope_message
        result["reason"] = "out_of_scope"

    return result
