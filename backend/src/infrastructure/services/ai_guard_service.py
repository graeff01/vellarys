"""
SERVIÇO DE GUARDA DA IA
========================

Verifica condições antes da IA responder:
- Horário de atendimento
- Escopo (se a pergunta é sobre o negócio)
- FAQ (respostas prontas)
- Limite de mensagens
"""

from datetime import datetime
from typing import Optional, Tuple
import pytz


def get_current_day_name() -> str:
    """Retorna o nome do dia atual em inglês."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return days[datetime.now().weekday()]


def check_business_hours(settings: dict, timezone: str = "America/Sao_Paulo") -> Tuple[bool, Optional[str]]:
    """
    Verifica se está dentro do horário de atendimento.
    
    Returns:
        (is_open, message_if_closed)
    """
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
    
    # Dia não habilitado
    if not day_config.get("enabled", False):
        return False, settings.get("out_of_hours_message", "Estamos fora do horário de atendimento.")
    
    # Verifica horário
    open_time = day_config.get("open", "")
    close_time = day_config.get("close", "")
    
    if not open_time or not close_time:
        return True, None
    
    try:
        current_time = now.strftime("%H:%M")
        
        if open_time <= current_time <= close_time:
            return True, None
        else:
            return False, settings.get("out_of_hours_message", "Estamos fora do horário de atendimento.")
    except:
        return True, None


def check_faq(message: str, settings: dict) -> Optional[str]:
    """
    Verifica se a mensagem corresponde a alguma pergunta do FAQ.
    
    Returns:
        Resposta do FAQ ou None
    """
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
        
        # Verifica match direto
        if question and question in message_lower:
            return answer
        
        # Verifica keywords
        if keywords:
            matches = sum(1 for kw in keywords if kw.lower() in message_lower)
            if matches >= 2 or (len(keywords) == 1 and matches == 1):
                return answer
    
    return None


async def check_scope(message: str, settings: dict, openai_check: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Verifica se a mensagem está dentro do escopo do negócio.
    
    Returns:
        (is_in_scope, message_if_out_of_scope)
    """
    if not settings.get("scope_enabled", True):
        return True, None
    
    scope_description = settings.get("scope_description", "")
    
    if not scope_description:
        return True, None
    
    # Lista de tópicos claramente fora de escopo
    out_of_scope_topics = [
        "receita de", "como fazer bolo", "piada", "conte uma história",
        "escreva um poema", "qual a capital", "quem foi", "história do brasil",
        "me ajuda com programação", "código python", "javascript",
        "previsão do tempo", "horóscopo", "resultado do jogo",
        "política", "eleição", "presidente",
    ]
    
    message_lower = message.lower()
    
    for topic in out_of_scope_topics:
        if topic in message_lower:
            return False, settings.get(
                "out_of_scope_message", 
                "Desculpe, não tenho informações sobre isso. Posso ajudar com dúvidas sobre nossos produtos e serviços!"
            )
    
    return True, None


def check_message_limit(message_count: int, settings: dict) -> Tuple[bool, Optional[str]]:
    """
    Verifica se atingiu o limite de mensagens sem qualificação.
    
    Returns:
        (should_force_handoff, reason)
    """
    max_messages = settings.get("max_messages_before_handoff", 15)
    
    if message_count >= max_messages:
        return True, "message_limit"
    
    return False, None


def run_ai_guards(
    message: str,
    message_count: int,
    settings: dict,
    lead_qualification: str = "frio",
) -> dict:
    """
    Executa todas as verificações de guarda da IA.
    
    Returns:
        {
            "can_respond": True/False,
            "response": "resposta automática se houver",
            "reason": "motivo se bloqueado",
            "force_handoff": True/False,
        }
    """
    result = {
        "can_respond": True,
        "response": None,
        "reason": None,
        "force_handoff": False,
    }
    
    # 1. Verifica horário de atendimento
    is_open, closed_message = check_business_hours(settings)
    if not is_open:
        result["can_respond"] = False
        result["response"] = closed_message
        result["reason"] = "out_of_hours"
        return result
    
    # 2. Verifica FAQ
    faq_response = check_faq(message, settings)
    if faq_response:
        result["response"] = faq_response
        result["reason"] = "faq"
        # Ainda permite a IA complementar se necessário
        return result
    
    # 3. Verifica limite de mensagens (só se não for quente)
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
    """
    Versão assíncrona com verificação de escopo via IA.
    """
    result = run_ai_guards(message, message_count, settings, lead_qualification)
    
    # Se já bloqueou por outro motivo, retorna
    if not result["can_respond"] or result["force_handoff"]:
        return result
    
    # 4. Verifica escopo
    is_in_scope, scope_message = await check_scope(message, settings)
    if not is_in_scope:
        result["response"] = scope_message
        result["reason"] = "out_of_scope"
        # Ainda permite responder com a mensagem de escopo
        return result
    
    return result