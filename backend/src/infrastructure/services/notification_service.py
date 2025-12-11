"""
SERVIÇO DE NOTIFICAÇÕES
========================

Responsável por:
1. Criar notificações no painel (banco de dados)
2. Enviar WhatsApp para o gestor
3. Montar resumo inteligente do lead

Centraliza toda lógica de notificação que estava espalhada
no dialog360_webhook.py e process_message.py.

Tipos de notificação:
- lead_new: Lead novo chegou
- lead_hot: Lead qualificado como quente
- lead_empreendimento: Lead interessado em empreendimento específico
- lead_out_of_hours: Lead chegou fora do horário
- handoff_requested: Lead pediu para falar com humano
- handoff_completed: Lead transferido para vendedor
"""

import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities import Lead, Tenant, Notification, Empreendimento, Message
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONSTANTES
# =============================================================================

DIALOG360_API_URL = "https://waba.360dialog.io/v1/messages"

# Tipos de notificação suportados
NOTIFICATION_TYPES = {
    "lead_new": {
        "title_template": "📥 Novo Lead!",
        "priority": "normal",
    },
    "lead_hot": {
        "title_template": "🔥 Lead Quente!",
        "priority": "high",
    },
    "lead_empreendimento": {
        "title_template": "🏢 Lead do {empreendimento}!",
        "priority": "high",
    },
    "lead_out_of_hours": {
        "title_template": "🌙 Lead fora do horário",
        "priority": "normal",
    },
    "handoff_requested": {
        "title_template": "🙋 Lead quer falar com humano",
        "priority": "high",
    },
    "handoff_completed": {
        "title_template": "✅ Lead transferido",
        "priority": "low",
    },
}

# Mapeamento de qualificação para emoji
QUALIFICATION_EMOJI = {
    "hot": "🔥 QUENTE",
    "quente": "🔥 QUENTE",
    "warm": "🟡 MORNO",
    "morno": "🟡 MORNO",
    "cold": "🔵 FRIO",
    "frio": "🔵 FRIO",
}


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def format_phone_display(phone: str) -> str:
    """
    Formata telefone para exibição amigável.
    5511999999999 → (11) 99999-9999
    """
    if not phone:
        return "Não informado"
    
    phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    
    if len(phone) == 13 and phone.startswith("55"):
        # 5511999999999 → (11) 99999-9999
        return f"({phone[2:4]}) {phone[4:9]}-{phone[9:]}"
    elif len(phone) == 12 and phone.startswith("55"):
        # 551199999999 → (11) 9999-9999
        return f"({phone[2:4]}) {phone[4:8]}-{phone[8:]}"
    elif len(phone) == 11:
        # 11999999999 → (11) 99999-9999
        return f"({phone[0:2]}) {phone[2:7]}-{phone[7:]}"
    elif len(phone) == 10:
        # 1199999999 → (11) 9999-9999
        return f"({phone[0:2]}) {phone[2:6]}-{phone[6:]}"
    
    return phone


def normalize_phone(phone: str) -> str:
    """
    Normaliza telefone para envio via API.
    Remove caracteres especiais e garante formato internacional.
    """
    if not phone:
        return ""
    
    phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    
    # Garante formato internacional (Brasil)
    if not phone.startswith("55") and len(phone) <= 11:
        phone = "55" + phone
    
    return phone


def format_datetime(dt: datetime) -> str:
    """Formata datetime para exibição."""
    if not dt:
        return "Agora"
    
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Converte para horário de Brasília
        from zoneinfo import ZoneInfo
        dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return dt_br.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return "Agora"


def get_qualification_display(qualification: str) -> str:
    """Retorna qualificação formatada com emoji."""
    if not qualification:
        return "📋 Em qualificação"
    return QUALIFICATION_EMOJI.get(qualification.lower(), "📋 Em qualificação")


# =============================================================================
# CONSTRUÇÃO DE RESUMOS
# =============================================================================

