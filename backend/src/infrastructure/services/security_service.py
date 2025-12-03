"""
SECURITY SERVICE - Serviço de Segurança
========================================

Proteção completa contra:
- Prompt Injection
- Comandos maliciosos
- Exposição de dados internos
- Manipulação da IA

CRÍTICO: Este serviço DEVE ser chamado ANTES de qualquer processamento de mensagem.
"""

import re
from typing import Tuple, List, Optional
from datetime import datetime
import hashlib


class ThreatLevel:
    """Níveis de ameaça detectados."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType:
    """Tipos de ameaças."""
    PROMPT_INJECTION = "prompt_injection"
    TOOL_EXPOSURE = "tool_exposure"
    DATA_EXTRACTION = "data_extraction"
    SYSTEM_MANIPULATION = "system_manipulation"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    SPAM = "spam"
    FLOODING = "flooding"


class SecurityCheckResult:
    """Resultado da verificação de segurança."""
    
    def __init__(
        self,
        is_safe: bool,
        threat_level: str,
        threat_type: Optional[str] = None,
        matched_pattern: Optional[str] = None,
        sanitized_content: Optional[str] = None,
        should_block: bool = False,
        log_required: bool = False,
        message: str = ""
    ):
        self.is_safe = is_safe
        self.threat_level = threat_level
        self.threat_type = threat_type
        self.matched_pattern = matched_pattern
        self.sanitized_content = sanitized_content
        self.should_block = should_block
        self.log_required = log_required
        self.message = message
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "threat_level": self.threat_level,
            "threat_type": self.threat_type,
            "matched_pattern": self.matched_pattern,
            "should_block": self.should_block,
            "log_required": self.log_required,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# PADRÕES DE DETECÇÃO DE AMEAÇAS
# =============================================================================

# Padrões de Prompt Injection (CRÍTICO)
PROMPT_INJECTION_PATTERNS = [
    # Tentativas de mudar o papel/comportamento
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
    r"ignore\s+everything\s+(above|before)",
    r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|programming)",
    r"forget\s+(all\s+)?(your\s+)?(instructions?|rules?|training)",
    r"you\s+are\s+now\s+(a|an|the)",
    r"act\s+as\s+(if\s+you\s+are|a|an)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"roleplay\s+as",
    r"switch\s+to\s+(\w+)\s+mode",
    r"enter\s+(\w+)\s+mode",
    r"enable\s+(\w+)\s+mode",
    r"activate\s+(\w+)\s+mode",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"god\s+mode",
    r"admin\s+mode",
    r"sudo\s+mode",
    r"root\s+access",
    
    # Tentativas de extrair system prompt
    r"(show|tell|reveal|display|print|output|repeat|what\s+is)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules?|programming)",
    r"what\s+are\s+your\s+(initial\s+)?(instructions?|rules?|directives?)",
    r"(copy|paste|print)\s+(your\s+)?(system|initial)\s+(prompt|message)",
    r"reveal\s+(hidden|secret)\s+(instructions?|prompts?)",
    
    # Tentativas em português
    r"ignore\s+(todas?\s+)?(as\s+)?(instruções|regras)\s+(anteriores|acima)",
    r"esqueça\s+(todas?\s+)?(as\s+)?(suas?\s+)?(instruções|regras)",
    r"desconsidere\s+(tudo|todas?)\s+(acima|anterior)",
    r"mostre\s+(seu|o)\s+(prompt|sistema)",
    r"qual\s+(é\s+)?(seu|o)\s+prompt",
    r"revele\s+(suas?\s+)?(instruções|regras)",
    r"finja\s+(ser|que\s+(você\s+)?é)",
    r"atue\s+como\s+(se\s+fosse|um|uma)",
    r"aja\s+como\s+(se\s+fosse|um|uma)",
    r"mude\s+(para\s+)?(modo|papel)",
]

# Padrões de exposição de tools/funções (CRÍTICO)
TOOL_EXPOSURE_PATTERNS = [
    # Inglês
    r"(list|show|tell|what\s+are|display|enumerate)\s+(all\s+)?(your\s+)?(tools?|functions?|capabilities|abilities|features|commands?|methods?|apis?)",
    r"what\s+(tools?|functions?|commands?|apis?)\s+(do\s+you\s+have|are\s+available|can\s+you\s+use)",
    r"(available|accessible)\s+(tools?|functions?|commands?)",
    r"(execute|run|call)\s+(function|tool|command|api)",
    r"function\s+(call|list|names?)",
    r"api\s+(endpoints?|list|calls?)",
    
    # Português
    r"(liste|mostre|quais\s+são|exiba|diga)\s+(todas?\s+)?(as\s+)?(suas?\s+)?(ferramentas?|funções|capacidades|habilidades|comandos?|tools?)",
    r"(quais?|que)\s+(ferramentas?|funções|comandos?|tools?)\s+(você\s+)?(tem|possui|usa|dispõe)",
    r"(ferramentas?|funções|comandos?)\s+(disponíveis?|acessíveis?)",
    r"(execute|rode|chame|acione)\s+(função|ferramenta|comando|tool)",
]

# Padrões de extração de dados (ALTO)
DATA_EXTRACTION_PATTERNS = [
    # Inglês
    r"(show|list|give|tell|display)\s+(me\s+)?(all\s+)?(users?|customers?|clients?|leads?|data|records?|database)",
    r"(dump|export|extract)\s+(all\s+)?(data|database|records?|users?)",
    r"select\s+\*\s+from",
    r"(access|read|get)\s+(other\s+)?(users?|tenants?|customers?)\s+(data|info|records?)",
    r"(bypass|skip)\s+(authentication|auth|login|security)",
    
    # Português
    r"(mostre|liste|dê|exiba)\s+(todos?\s+)?(os\s+)?(usuários?|clientes?|leads?|dados?|registros?)",
    r"(exporte|extraia|dump)\s+(todos?\s+)?(os\s+)?(dados?|banco|registros?)",
    r"(acesse|leia|busque)\s+(dados?\s+)?(de\s+)?(outros?\s+)?(usuários?|clientes?|tenants?)",
    r"(pule|ignore|bypass)\s+(autenticação|login|segurança)",
]

# Padrões de manipulação do sistema (ALTO)
SYSTEM_MANIPULATION_PATTERNS = [
    # Comandos de sistema
    r"(execute|run|eval|exec)\s*\(",
    r"os\.(system|popen|exec)",
    r"subprocess\.",
    r"import\s+(os|sys|subprocess)",
    r"__import__",
    r"\beval\b",
    r"\bexec\b",
    r"shell\s*=\s*true",
    r"rm\s+-rf",
    r"sudo\s+",
    r"chmod\s+",
    r"curl\s+",
    r"wget\s+",
    
    # SQL Injection
    r";\s*(drop|delete|truncate|alter|update|insert)\s+",
    r"'\s*(or|and)\s+'?\d+'\s*=\s*'?\d+",
    r"union\s+(all\s+)?select",
    r"--\s*$",
    r"/\*.*\*/",
]

# Padrões de XSS
XSS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"<svg[^>]*onload",
]

# Padrões de spam/flooding
SPAM_PATTERNS = [
    r"(.)\1{10,}",  # Caractere repetido 10+ vezes
    r"(\b\w+\b)(\s+\1){5,}",  # Palavra repetida 5+ vezes
]

# Palavras-chave suspeitas (baixa prioridade, apenas log)
SUSPICIOUS_KEYWORDS = [
    "hack", "hacker", "exploit", "vulnerability", "injection",
    "bypass", "crack", "malware", "virus", "trojan",
    "password", "credential", "token", "secret", "key",
]


def check_prompt_injection(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se há tentativa de prompt injection.
    
    Returns:
        (is_injection, matched_pattern)
    """
    content_lower = content.lower()
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True, pattern
    
    return False, None


