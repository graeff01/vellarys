"""
SERVIÇO DE HORÁRIO COMERCIAL
=============================

Responsável por:
1. Verificar se o tenant está em horário de atendimento
2. Retornar mensagem apropriada quando fora do horário
3. Calcular próximo horário de atendimento

Estrutura esperada em tenant.settings:
{
    "business_hours": {
        "enabled": True,
        "timezone": "America/Sao_Paulo",
        "schedule": {
            "monday": {"open": "08:00", "close": "18:00", "enabled": True},
            "tuesday": {"open": "08:00", "close": "18:00", "enabled": True},
            ...
        },
        "out_of_hours_message": "Olá! Nosso horário de atendimento é...",
        "out_of_hours_behavior": "message_only"  # message_only, queue, emergency
    }
}
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from src.domain.entities import Tenant

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Mapeamento dia da semana (Python) → chave do schedule
WEEKDAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

# Configuração padrão se não houver nas settings
DEFAULT_BUSINESS_HOURS = {
    "enabled": False,
    "timezone": "America/Sao_Paulo",
    "schedule": {
        "monday": {"open": "08:00", "close": "18:00", "enabled": True},
        "tuesday": {"open": "08:00", "close": "18:00", "enabled": True},
        "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
        "thursday": {"open": "08:00", "close": "18:00", "enabled": True},
        "friday": {"open": "08:00", "close": "18:00", "enabled": True},
        "saturday": {"open": "08:00", "close": "12:00", "enabled": False},
        "sunday": {"open": "", "close": "", "enabled": False},
    },
    "out_of_hours_message": None,
    "out_of_hours_behavior": "message_only",
}

# Mensagem padrão fora do horário
DEFAULT_OUT_OF_HOURS_MESSAGE = (
    "Olá! 😊 Recebi sua mensagem, mas estamos fora do horário de atendimento.\n\n"
    "Um especialista vai te retornar no próximo dia útil.\n\n"
    "Enquanto isso, fique à vontade para deixar sua dúvida!"
)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def parse_time(time_str: str) -> Optional[time]:
    """
    Converte string "HH:MM" para objeto time.
    Retorna None se inválido.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    
    try:
        parts = time_str.strip().split(":")
        if len(parts) >= 2:
            hour = int(parts[0])
            minute = int(parts[1])
            return time(hour, minute)
    except (ValueError, IndexError):
        pass
    
    return None


def get_timezone(tz_name: str) -> ZoneInfo:
    """
    Retorna ZoneInfo para o timezone especificado.
    Fallback para America/Sao_Paulo se inválido.
    """
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Timezone inválido: {tz_name}, usando America/Sao_Paulo")
        return ZoneInfo("America/Sao_Paulo")


def format_time_for_display(t: time) -> str:
    """Formata time para exibição amigável (ex: 8h, 18h)."""
    if t.minute == 0:
        return f"{t.hour}h"
    return f"{t.hour}h{t.minute:02d}"


# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================

def get_business_hours_config(tenant: Tenant) -> dict:
    """
    Extrai configuração de horário comercial do tenant.
    Retorna config padrão se não existir.
    """
    settings = tenant.settings or {}
    config = settings.get("business_hours", {})
    
    # Merge com defaults para garantir que todos os campos existem
    merged = {**DEFAULT_BUSINESS_HOURS, **config}
    
    # Garante que schedule tem todos os dias
    merged["schedule"] = {
        **DEFAULT_BUSINESS_HOURS["schedule"],
        **config.get("schedule", {}),
    }
    
    return merged


