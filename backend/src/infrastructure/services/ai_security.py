"""
SEGURANÇA ANTI-ALUCINAÇÃO
=========================
Arquivo: backend/src/infrastructure/services/ai_security.py
"""

import re
from typing import Tuple


def build_security_instructions(
    company_name: str,
    scope_description: str,
    out_of_scope_message: str
) -> str:
    """Instruções de segurança para adicionar ao prompt"""
    
    return f"""

🔒 REGRAS DE SEGURANÇA - NUNCA VIOLE:

1. NUNCA mencione valores, preços ou custos
2. NUNCA mencione prazos de entrega ou disponibilidade específica
3. NUNCA invente especificações técnicas
4. Se não souber, seja HONESTO

ESCOPO DE {company_name}:
{scope_description}

QUANDO NÃO SOUBER:
Responda: "{out_of_scope_message}"

QUANDO TRANSFERIR:
- Cliente pergunta valores/preços
- Cliente quer fechar negócio
- Cliente pede para falar com alguém

EXEMPLOS ERRADOS:
❌ "Os valores ficam entre R$ 150 e R$ 600"
❌ "Entrega em 2 dias"
❌ "Temos 5 unidades disponíveis"

EXEMPLOS CORRETOS:
✅ "Para valores, posso conectar você com nossa equipe"
✅ "Gostaria de falar com um especialista?"
"""


def is_response_safe(response: str) -> bool:
    """Verifica se resposta contém alucinação"""
    
    response_lower = response.lower()
    
    critical_patterns = [
        r'r\$\s*\d+',                          # R$ 150
        r'\d+[\d\.,]*\s*reais?',               # 150 reais
        r'(?:custa|preço|valor).*\d+',         # custa 150
        r'entre.*\d+.*e.*\d+.*reais?',         # entre 100 e 200
        r'entrega\s+em\s+\d+\s+dias?',         # entrega em 2 dias
        r'(?:temos|tenho)\s+\d+\s+unidades?',  # temos 5 unidades
    ]
    
    for pattern in critical_patterns:
        if re.search(pattern, response_lower):
            return False
    
    return True


def sanitize_response(response: str, fallback_message: str) -> Tuple[str, bool]:
    """
    Valida resposta. Se insegura, retorna fallback.
    Returns: (resposta_final, foi_bloqueada)
    """
    if is_response_safe(response):
        return response, False
    else:
        return fallback_message, True


def should_handoff(user_message: str, ai_response: str) -> dict:
    """Detecta se deve fazer handoff"""
    
    user_lower = user_message.lower()
    response_lower = ai_response.lower()
    
    handoff_keywords = [
        'quanto custa', 'preço', 'valor', 'orçamento',
        'quero comprar', 'fechar', 'contratar',
        'falar com', 'atendente',
    ]
    
    for keyword in handoff_keywords:
        if keyword in user_lower:
            return {"should_handoff": True, "reason": f"Perguntou sobre: {keyword}"}
    
    if 'conectar' in response_lower or 'transferir' in response_lower:
        return {"should_handoff": True, "reason": "IA sugeriu transferência"}
    
    return {"should_handoff": False, "reason": None}