def build_lead_summary_text(
    lead: Lead,
    include_conversation: bool = False,
    conversation_messages: List[Dict] = None,
) -> str:
    """
    Constrói resumo textual do lead para notificação.
    
    Args:
        lead: Entidade Lead
        include_conversation: Se deve incluir resumo da conversa
        conversation_messages: Lista de mensagens (se include_conversation=True)
    
    Returns:
        Texto formatado do resumo
    """
    sections = []
    
    # Dados básicos
    sections.append(f"👤 *Nome:* {lead.name or 'Não informado'}")
    sections.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")
    sections.append(f"📊 *Qualificação:* {get_qualification_display(lead.qualification)}")
    
    if lead.city:
        sections.append(f"📍 *Cidade:* {lead.city}")
    
    # Dados coletados (custom_data)
    if lead.custom_data:
        extras = []
        
        # Empreendimento
        if lead.custom_data.get("empreendimento_nome"):
            extras.append(f"🏢 *Empreendimento:* {lead.custom_data['empreendimento_nome']}")
        
        # Tipologia / Interesse
        tipologia = lead.custom_data.get("tipologia") or lead.custom_data.get("interesse")
        if tipologia:
            extras.append(f"🏠 *Interesse:* {tipologia}")
        
        # Orçamento
        orcamento = lead.custom_data.get("orcamento") or lead.custom_data.get("budget_range")
        if orcamento:
            extras.append(f"💰 *Orçamento:* {orcamento}")
        
        # Prazo / Urgência
        prazo = lead.custom_data.get("prazo") or lead.custom_data.get("urgency_level")
        if prazo:
            extras.append(f"⏰ *Prazo:* {prazo}")
        
        # Forma de pagamento
        if lead.custom_data.get("forma_pagamento"):
            extras.append(f"💳 *Pagamento:* {lead.custom_data['forma_pagamento']}")
        
        # Finalidade
        finalidade = lead.custom_data.get("finalidade") or lead.custom_data.get("objetivo")
        if finalidade:
            extras.append(f"🎯 *Finalidade:* {finalidade}")
        
        # Situação familiar
        if lead.custom_data.get("family_situation"):
            extras.append(f"👨‍👩‍👧 *Família:* {lead.custom_data['family_situation']}")
        
        if extras:
            sections.append("\n📝 *Informações coletadas:*")
            sections.extend(extras)
    
    # Resumo da conversa (se já gerado)
    if lead.summary:
        sections.append(f"\n💬 *Resumo:*\n{lead.summary[:500]}{'...' if len(lead.summary) > 500 else ''}")
    
    # Timestamp
    sections.append(f"\n🕐 *Recebido:* {format_datetime(lead.created_at)}")
    
    return "\n".join(sections)


def build_whatsapp_notification_message(
    lead: Lead,
    notification_type: str,
    tenant: Tenant,
    empreendimento: Empreendimento = None,
    extra_context: str = None,
) -> str:
    """
    Constrói mensagem completa para enviar via WhatsApp ao gestor.
    
    Args:
        lead: Entidade Lead
        notification_type: Tipo da notificação (lead_hot, lead_empreendimento, etc)
        tenant: Tenant para pegar nome da empresa
        empreendimento: Empreendimento (se aplicável)
        extra_context: Contexto adicional (motivo do handoff, etc)
    
    Returns:
        Mensagem formatada para WhatsApp
    """
    settings_dict = tenant.settings or {}
    company_name = settings_dict.get("basic", {}).get("company_name") or tenant.name
    
    # Título baseado no tipo
    type_config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["lead_new"])
    title = type_config["title_template"]
    
    if empreendimento and "{empreendimento}" in title:
        title = title.format(empreendimento=empreendimento.nome)
    
    # Header
    lines = [f"*{title}*"]
    lines.append(f"📍 {company_name}")
    lines.append("─" * 20)
    
    # Resumo do lead
    lines.append(build_lead_summary_text(lead))
    
    # Contexto extra
    if extra_context:
        lines.append(f"\n📌 *Observação:* {extra_context}")
    
    # Footer
    lines.append("\n─" * 20)
    lines.append("_Clique no número acima para iniciar atendimento_")
    
    return "\n".join(lines)


# =============================================================================
# ENVIO VIA WHATSAPP (360DIALOG)
# =============================================================================