def check_tool_exposure(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se há tentativa de expor tools/funções.
    
    Returns:
        (is_attempt, matched_pattern)
    """
    content_lower = content.lower()
    
    for pattern in TOOL_EXPOSURE_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True, pattern
    
    return False, None


def check_data_extraction(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se há tentativa de extração de dados.
    
    Returns:
        (is_attempt, matched_pattern)
    """
    content_lower = content.lower()
    
    for pattern in DATA_EXTRACTION_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True, pattern
    
    return False, None


def check_system_manipulation(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se há tentativa de manipulação do sistema.
    
    Returns:
        (is_attempt, matched_pattern)
    """
    for pattern in SYSTEM_MANIPULATION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, pattern
    
    return False, None


def check_xss(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se há tentativa de XSS.
    
    Returns:
        (is_attempt, matched_pattern)
    """
    for pattern in XSS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, pattern
    
    return False, None


def check_spam(content: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se é spam/flooding.
    
    Returns:
        (is_spam, matched_pattern)
    """
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, content):
            return True, pattern
    
    return False, None


def check_suspicious_keywords(content: str) -> List[str]:
    """
    Verifica palavras-chave suspeitas (para logging).
    
    Returns:
        Lista de keywords encontradas
    """
    content_lower = content.lower()
    found = []
    
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in content_lower:
            found.append(keyword)
    
    return found


def sanitize_input(content: str) -> str:
    """
    Sanitiza input removendo caracteres perigosos.
    
    Returns:
        Conteúdo sanitizado
    """
    # Remove caracteres de controle (exceto newline e tab)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    
    # Remove sequências de escape ANSI
    sanitized = re.sub(r'\x1b\[[0-9;]*m', '', sanitized)
    
    # Limita tamanho (proteção contra DoS)
    max_length = 4000  # 4k caracteres
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Remove múltiplos espaços/newlines consecutivos
    sanitized = re.sub(r'\n{4,}', '\n\n\n', sanitized)
    sanitized = re.sub(r' {4,}', '   ', sanitized)
    
    return sanitized.strip()


def run_security_check(
    content: str,
    sender_id: str = None,
    tenant_id: int = None,
) -> SecurityCheckResult:
    """
    Executa verificação de segurança completa.
    
    DEVE ser chamado ANTES de qualquer processamento.
    
    Returns:
        SecurityCheckResult com status e detalhes
    """
    
    # Sanitiza primeiro
    sanitized = sanitize_input(content)
    
    # 1. Verifica prompt injection (CRÍTICO)
    is_injection, pattern = check_prompt_injection(sanitized)
    if is_injection:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.CRITICAL,
            threat_type=ThreatType.PROMPT_INJECTION,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=True,
            log_required=True,
            message="Tentativa de prompt injection detectada"
        )
    
    # 2. Verifica exposição de tools (CRÍTICO)
    is_tool_exposure, pattern = check_tool_exposure(sanitized)
    if is_tool_exposure:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.CRITICAL,
            threat_type=ThreatType.TOOL_EXPOSURE,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=True,
            log_required=True,
            message="Tentativa de exposição de ferramentas detectada"
        )
    
    # 3. Verifica extração de dados (ALTO)
    is_data_extract, pattern = check_data_extraction(sanitized)
    if is_data_extract:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.HIGH,
            threat_type=ThreatType.DATA_EXTRACTION,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=True,
            log_required=True,
            message="Tentativa de extração de dados detectada"
        )
    
    # 4. Verifica manipulação do sistema (ALTO)
    is_manipulation, pattern = check_system_manipulation(sanitized)
    if is_manipulation:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.HIGH,
            threat_type=ThreatType.SYSTEM_MANIPULATION,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=True,
            log_required=True,
            message="Tentativa de manipulação do sistema detectada"
        )
    
    # 5. Verifica XSS (MÉDIO)
    is_xss, pattern = check_xss(sanitized)
    if is_xss:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.MEDIUM,
            threat_type=ThreatType.XSS_ATTEMPT,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=True,
            log_required=True,
            message="Tentativa de XSS detectada"
        )
    
    # 6. Verifica spam (BAIXO)
    is_spam, pattern = check_spam(sanitized)
    if is_spam:
        return SecurityCheckResult(
            is_safe=False,
            threat_level=ThreatLevel.LOW,
            threat_type=ThreatType.SPAM,
            matched_pattern=pattern,
            sanitized_content=sanitized,
            should_block=False,  # Não bloqueia, mas loga
            log_required=True,
            message="Possível spam detectado"
        )
    
    # 7. Verifica keywords suspeitas (apenas log)
    suspicious = check_suspicious_keywords(sanitized)
    if suspicious:
        return SecurityCheckResult(
            is_safe=True,
            threat_level=ThreatLevel.LOW,
            threat_type=None,
            matched_pattern=", ".join(suspicious),
            sanitized_content=sanitized,
            should_block=False,
            log_required=True,
            message=f"Palavras suspeitas detectadas: {', '.join(suspicious)}"
        )
    
    # Tudo OK
    return SecurityCheckResult(
        is_safe=True,
        threat_level=ThreatLevel.SAFE,
        threat_type=None,
        matched_pattern=None,
        sanitized_content=sanitized,
        should_block=False,
        log_required=False,
        message=""
    )


def get_safe_response_for_threat(threat_type: str) -> str:
    """
    Retorna resposta segura para cada tipo de ameaça.
    Não revela que detectamos a ameaça.
    """
    
    responses = {
        ThreatType.PROMPT_INJECTION: (
            "Desculpe, não entendi sua mensagem. "
            "Posso ajudar com informações sobre nossos produtos e serviços! "
            "O que você gostaria de saber?"
        ),
        ThreatType.TOOL_EXPOSURE: (
            "Sou um assistente virtual e estou aqui para ajudar com suas dúvidas! "
            "Como posso ajudar você hoje?"
        ),
        ThreatType.DATA_EXTRACTION: (
            "Por questões de privacidade, não posso compartilhar essas informações. "
            "Posso ajudar com algo sobre nossos produtos ou serviços?"
        ),
        ThreatType.SYSTEM_MANIPULATION: (
            "Hmm, não consegui processar essa mensagem. "
            "Poderia reformular sua pergunta?"
        ),
        ThreatType.JAILBREAK_ATTEMPT: (
            "Sou um assistente focado em ajudar com nossos produtos e serviços. "
            "Como posso ajudar?"
        ),
        ThreatType.XSS_ATTEMPT: (
            "Desculpe, houve um problema com sua mensagem. "
            "Por favor, tente novamente com texto simples."
        ),
        ThreatType.SPAM: (
            "Por favor, envie sua mensagem de forma mais clara para que eu possa ajudar!"
        ),
    }
    
    return responses.get(
        threat_type,
        "Desculpe, não consegui processar sua mensagem. Como posso ajudar?"
    )


def hash_sensitive_data(data: str) -> str:
    """
    Cria hash de dados sensíveis para logging seguro.
    """
    return hashlib.sha256(data.encode()).hexdigest()[:16]