def is_within_business_hours(
    tenant: Tenant,
    check_time: datetime = None,
) -> Tuple[bool, Optional[str]]:
    """
    Verifica se está dentro do horário comercial do tenant.
    
    Args:
        tenant: Tenant para verificar
        check_time: Datetime para verificar (default: agora)
    
    Returns:
        Tuple[bool, Optional[str]]:
            - True/False se está dentro do horário
            - Motivo se estiver fora (para logging)
    
    Exemplos de retorno:
        (True, None) - Está no horário
        (False, "disabled") - Controle de horário desabilitado (considera dentro)
        (False, "day_disabled") - Dia não atende
        (False, "before_open") - Antes do horário de abertura
        (False, "after_close") - Após horário de fechamento
    """
    config = get_business_hours_config(tenant)
    
    # Se controle de horário não está habilitado, sempre permite
    if not config.get("enabled", False):
        return True, "disabled"
    
    # Pega timezone e hora atual
    tz = get_timezone(config.get("timezone", "America/Sao_Paulo"))
    
    if check_time:
        # Converte para o timezone do tenant
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=ZoneInfo("UTC"))
        now = check_time.astimezone(tz)
    else:
        now = datetime.now(tz)
    
    # Pega dia da semana
    weekday = now.weekday()
    day_key = WEEKDAY_MAP[weekday]
    
    # Pega configuração do dia
    schedule = config.get("schedule", {})
    day_config = schedule.get(day_key, {})
    
    # Se o dia não está habilitado, está fora do horário
    if not day_config.get("enabled", False):
        logger.debug(f"Tenant {tenant.slug}: {day_key} não está habilitado")
        return False, "day_disabled"
    
    # Parse dos horários
    open_time = parse_time(day_config.get("open", ""))
    close_time = parse_time(day_config.get("close", ""))
    
    if not open_time or not close_time:
        logger.warning(f"Tenant {tenant.slug}: horários inválidos para {day_key}")
        return True, "invalid_config"  # Na dúvida, permite
    
    current_time = now.time()
    
    # Verifica se está dentro do horário
    if current_time < open_time:
        logger.debug(f"Tenant {tenant.slug}: antes do horário ({current_time} < {open_time})")
        return False, "before_open"
    
    if current_time > close_time:
        logger.debug(f"Tenant {tenant.slug}: após horário ({current_time} > {close_time})")
        return False, "after_close"
    
    return True, None


def get_out_of_hours_message(
    tenant: Tenant,
    reason: str = None,
) -> str:
    """
    Retorna a mensagem apropriada para fora do horário.
    
    Args:
        tenant: Tenant
        reason: Motivo (day_disabled, before_open, after_close)
    
    Returns:
        Mensagem formatada para enviar ao lead
    """
    config = get_business_hours_config(tenant)
    settings = tenant.settings or {}
    
    # Tenta pegar mensagem customizada
    custom_message = config.get("out_of_hours_message")
    if custom_message and custom_message.strip():
        return custom_message.strip()
    
    # Monta mensagem inteligente baseada no motivo
    company_name = settings.get("basic", {}).get("company_name") or tenant.name
    
    # Pega próximo horário de atendimento
    next_open = get_next_business_opening(tenant)
    
    if next_open:
        next_open_str = format_next_opening(next_open)
        message = (
            f"Olá! 😊 Recebi sua mensagem.\n\n"
            f"No momento estamos fora do horário de atendimento da {company_name}.\n\n"
            f"Um especialista vai te retornar {next_open_str}.\n\n"
            f"Enquanto isso, fique à vontade para deixar suas dúvidas que responderemos assim que possível!"
        )
    else:
        message = (
            f"Olá! 😊 Recebi sua mensagem.\n\n"
            f"No momento estamos fora do horário de atendimento da {company_name}.\n\n"
            f"Um especialista vai te retornar no próximo dia útil.\n\n"
            f"Enquanto isso, fique à vontade para deixar suas dúvidas!"
        )
    
    return message


def get_next_business_opening(
    tenant: Tenant,
    from_time: datetime = None,
) -> Optional[datetime]:
    """
    Calcula o próximo horário de abertura.
    
    Args:
        tenant: Tenant
        from_time: A partir de quando calcular (default: agora)
    
    Returns:
        Datetime do próximo horário de abertura ou None
    """
    config = get_business_hours_config(tenant)
    
    if not config.get("enabled", False):
        return None
    
    tz = get_timezone(config.get("timezone", "America/Sao_Paulo"))
    
    if from_time:
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=ZoneInfo("UTC"))
        now = from_time.astimezone(tz)
    else:
        now = datetime.now(tz)
    
    schedule = config.get("schedule", {})
    
    # Procura nos próximos 7 dias
    for days_ahead in range(8):
        check_date = now + timedelta(days=days_ahead)
        weekday = check_date.weekday()
        day_key = WEEKDAY_MAP[weekday]
        day_config = schedule.get(day_key, {})
        
        if not day_config.get("enabled", False):
            continue
        
        open_time = parse_time(day_config.get("open", ""))
        if not open_time:
            continue
        
        # Monta datetime de abertura
        opening = check_date.replace(
            hour=open_time.hour,
            minute=open_time.minute,
            second=0,
            microsecond=0,
        )
        
        # Se é hoje mas já passou, pula para próximo dia
        if days_ahead == 0 and opening <= now:
            continue
        
        return opening
    
    return None