async def send_whatsapp_message(
    api_key: str,
    to: str,
    text: str,
) -> Dict[str, Any]:
    """
    Envia mensagem de texto via 360Dialog.
    
    Args:
        api_key: API Key do tenant no 360Dialog
        to: Número do destinatário (formato: 5511999999999)
        text: Texto da mensagem
    
    Returns:
        Dict com success e message_id ou error
    """
    if not api_key:
        logger.error("send_whatsapp_message: API key não fornecida")
        return {"success": False, "error": "api_key_missing"}
    
    if not to:
        logger.error("send_whatsapp_message: Destinatário não fornecido")
        return {"success": False, "error": "recipient_missing"}
    
    headers = {
        "D360-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_phone(to),
        "type": "text",
        "text": {
            "body": text,
            "preview_url": False,
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DIALOG360_API_URL,
                json=payload,
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✅ WhatsApp enviado para {to[-4:]}**** - ID: {message_id}")
                return {"success": True, "message_id": message_id}
            else:
                logger.error(f"❌ Erro WhatsApp para {to[-4:]}****: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text, "status_code": response.status_code}
                
    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout ao enviar WhatsApp para {to[-4:]}****")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"❌ Exceção ao enviar WhatsApp: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FUNÇÕES PRINCIPAIS DE NOTIFICAÇÃO
# =============================================================================

async def create_panel_notification(
    db: AsyncSession,
    tenant_id: int,
    notification_type: str,
    lead: Lead,
    empreendimento: Empreendimento = None,
    extra_message: str = None,
) -> Notification:
    """
    Cria notificação no painel (banco de dados).
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        notification_type: Tipo da notificação
        lead: Lead relacionado
        empreendimento: Empreendimento (se aplicável)
        extra_message: Mensagem adicional
    
    Returns:
        Notification criada
    """
    type_config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["lead_new"])
    
    # Monta título
    title = type_config["title_template"]
    if empreendimento and "{empreendimento}" in title:
        title = title.format(empreendimento=empreendimento.nome)
    
    # Monta mensagem
    lead_name = lead.name or "Lead"
    qualification = get_qualification_display(lead.qualification)
    
    if notification_type == "lead_hot":
        message = f"{lead_name} está muito interessado! {qualification}"
    elif notification_type == "lead_empreendimento" and empreendimento:
        message = f"{lead_name} interessado no {empreendimento.nome}. {qualification}"
    elif notification_type == "lead_out_of_hours":
        message = f"{lead_name} entrou em contato fora do horário comercial."
    elif notification_type == "handoff_requested":
        message = f"{lead_name} solicitou falar com um especialista."
    elif notification_type == "handoff_completed":
        message = f"{lead_name} foi transferido para atendimento humano."
    else:
        message = f"Novo lead: {lead_name}"
    
    if extra_message:
        message += f" {extra_message}"
    
    # Cria notificação
    notification = Notification(
        tenant_id=tenant_id,
        type=notification_type,
        title=title,
        message=message,
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )
    
    db.add(notification)
    await db.flush()
    
    logger.info(f"📬 Notificação criada: {notification_type} - Lead {lead.id}")
    
    return notification


async def notify_gestor_whatsapp(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    notification_type: str,
    empreendimento: Empreendimento = None,
    extra_context: str = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Envia notificação para o gestor via WhatsApp.
    
    Args:
        db: Sessão do banco
        tenant: Tenant
        lead: Lead
        notification_type: Tipo da notificação
        empreendimento: Empreendimento (se aplicável)
        extra_context: Contexto adicional
        force: Se True, envia mesmo se já notificou antes
    
    Returns:
        Dict com resultado do envio
    """
    # Verifica se já notificou (evita spam)
    if not force and lead.custom_data:
        notification_key = f"gestor_notified_{notification_type}"
        if lead.custom_data.get(notification_key):
            logger.debug(f"Lead {lead.id} já notificou gestor para {notification_type}")
            return {"success": False, "reason": "already_notified"}
    
    # Pega configurações do tenant
    settings_dict = tenant.settings or {}
    
    # Determina número do gestor
    gestor_phone = None
    
    # Prioridade 1: WhatsApp do empreendimento (se houver)
    if empreendimento and empreendimento.whatsapp_notificacao:
        gestor_phone = empreendimento.whatsapp_notificacao
    
    # Prioridade 2: WhatsApp do gestor nas configurações de handoff
    if not gestor_phone:
        handoff_config = settings_dict.get("handoff", {})
        gestor_phone = handoff_config.get("manager_whatsapp")
    
    if not gestor_phone:
        logger.warning(f"Tenant {tenant.slug} não tem WhatsApp do gestor configurado")
        return {"success": False, "reason": "no_gestor_phone"}
    
    # Pega API key do 360Dialog
    api_key = settings_dict.get("dialog360_api_key")
    if not api_key:
        logger.warning(f"Tenant {tenant.slug} não tem dialog360_api_key configurado")
        return {"success": False, "reason": "no_api_key"}
    
    # Monta mensagem
    message = build_whatsapp_notification_message(
        lead=lead,
        notification_type=notification_type,
        tenant=tenant,
        empreendimento=empreendimento,
        extra_context=extra_context,
    )
    
    # Envia
    result = await send_whatsapp_message(
        api_key=api_key,
        to=gestor_phone,
        text=message,
    )
    
    # Marca como notificado
    if result.get("success"):
        if not lead.custom_data:
            lead.custom_data = {}
        
        notification_key = f"gestor_notified_{notification_type}"
        lead.custom_data[notification_key] = True
        lead.custom_data[f"{notification_key}_at"] = datetime.now(timezone.utc).isoformat()
        lead.custom_data[f"{notification_key}_phone"] = gestor_phone
        
        logger.info(f"✅ Gestor notificado via WhatsApp - Lead {lead.id}, Tipo: {notification_type}")
    
    return result


async def notify_gestor(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    notification_type: str,
    empreendimento: Empreendimento = None,
    extra_context: str = None,
    send_whatsapp: bool = True,
    create_panel: bool = True,
) -> Dict[str, Any]:
    """
    Função principal para notificar o gestor.
    Cria notificação no painel E envia WhatsApp (se configurado).
    
    Args:
        db: Sessão do banco
        tenant: Tenant
        lead: Lead
        notification_type: Tipo (lead_hot, lead_empreendimento, etc)
        empreendimento: Empreendimento (se aplicável)
        extra_context: Contexto adicional
        send_whatsapp: Se deve enviar WhatsApp
        create_panel: Se deve criar notificação no painel
    
    Returns:
        Dict com resultados
    """
    results = {
        "panel_notification": None,
        "whatsapp_sent": False,
        "whatsapp_error": None,
    }
    
    try:
        # 1. Cria notificação no painel
        if create_panel:
            notification = await create_panel_notification(
                db=db,
                tenant_id=tenant.id,
                notification_type=notification_type,
                lead=lead,
                empreendimento=empreendimento,
                extra_message=extra_context,
            )
            results["panel_notification"] = notification.id
        
        # 2. Envia WhatsApp para o gestor
        if send_whatsapp:
            whatsapp_result = await notify_gestor_whatsapp(
                db=db,
                tenant=tenant,
                lead=lead,
                notification_type=notification_type,
                empreendimento=empreendimento,
                extra_context=extra_context,
            )
            
            results["whatsapp_sent"] = whatsapp_result.get("success", False)
            if not whatsapp_result.get("success"):
                results["whatsapp_error"] = whatsapp_result.get("reason") or whatsapp_result.get("error")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao notificar gestor: {e}")
        results["error"] = str(e)
        return results


# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

async def notify_lead_hot(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    empreendimento: Empreendimento = None,
) -> Dict[str, Any]:
    """Notifica gestor sobre lead quente."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_hot",
        empreendimento=empreendimento,
    )


async def notify_lead_empreendimento(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    empreendimento: Empreendimento,
) -> Dict[str, Any]:
    """Notifica gestor sobre lead interessado em empreendimento."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_empreendimento",
        empreendimento=empreendimento,
    )


async def notify_out_of_hours(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
) -> Dict[str, Any]:
    """Notifica gestor sobre lead que chegou fora do horário."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_out_of_hours",
        send_whatsapp=False,  # Não envia WhatsApp fora do horário
    )


async def notify_handoff_requested(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    reason: str = None,
) -> Dict[str, Any]:
    """Notifica gestor que lead pediu para falar com humano."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="handoff_requested",
        extra_context=reason,
    )