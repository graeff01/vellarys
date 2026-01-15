"""
Módulo de Segurança para Processamento de Mensagens
=====================================================

Este módulo encapsula toda a lógica de segurança relacionada
à análise e ao tratamento de mensagens recebidas, como
sanitização, detecção de spam e verificação de ameaças.
"""
import logging
from typing import List, Dict, Optional

from src.config import get_settings
from src.infrastructure.services.ai_security import is_prompt_safe

logger = logging.getLogger(__name__)
settings = get_settings()


def sanitize_message_content(content: str) -> str:
    """Remove conteúdo potencialmente perigoso ou muito longo."""
    if not content:
        return ""
    content = content[: settings.max_message_length]
    content = content.replace('\\0', '').replace('\\r', '')
    return content.strip()


def check_spam_repetition(history: List[Dict[str, str]], message_count: int) -> Optional[str]:
    """
    Verifica se o usuário está repetindo a mesma mensagem.
    Retorna uma mensagem de resposta se o spam for detectado, senão None.
    """
    if message_count <= 3:
        return None

    # Pega as últimas 3 mensagens do usuário
    recent_user_msgs = [
        msg.get("content", "") for msg in history[-6:]
        if msg.get("role") == "user"
    ][-3:]

    # Verifica se está repetindo a mesma coisa 3x
    if len(recent_user_msgs) == 3 and recent_user_msgs[0] == recent_user_msgs[1] == recent_user_msgs[2]:
        logger.warning("⚠️ Detectado spam por repetição.")
        return "Percebi que você está repetindo a mesma mensagem. Posso te ajudar com algo específico?"

    return None


def check_jailbreak_attempt(content: str, company_name: str) -> Optional[str]:
    """
    Verifica se a mensagem é uma tentativa de jailbreak.
    Retorna uma resposta segura se for detectada, senão None.
    """
    if not is_prompt_safe(content):
        logger.warning("🚨 Tentativa de Jailbreak detectada!")
        return f"Desculpe, não entendi perfeitamente. Pode reformular? Sou um assistente da {company_name} focado em imóveis."
    return None