def format_next_opening(next_open: datetime) -> str:
    """
    Formata o próximo horário de abertura para texto amigável.
    
    Exemplos:
        - "amanhã às 8h"
        - "na segunda-feira às 8h"
        - "hoje às 14h" (se ainda for hoje)
    """
    now = datetime.now(next_open.tzinfo)
    
    # Diferença em dias
    days_diff = (next_open.date() - now.date()).days
    
    time_str = format_time_for_display(next_open.time())
    
    if days_diff == 0:
        return f"hoje às {time_str}"
    elif days_diff == 1:
        return f"amanhã às {time_str}"
    else:
        # Nome do dia da semana em português
        weekday_names = {
            0: "segunda-feira",
            1: "terça-feira",
            2: "quarta-feira",
            3: "quinta-feira",
            4: "sexta-feira",
            5: "sábado",
            6: "domingo",
        }
        day_name = weekday_names.get(next_open.weekday(), "")
        return f"na {day_name} às {time_str}"


def get_business_hours_summary(tenant: Tenant) -> str:
    """
    Retorna um resumo dos horários de funcionamento.
    Útil para incluir em respostas ou FAQ.
    
    Exemplo:
        "Segunda a sexta das 8h às 18h, sábado das 8h às 12h"
    """
    config = get_business_hours_config(tenant)
    
    if not config.get("enabled", False):
        return "Atendimento 24 horas"
    
    schedule = config.get("schedule", {})
    
    # Agrupa dias com mesmo horário
    groups = []
    current_group = None
    
    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_names_short = {
        "monday": "Seg",
        "tuesday": "Ter",
        "wednesday": "Qua",
        "thursday": "Qui",
        "friday": "Sex",
        "saturday": "Sáb",
        "sunday": "Dom",
    }
    
    for day_key in day_order:
        day_config = schedule.get(day_key, {})
        
        if not day_config.get("enabled", False):
            if current_group:
                groups.append(current_group)
                current_group = None
            continue
        
        open_time = day_config.get("open", "")
        close_time = day_config.get("close", "")
        hours = f"{open_time}-{close_time}"
        
        if current_group and current_group["hours"] == hours:
            current_group["days"].append(day_key)
        else:
            if current_group:
                groups.append(current_group)
            current_group = {"days": [day_key], "hours": hours}
    
    if current_group:
        groups.append(current_group)
    
    # Formata
    parts = []
    for group in groups:
        days = group["days"]
        hours = group["hours"]
        
        if len(days) == 1:
            day_str = day_names_short[days[0]]
        elif len(days) == 2:
            day_str = f"{day_names_short[days[0]]} e {day_names_short[days[1]]}"
        else:
            day_str = f"{day_names_short[days[0]]} a {day_names_short[days[-1]]}"
        
        open_t = parse_time(hours.split("-")[0])
        close_t = parse_time(hours.split("-")[1])
        
        if open_t and close_t:
            hours_str = f"das {format_time_for_display(open_t)} às {format_time_for_display(close_t)}"
        else:
            hours_str = hours
        
        parts.append(f"{day_str} {hours_str}")
    
    return ", ".join(parts) if parts else "Horário não configurado"


# =============================================================================
# CLASSE DE RESULTADO (para uso no process_message)
# =============================================================================

class BusinessHoursCheckResult:
    """Resultado da verificação de horário comercial."""
    
    def __init__(
        self,
        is_open: bool,
        reason: Optional[str] = None,
        message: Optional[str] = None,
        next_opening: Optional[datetime] = None,
    ):
        self.is_open = is_open
        self.reason = reason
        self.message = message
        self.next_opening = next_opening
    
    def __bool__(self) -> bool:
        return self.is_open


def check_business_hours(tenant: Tenant) -> BusinessHoursCheckResult:
    """
    Função principal para verificar horário comercial.
    Retorna objeto com todas as informações necessárias.
    
    Uso:
        result = check_business_hours(tenant)
        if not result:
            return result.message
    """
    is_open, reason = is_within_business_hours(tenant)
    
    if is_open:
        return BusinessHoursCheckResult(is_open=True, reason=reason)
    
    message = get_out_of_hours_message(tenant, reason)
    next_opening = get_next_business_opening(tenant)
    
    return BusinessHoursCheckResult(
        is_open=False,
        reason=reason,
        message=message,
        next_opening=next_opening,
    )