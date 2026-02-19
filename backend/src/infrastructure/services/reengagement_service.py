"""
SERVIÇO DE REENGAJAMENTO
=========================

Responsável por:
1. Detectar leads inativos
2. Gerar mensagens personalizadas de reengajamento
3. Enviar e registrar tentativas
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Tenant, Message, Notification
from src.domain.prompts import get_niche_config


# ==========================================
# CONFIGURAÇÃO PADRÃO
# ==========================================

DEFAULT_REENGAGEMENT_CONFIG = {
    "enabled": False,
    "inactivity_hours": 24,          # Tempo de inatividade para reengajar
    "max_attempts": 3,                # Máximo de tentativas
    "min_hours_between_attempts": 24, # Intervalo mínimo entre tentativas
    "respect_business_hours": True,   # Só reengajar em horário comercial
    "exclude_hot_leads": True,        # Não reengajar leads quentes
    "exclude_handed_off": True,       # Não reengajar leads já transferidos
    "custom_message": None,           # Mensagem customizada (None = IA gera)
}


# ==========================================
# TEMPLATES DE MENSAGEM POR NICHO
# ==========================================

REENGAGEMENT_TEMPLATES = {
    "real_estate": [
        "Oi{nome}! 😊 Vi que você estava buscando um imóvel. Surgiu alguma dúvida que eu possa ajudar?",
        "Olá{nome}! Passando para saber se ainda está interessado. Temos algumas opções que podem te interessar!",
        "Oi{nome}! Não quero ser inconveniente, mas caso ainda esteja procurando, estou aqui para ajudar! 🏠",
    ],
    "healthcare": [
        "Oi{nome}! 😊 Vi que você tinha interesse em agendar. Posso ajudar a encontrar o melhor horário?",
        "Olá{nome}! Passando para saber se ainda precisa de atendimento. Estou aqui para ajudar!",
        "Oi{nome}! Caso ainda precise, temos horários disponíveis. Posso verificar para você? 📋",
    ],
    "fitness": [
        "Oi{nome}! 💪 Vi que você estava interessado em começar a treinar. Posso ajudar com mais informações?",
        "Olá{nome}! Ainda está pensando em começar? Temos condições especiais essa semana!",
        "Oi{nome}! Lembrei de você! Se ainda tiver interesse, estou aqui para tirar suas dúvidas! 🏋️",
    ],
    "education": [
        "Oi{nome}! 📚 Vi que você tinha interesse em nossos cursos. Posso ajudar com mais informações?",
        "Olá{nome}! Passando para saber se ainda está considerando estudar conosco. Alguma dúvida?",
        "Oi{nome}! As matrículas ainda estão abertas! Posso ajudar com algo? 🎓",
    ],
    "services": [
        "Oi{nome}! 😊 Vi que você pediu informações. Posso ajudar com mais alguma coisa?",
        "Olá{nome}! Passando para saber se ainda precisa do nosso serviço. Estou à disposição!",
        "Oi{nome}! Caso ainda tenha interesse, estou aqui para ajudar! 👋",
    ],
}


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def get_reengagement_message(
    niche: str,
    attempt: int,
    lead_name: Optional[str] = None,
    custom_message: Optional[str] = None,
) -> str:
    """
    Retorna a mensagem de reengajamento apropriada.
    
    Args:
        niche: Nicho do tenant
        attempt: Número da tentativa (1, 2, 3...)
        lead_name: Nome do lead (opcional)
        custom_message: Mensagem customizada (sobrescreve template)
    """
    # Se tem mensagem customizada, usa ela
    if custom_message:
        message = custom_message
    else:
        # Pega templates do nicho ou usa services como fallback
        templates = REENGAGEMENT_TEMPLATES.get(niche, REENGAGEMENT_TEMPLATES["services"])
        
        # Seleciona baseado na tentativa (0-indexed)
        template_index = min(attempt - 1, len(templates) - 1)
        message = templates[template_index]
    
    # Substitui o nome
    nome_formatado = f" {lead_name}" if lead_name else ""
    message = message.replace("{nome}", nome_formatado)
    
    return message


def should_reengagement_now(
    settings: dict,
    current_hour: int = None,
) -> bool:
    """
    Verifica se deve fazer reengajamento agora (horário comercial).
    """
    config = {**DEFAULT_REENGAGEMENT_CONFIG, **settings.get("reengagement", {})}
    
    if not config.get("respect_business_hours"):
        return True
    
    if current_hour is None:
        current_hour = datetime.now().hour
    
    # Considera horário comercial: 8h às 20h
    return 8 <= current_hour <= 20


# ==========================================
# FUNÇÕES PRINCIPAIS
# ==========================================

async def get_leads_to_reengage(
    db: AsyncSession,
    tenant: Tenant,
) -> List[Lead]:
    """
    Busca leads que precisam ser reengajados.
    
    Critérios:
    - Inativo há mais de X horas
    - Menos de Y tentativas de reengajamento
    - Não é lead quente (opcional)
    - Não foi transferido (opcional)
    - Última tentativa foi há mais de Z horas
    """
    settings = tenant.settings or {}
    config = {**DEFAULT_REENGAGEMENT_CONFIG, **settings.get("reengagement", {})}
    
    # Se reengajamento não está habilitado, retorna lista vazia
    if not config.get("enabled"):
        return []
    
    now = datetime.now(timezone.utc)
    inactivity_threshold = now - timedelta(hours=config["inactivity_hours"])
    min_between_attempts = now - timedelta(hours=config["min_hours_between_attempts"])
    
    # Monta a query
    conditions = [
        Lead.tenant_id == tenant.id,
        Lead.reengagement_attempts < config["max_attempts"],
        Lead.reengagement_status.in_(["none", "sent"]),  # Não pega responded, failed, given_up
        or_(
            Lead.last_activity_at <= inactivity_threshold,
            and_(
                Lead.last_activity_at.is_(None),
                Lead.created_at <= inactivity_threshold
            )
        ),
        or_(
            Lead.last_reengagement_at.is_(None),
            Lead.last_reengagement_at <= min_between_attempts
        ),
    ]
    
    # Exclui leads quentes se configurado
    if config.get("exclude_hot_leads"):
        conditions.append(Lead.qualification.notin_(["hot", "quente"]))
    
    # Exclui leads transferidos se configurado
    if config.get("exclude_handed_off"):
        conditions.append(Lead.handed_off_at.is_(None))
    
    # Exclui leads perdidos
    conditions.append(Lead.status.notin_(["lost", "perdido", "closed"]))
    
    result = await db.execute(
        select(Lead)
        .where(and_(*conditions))
        .order_by(Lead.last_activity_at.asc().nullsfirst())
        .limit(50)  # Processa em lotes
    )
    
    return list(result.scalars().all())


async def execute_reengagement(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
) -> dict:
    """
    Executa o reengajamento de um lead específico.
    
    Returns:
        {
            "success": bool,
            "message": str,
            "attempt": int,
        }
    """
    from .whatsapp_service import send_whatsapp_message
    
    settings = tenant.settings or {}
    config = {**DEFAULT_REENGAGEMENT_CONFIG, **settings.get("reengagement", {})}
    niche = settings.get("niche", "services")
    
    # Incrementa tentativa
    lead.reengagement_attempts += 1
    attempt = lead.reengagement_attempts
    
    # Gera mensagem
    message = get_reengagement_message(
        niche=niche,
        attempt=attempt,
        lead_name=lead.name,
        custom_message=config.get("custom_message"),
    )
    
    # Tenta enviar
    try:
        # Se tem telefone, envia via WhatsApp
        if lead.phone:
            await send_whatsapp_message(lead.phone, message)
        
        # Salva a mensagem no histórico
        msg = Message(
            lead_id=lead.id,
            role="assistant",
            content=message,
            tokens_used=0,
        )
        db.add(msg)
        
        # Atualiza lead
        lead.last_reengagement_at = datetime.now(timezone.utc)
        lead.reengagement_status = "sent"
        
        # Se atingiu máximo de tentativas, marca como given_up
        if attempt >= config["max_attempts"]:
            lead.reengagement_status = "given_up"
        
        # Cria notificação
        notification = Notification(
            tenant_id=tenant.id,
            type="reengagement",
            title="🔄 Reengajamento enviado",
            message=f"Tentativa {attempt} para {lead.name or lead.phone}",
            reference_type="lead",
            reference_id=lead.id,
            read=False,
        )
        db.add(notification)
        
        await db.commit()
        
        return {
            "success": True,
            "message": message,
            "attempt": attempt,
            "status": lead.reengagement_status,
        }
        
    except Exception as e:
        lead.reengagement_status = "failed"
        await db.commit()
        
        return {
            "success": False,
            "error": str(e),
            "attempt": attempt,
            "status": "failed",
        }


async def process_reengagement_batch(
    db: AsyncSession,
    tenant: Tenant,
) -> dict:
    """
    Processa um lote de reengajamentos para o tenant.
    
    Returns:
        {
            "processed": int,
            "success": int,
            "failed": int,
            "skipped": int,
        }
    """
    settings = tenant.settings or {}
    
    # Verifica horário comercial
    if not should_reengagement_now(settings):
        return {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "outside_business_hours",
        }
    
    # Busca leads para reengajar
    leads = await get_leads_to_reengage(db, tenant)
    
    results = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    
    for lead in leads:
        results["processed"] += 1
        
        result = await execute_reengagement(db, lead, tenant)
        
        if result.get("success"):
            results["success"] += 1
        else:
            results["failed"] += 1
    
    return results


async def mark_lead_activity(
    db: AsyncSession,
    lead: Lead,
) -> None:
    """
    Marca que o lead teve atividade (deve ser chamado quando lead envia mensagem).
    Reseta o status de reengajamento se o lead respondeu.
    """
    lead.last_activity_at = datetime.now(timezone.utc)
    
    # Se estava em reengajamento e respondeu, marca como responded
    if lead.reengagement_status == "sent":
        lead.reengagement_status = "responded"
    
    await db.commit()